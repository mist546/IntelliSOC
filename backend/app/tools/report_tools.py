from sqlalchemy.orm import Session

from app.models.incident import Incident
from app.models.investigation import Investigation
from app.services.reporting.service import generate_report as _generate_report


def generate_report(db: Session, investigation: Investigation, report_format: str = "json") -> dict | None:
    """Agent tool: produce an incident report that includes this investigation.

    Reports are scoped to the incident (so every alert/investigation in it is
    covered). Returns a small summary dict, or None when the alert was not
    correlated into an incident (nothing to report against).
    """
    if not investigation.incident_id:
        return None
    incident = db.query(Incident).filter(Incident.id == investigation.incident_id).first()
    if not incident:
        return None
    report = _generate_report(db, incident, report_format=report_format)
    return {"report_id": report.id, "incident_id": incident.id, "format": report.format}
