"""The Mini-SOC agentic investigation orchestrator (Milestone 2).

This is intentionally ONE orchestrator, not a multi-agent swarm (per project
scope). Rather than letting a small local LLM freely choose tool calls via
function-calling (unreliable with 3-4B parameter models and hard to audit),
the orchestrator itself dynamically decides which tools are relevant based
on the alert's content - e.g. it only looks up domain threat intelligence
if a domain indicator is present, only searches previous incidents when a
correlating indicator (IP/username) exists, etc. Every step is recorded in
an auditable trace (section 23 of the spec) before the aggregated evidence
is handed to the local LLM for the final structured analysis. This keeps
the "agentic" investigation reliable and explainable, which the project
brief explicitly prioritizes over flashier but fragile autonomy.
"""
import json
from datetime import timedelta

from sqlalchemy.orm import Session

from app.models.alert import Alert
from app.models.investigation import Investigation
from app.services.llm.service import generate_structured_analysis, is_llm_available
from app.services.risk.anomaly_detector import compute_anomaly_score
from app.tools.alert_tools import get_alert_details, get_related_events
from app.tools.incident_tools import search_previous_incidents
from app.tools.knowledge_tools import get_response_playbook, search_security_knowledge
from app.tools.log_tools import search_related_logs
from app.tools.risk_tools import calculate_risk_tool
from app.tools.threat_intel_tools import get_ip_threat_intelligence
from app.utils.logging import get_logger
from app.utils.time import utc_now

logger = get_logger(__name__)

RELATED_LOGS_WINDOW_MINUTES = 30


class Trace:
    def __init__(self) -> None:
        self._steps: list[dict] = []

    def add(self, action: str, detail: str) -> None:
        self._steps.append({"step": len(self._steps) + 1, "action": action, "detail": detail})
        logger.info("[investigation] %s: %s", action, detail)

    @property
    def steps(self) -> list[dict]:
        return self._steps


def _build_evidence_prompt(
    alert_details: dict,
    related_events: list[dict],
    threat_intel: list[dict],
    knowledge: list[dict],
    playbook: list[dict],
    previous_incidents: list[dict],
    risk,
) -> str:
    def _trim(chunks: list[dict], max_chars: int = 350) -> list[dict]:
        return [{**c, "content": (c.get("content") or "")[:max_chars]} for c in chunks]

    sections = [
        "## EVIDENCE (directly observed by the system - ground truth)",
        json.dumps(
            {
                "alert": alert_details,
                "related_log_events": related_events[:8],
                "related_log_event_count": len(related_events),
            },
            indent=2,
            default=str,
        ),
        "\n## THREAT_INTELLIGENCE (from configured threat intel providers)",
        json.dumps(threat_intel, indent=2, default=str) if threat_intel else "No threat intelligence available for the indicators in this alert.",
        "\n## KNOWLEDGE (retrieved from the security knowledge base via RAG)",
        json.dumps(_trim(knowledge), indent=2, default=str) if knowledge else "No relevant knowledge base entries retrieved.",
        "\n## RESPONSE_PLAYBOOK (retrieved from the security knowledge base via RAG)",
        json.dumps(_trim(playbook), indent=2, default=str) if playbook else "No specific playbook retrieved.",
        "\n## PREVIOUS_INCIDENTS (same source IP/username, if any)",
        json.dumps(previous_incidents, indent=2, default=str) if previous_incidents else "No related previous incidents found.",
        "\n## RISK (deterministic score already computed - do not contradict without evidence-based reason)",
        json.dumps(
            {"risk_score": risk.risk_score, "severity": risk.severity, "confidence": risk.confidence, "risk_factors": risk.risk_factors},
            indent=2,
        ),
        "\nProduce your structured JSON analysis now, following the schema and rules exactly.",
    ]
    return "\n".join(sections)


def investigate_alert(db: Session, alert: Alert, force: bool = False) -> Investigation:
    trace = Trace()
    trace.add("Alert received", f"Alert {alert.id} ({alert.detection_rule}, severity={alert.severity})")

    alert_details = get_alert_details(db, alert.id) or {}
    trace.add("Alert details loaded", f"Title: {alert.title}")

    linked_events = get_related_events(db, alert)

    window_start = alert.timestamp - timedelta(minutes=RELATED_LOGS_WINDOW_MINUTES)
    window_end = alert.timestamp + timedelta(minutes=RELATED_LOGS_WINDOW_MINUTES)
    searched_events = []
    if alert.source_ip or alert.username:
        searched_events = search_related_logs(
            db,
            source_ip=alert.source_ip,
            username=alert.username if not alert.source_ip else None,
            start_time=window_start,
            end_time=window_end,
        )
        trace.add(
            "Related authentication/activity logs searched",
            f"{len(searched_events)} event(s) found within +/-{RELATED_LOGS_WINDOW_MINUTES} minutes",
        )

    related_events = {e["id"]: e for e in (linked_events + searched_events)}.values()
    related_events = sorted(related_events, key=lambda e: e["timestamp"])

    threat_intel: list[dict] = []
    if alert.source_ip:
        try:
            threat_intel = get_ip_threat_intelligence(db, alert.source_ip)
            if threat_intel:
                reps = ", ".join(f"{t['source']}={t['reputation']}" for t in threat_intel)
                trace.add("Threat intelligence lookup completed", f"IP {alert.source_ip}: {reps}")
        except Exception as exc:  # noqa: BLE001
            trace.add("Threat intelligence lookup failed", str(exc))

    knowledge_results: list[dict] = []
    try:
        kb_query = f"{alert.detection_rule.replace('_', ' ')} {alert.title}"
        kb_response = search_security_knowledge(kb_query)
        if kb_response["available"]:
            knowledge_results = kb_response["results"]
            trace.add("Security knowledge retrieved from RAG", f"{len(knowledge_results)} relevant chunk(s) found")
        else:
            trace.add("RAG knowledge retrieval unavailable", kb_response["message"])
    except Exception as exc:  # noqa: BLE001
        trace.add("RAG knowledge retrieval failed", str(exc))

    playbook_results: list[dict] = []
    try:
        playbook_response = get_response_playbook(alert.detection_rule)
        if playbook_response["available"]:
            playbook_results = playbook_response["results"]
            trace.add("Response playbook retrieved from RAG", f"{len(playbook_results)} relevant chunk(s) found")
    except Exception as exc:  # noqa: BLE001
        trace.add("Response playbook retrieval failed", str(exc))

    previous_incidents: list[dict] = []
    try:
        previous_incidents = search_previous_incidents(
            db, source_ip=alert.source_ip, username=alert.username, exclude_incident_id=alert.incident_id
        )
        if previous_incidents:
            trace.add("Previous related incidents checked", f"{len(previous_incidents)} found")
    except Exception as exc:  # noqa: BLE001
        trace.add("Previous incident search failed", str(exc))

    anomaly = compute_anomaly_score(db, alert.source_ip, alert.timestamp) if alert.source_ip else None
    if anomaly and anomaly.anomaly_score is not None:
        trace.add(
            "ML anomaly score computed (supplementary only)",
            f"anomaly_score={anomaly.anomaly_score}, is_anomaly={anomaly.is_anomaly} ({anomaly.note})",
        )
    elif anomaly:
        trace.add("ML anomaly detection skipped", anomaly.note)

    risk = calculate_risk_tool(
        alert,
        threat_intel_results=_dicts_to_ti_results(threat_intel),
        anomaly_score=anomaly.anomaly_score if anomaly else None,
        is_anomaly=anomaly.is_anomaly if anomaly else False,
    )
    trace.add("Risk calculated", f"score={risk.risk_score}, severity={risk.severity}, confidence={risk.confidence}")

    evidence_prompt = _build_evidence_prompt(
        alert_details, list(related_events), threat_intel, knowledge_results, playbook_results, previous_incidents, risk
    )

    llm_available = is_llm_available()
    ai_analysis = None
    error_message = None
    if llm_available:
        trace.add("Evidence sent to local LLM", "Requesting structured analysis from Ollama")
        analysis, err = generate_structured_analysis(evidence_prompt)
        if analysis:
            ai_analysis = analysis.model_dump()
            trace.add("AI analysis validated", f"attack_type={analysis.attack_type}, confidence={analysis.confidence}")
            trace.add(
                "Response recommendation generated",
                f"{len(analysis.recommended_actions)} action(s) recommended (require human approval)",
            )
        else:
            error_message = err
            llm_available = False
            trace.add("AI analysis failed", err or "unknown error")
    else:
        error_message = "Ollama is unavailable or the configured model is not installed."
        trace.add("Local LLM unavailable", "Continuing investigation using non-LLM evidence only")

    trace.add("Investigation completed", f"llm_available={llm_available}")

    investigation = Investigation(
        alert_id=alert.id,
        incident_id=alert.incident_id,
        status="COMPLETED",
        trace=trace.steps,
        evidence={
            "alert": alert_details,
            "related_events": list(related_events),
        },
        threat_intelligence=threat_intel,
        rag_sources=knowledge_results + playbook_results,
        risk_score=risk.risk_score,
        risk_factors=risk.risk_factors,
        ai_analysis=ai_analysis,
        llm_available=llm_available,
        error_message=error_message,
        completed_at=utc_now(),
    )
    db.add(investigation)
    db.commit()
    db.refresh(investigation)
    return investigation


def _dicts_to_ti_results(items: list[dict]):
    from app.services.threat_intel.base import ThreatIntelResult

    results = []
    for item in items:
        results.append(
            ThreatIntelResult(
                indicator=item["indicator"],
                indicator_type=item["indicator_type"],
                reputation=item["reputation"],
                classification=item.get("classification"),
                source=item["source"],
                confidence=item["confidence"],
                details=item.get("details", {}),
            )
        )
    return results
