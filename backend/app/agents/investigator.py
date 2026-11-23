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

Investigations run in the background (see `start_investigation` and
`run_investigation_job`): the API returns a RUNNING investigation at once,
and each trace step is saved and pushed to the dashboard over the live
event stream as it happens, so the analyst watches the agent work.
"""
import json
import re
from collections.abc import Callable
from datetime import timedelta

from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session

from app.models.alert import Alert
from app.models.investigation import Investigation
from app.services.live_events import publish_event
from app.services.llm.service import generate_structured_analysis, is_llm_available
from app.services.risk.anomaly_detector import compute_anomaly_score
from app.tools.alert_tools import get_alert_details, get_related_events
from app.tools.incident_tools import search_previous_incidents
from app.tools.knowledge_tools import get_background_knowledge, get_investigation_playbook, get_response_playbook
from app.tools.log_tools import search_related_logs
from app.tools.report_tools import generate_report
from app.tools.risk_tools import calculate_risk_tool
from app.tools.threat_intel_tools import get_ip_threat_intelligence
from app.utils.logging import get_logger
from app.utils.time import utc_now

logger = get_logger(__name__)

RELATED_LOGS_WINDOW_MINUTES = 30
KNOWLEDGE_EXCERPT_CHARS = 450
IP_RE = re.compile(r"\b(?:\d{1,3}\.){3}\d{1,3}\b")

# (purpose, trace label, tool) - three separate knowledge questions per alert.
KNOWLEDGE_STEPS = (
    ("investigation_playbook", "Investigation playbook retrieved", get_investigation_playbook),
    ("response_playbook", "Response playbook retrieved", get_response_playbook),
    ("background", "Attack and vulnerability knowledge retrieved", get_background_knowledge),
)


class Trace:
    def __init__(self, on_step: Callable[[dict], None] | None = None) -> None:
        self._steps: list[dict] = []
        self._on_step = on_step

    def add(self, action: str, detail: str) -> None:
        step = {"step": len(self._steps) + 1, "action": action, "detail": detail}
        self._steps.append(step)
        logger.info("[investigation] %s: %s", action, detail)
        if self._on_step:
            self._on_step(step)

    @property
    def steps(self) -> list[dict]:
        return self._steps


def _build_evidence_prompt(
    alert_details: dict,
    related_events: list[dict],
    threat_intel: list[dict],
    knowledge: list[dict],
    previous_incidents: list[dict],
    risk,
    observations: list[str] | None = None,
) -> str:
    def _knowledge_block(purpose: str, empty: str) -> str:
        # A chunk that answers several questions is printed once, under the
        # first question that retrieved it, and referenced from the others.
        items = [k for k in knowledge if k.get("purpose") == purpose]
        shown_above = [k["id"] for k in knowledge if purpose in k.get("also", [])]
        parts = [f"[{k['id']}] ({citation_label(k)})\n{(k.get('content') or '')[:KNOWLEDGE_EXCERPT_CHARS]}" for k in items]
        if shown_above:
            parts.append(f"Also relevant here: {', '.join(f'[{i}]' for i in shown_above)} (shown above).")
        return "\n\n".join(parts) if parts else empty

    sections = [
        "## EVIDENCE (directly observed by the system - ground truth)",
        json.dumps(
            {
                "alert": alert_details,
                # Deterministic observations over ALL related events (the event
                # sample below is truncated, so key facts like "a successful
                # login followed the failures" must not depend on the cut-off).
                "observations": observations or [],
                "related_log_events_sample": related_events[:8],
                "related_log_event_count": len(related_events),
            },
            indent=2,
            default=str,
        ),
        "\n## THREAT_INTELLIGENCE (from configured threat intel providers)",
        json.dumps(threat_intel, indent=2, default=str) if threat_intel else "No threat intelligence available for the indicators in this alert.",
        "\n## KNOWLEDGE - cite these by their [K] id in \"references\"",
        "### INVESTIGATION_PLAYBOOK (how to verify this kind of alert)",
        _knowledge_block("investigation_playbook", "No investigation playbook retrieved."),
        "### RESPONSE_PLAYBOOK (what to recommend)",
        _knowledge_block("response_playbook", "No response playbook retrieved."),
        "### BACKGROUND (attack, vulnerability, MITRE ATT&CK, OWASP, NIST)",
        _knowledge_block("background", "No relevant background knowledge retrieved."),
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


def _summarize_auth_evidence(events: list[dict]) -> list[tuple[str, str]]:
    """Turn related auth events into the concise, auditable observations the
    trace shows (e.g. "43 failed attempts found", "Successful login detected").
    Only counts what was directly observed - never infers compromise."""
    failures = [e for e in events if e.get("event_type") == "AUTH_FAILURE"]
    successes = [e for e in events if e.get("event_type") == "AUTH_SUCCESS"]
    observations: list[tuple[str, str]] = []
    if failures:
        users = sorted({e["username"] for e in failures if e.get("username")})
        user_note = f" against {len(users)} account(s): {', '.join(users[:5])}" if users else ""
        observations.append(("Failed authentication attempts found", f"{len(failures)} failed attempt(s){user_note}"))
    if successes:
        after_failure = failures and successes[-1]["timestamp"] > failures[0]["timestamp"]
        detail = "; ".join(f"{e.get('username') or 'unknown user'} at {e['timestamp']}" for e in successes[:3])
        if after_failure:
            detail += " - occurred AFTER failed attempts from the same indicator (possible successful brute force)"
        observations.append(("Successful login detected", detail))
    return observations


def citation_label(item: dict) -> str:
    """"response_playbooks/escalation.md" or "nist/sp_800_61_rev3.pdf p. 14"."""
    return f"{item['source']} p. {item['page']}" if item.get("page") else item["source"]


def resolve_references(raw_refs: list[str], knowledge: list[dict]) -> tuple[list[dict], list[str]]:
    """Map the LLM's cited [K] ids to the knowledge actually provided.
    Returns (resolved references, ids that were never provided). Invented
    citations are dropped rather than shown as if they were real sources."""
    by_id = {k["id"]: k for k in knowledge}
    resolved: list[dict] = []
    unknown: list[str] = []
    for raw in raw_refs:
        ref_id = str(raw).strip().strip("[]").upper()
        if ref_id in by_id:
            if all(r["id"] != ref_id for r in resolved):
                k = by_id[ref_id]
                resolved.append({key: k.get(key) for key in ("id", "source", "title", "page", "heading", "category")})
        else:
            unknown.append(str(raw))
    return resolved, unknown


def _gather_knowledge(alert: Alert, trace: Trace) -> list[dict]:
    """Ask the three knowledge questions and number every retrieved chunk
    K1..Kn so the LLM can cite exactly what it used. The query context is
    the alert's title/description with IP addresses removed (IPs carry no
    meaning for retrieval and only add noise)."""
    context = IP_RE.sub("", f"{alert.title}. {alert.description or ''}")
    knowledge: list[dict] = []
    for purpose, label, tool in KNOWLEDGE_STEPS:
        try:
            response = tool(alert.detection_rule, context)
        except Exception as exc:  # noqa: BLE001
            trace.add(f"{label.split(' retrieved')[0]} retrieval failed", str(exc))
            continue
        if not response["available"]:
            trace.add("RAG knowledge retrieval unavailable", response["message"])
            break  # the same reason (empty index, embeddings down) applies to every step
        new, repeated = [], []
        for result in response["results"]:
            existing = next((k for k in knowledge if k["content"] == result["content"]), None)
            if existing:
                existing.setdefault("also", []).append(purpose)
                repeated.append(existing["id"])
            else:
                item = {**result, "id": f"K{len(knowledge) + 1}", "purpose": purpose}
                knowledge.append(item)
                new.append(item)
        details = []
        if new:
            details.append(f"{len(new)} section(s) from {', '.join(sorted({citation_label(r) for r in new}))}")
        if repeated:
            details.append(f"{len(repeated)} section(s) already retrieved above ({', '.join(repeated)})")
        trace.add(label, "; ".join(details) or response["message"] or "No sufficiently relevant knowledge found")
    return knowledge


def _investigation_event(investigation: Investigation) -> dict:
    return {"id": investigation.id, "alert_id": investigation.alert_id, "status": investigation.status}


def start_investigation(db: Session, alert: Alert) -> tuple[Investigation, bool]:
    """Create the RUNNING investigation record for an alert. Returns
    (investigation, created); if one is already running for this alert it
    is returned instead of starting a duplicate."""
    running = (
        db.query(Investigation)
        .filter(Investigation.alert_id == alert.id, Investigation.status.in_(["PENDING", "RUNNING"]))
        .first()
    )
    if running:
        return running, False

    investigation = Investigation(alert_id=alert.id, incident_id=alert.incident_id, status="RUNNING", trace=[])
    db.add(investigation)
    db.commit()
    db.refresh(investigation)
    publish_event("investigation.started", _investigation_event(investigation))
    return investigation, True


def run_investigation_job(bind: Engine, investigation_id: str) -> None:
    """Background entry point: runs a started investigation in its own DB
    session. Any unexpected error marks it FAILED instead of leaving it
    stuck in RUNNING."""
    db = Session(bind=bind)
    try:
        investigation = db.get(Investigation, investigation_id)
        alert = db.get(Alert, investigation.alert_id) if investigation else None
        if investigation is None or alert is None:
            logger.error("Investigation %s or its alert no longer exists", investigation_id)
            return
        try:
            investigate_alert(db, alert, investigation=investigation)
        except Exception as exc:  # noqa: BLE001
            logger.exception("Investigation %s failed", investigation_id)
            db.rollback()
            investigation.status = "FAILED"
            investigation.error_message = f"Investigation failed: {exc}"[:1024]
            investigation.completed_at = utc_now()
            db.commit()
            publish_event("investigation.completed", _investigation_event(investigation))
    finally:
        db.close()


def investigate_alert(
    db: Session, alert: Alert, force: bool = False, investigation: Investigation | None = None
) -> Investigation:
    if investigation is None:
        investigation, _ = start_investigation(db, alert)

    def save_step(step: dict) -> None:
        # Persist the trace after every step so a page refresh (or another
        # analyst) sees the progress, then push it to connected dashboards.
        investigation.trace = list(trace.steps)
        db.commit()
        publish_event("investigation.step", {**_investigation_event(investigation), "step": step})

    trace = Trace(on_step=save_step)
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

    indicators = {k: v for k, v in (("source_ip", alert.source_ip), ("username", alert.username), ("host", alert.host)) if v}
    trace.add(
        "Indicators extracted",
        ", ".join(f"{k}={v}" for k, v in indicators.items()) if indicators else "No IP/username/host indicators on this alert",
    )
    observations = _summarize_auth_evidence(related_events)
    for observation in observations:
        trace.add(*observation)

    threat_intel: list[dict] = []
    if alert.source_ip:
        try:
            threat_intel = get_ip_threat_intelligence(db, alert.source_ip)
            if threat_intel:
                reps = ", ".join(f"{t['source']}={t['reputation']}" for t in threat_intel)
                trace.add("Threat intelligence lookup completed", f"IP {alert.source_ip}: {reps}")
        except Exception as exc:  # noqa: BLE001
            trace.add("Threat intelligence lookup failed", str(exc))

    knowledge = _gather_knowledge(alert, trace)

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
        alert_details,
        list(related_events),
        threat_intel,
        knowledge,
        previous_incidents,
        risk,
        observations=[f"{action}: {detail}" for action, detail in observations],
    )

    llm_available = is_llm_available()
    ai_analysis = None
    error_message = None
    if llm_available:
        trace.add("Evidence sent to local LLM", "Requesting structured analysis from Ollama")
        analysis, err = generate_structured_analysis(evidence_prompt)
        if analysis:
            ai_analysis = analysis.model_dump()
            references, unknown = resolve_references(analysis.references, knowledge)
            ai_analysis["references"] = references
            trace.add("AI analysis validated", f"attack_type={analysis.attack_type}, confidence={analysis.confidence}")
            trace.add(
                "AI citations checked",
                f"{len(references)} cited knowledge source(s) verified"
                + (f"; {len(unknown)} citation(s) to sources that were never provided removed" if unknown else ""),
            )
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

    investigation.incident_id = alert.incident_id
    investigation.evidence = {"alert": alert_details, "related_events": list(related_events)}
    investigation.threat_intelligence = threat_intel
    investigation.rag_sources = knowledge
    investigation.risk_score = risk.risk_score
    investigation.risk_factors = risk.risk_factors
    investigation.ai_analysis = ai_analysis
    investigation.llm_available = llm_available
    investigation.error_message = error_message
    # Marked COMPLETED before the report step so the saved report records
    # the final status.
    investigation.status = "COMPLETED"
    investigation.completed_at = utc_now()
    trace.add("Investigation completed", f"llm_available={llm_available}")

    # Final tool: persist a JSON incident report that captures this investigation.
    # Analysts can still generate PDF reports on demand from the incident page.
    if investigation.incident_id:
        try:
            report_info = generate_report(db, investigation, report_format="json")
            if report_info:
                trace.add("Investigation report generated", f"JSON report {report_info['report_id']} for incident {report_info['incident_id']}")
        except Exception as exc:  # noqa: BLE001 - reporting must never fail the investigation
            trace.add("Investigation report generation failed", str(exc))

    db.commit()
    db.refresh(investigation)
    publish_event("investigation.completed", _investigation_event(investigation))
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
