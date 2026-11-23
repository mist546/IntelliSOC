from sqlalchemy.orm import Session

from app.models.incident import Incident
from app.models.investigation import Investigation


def build_report_content(db: Session, incident: Incident) -> dict:
    investigations = (
        db.query(Investigation)
        .filter(Investigation.incident_id == incident.id)
        .order_by(Investigation.created_at)
        .all()
    )

    alerts = [
        {
            "id": a.id,
            "title": a.title,
            "severity": a.severity,
            "confidence": a.confidence,
            "detection_rule": a.detection_rule,
            "description": a.description,
            "evidence": a.evidence,
            "source_ip": a.source_ip,
            "username": a.username,
            "host": a.host,
            "status": a.status,
            "timestamp": a.timestamp.isoformat(),
        }
        for a in incident.alerts
    ]

    timeline = sorted(
        [{"timestamp": a["timestamp"], "event": f"Alert: {a['title']} ({a['severity']})"} for a in alerts],
        key=lambda x: x["timestamp"],
    )

    investigations_out = []
    for inv in investigations:
        analysis = inv.ai_analysis or {}
        investigations_out.append(
            {
                "id": inv.id,
                "alert_id": inv.alert_id,
                "status": inv.status,
                "trace": inv.trace,
                "threat_intelligence": inv.threat_intelligence,
                "rag_sources": [
                    {"id": s.get("id"), "title": s.get("title"), "source": s.get("source"), "page": s.get("page")}
                    for s in inv.rag_sources
                ],
                # Knowledge the AI actually cited (verified against what it was given).
                "ai_references": analysis.get("references", []),
                "risk_score": inv.risk_score,
                "risk_factors": inv.risk_factors,
                "llm_available": inv.llm_available,
                "ai_summary": analysis.get("summary"),
                "ai_severity": analysis.get("severity"),
                "ai_confidence": analysis.get("confidence"),
                "ai_impact": analysis.get("impact"),
                "mitre_technique": analysis.get("mitre_technique"),
                "owasp_category": analysis.get("owasp_category"),
                "recommended_actions": analysis.get("recommended_actions", []),
                "requires_human_approval": analysis.get("requires_human_approval", True),
                "insufficient_evidence": analysis.get("insufficient_evidence", False),
            }
        )

    return {
        "incident_summary": {
            "id": incident.id,
            "title": incident.title,
            "description": incident.description,
            "severity": incident.severity,
            "status": incident.status,
            "created_at": incident.created_at.isoformat(),
            "updated_at": incident.updated_at.isoformat(),
        },
        "alerts": alerts,
        "timeline": timeline,
        "investigations": investigations_out,
        "containment_status": "No containment actions were executed automatically. "
        "All response actions above are recommendations pending human analyst approval.",
    }
