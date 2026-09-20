from pathlib import Path

from sqlalchemy.orm import Session

from app.config import get_settings
from app.models.incident import Incident
from app.models.report import Report
from app.services.reporting.builder import build_report_content
from app.services.reporting.pdf_renderer import render_pdf

settings = get_settings()


def generate_report(db: Session, incident: Incident, report_format: str = "json") -> Report:
    content = build_report_content(db, incident)

    report = Report(incident_id=incident.id, format=report_format, content=content)
    db.add(report)
    db.flush()

    if report_format == "pdf":
        output_path = str(Path(settings.REPORTS_DIR) / f"{report.id}.pdf")
        render_pdf(content, output_path)
        report.file_path = output_path

    db.commit()
    db.refresh(report)
    return report
