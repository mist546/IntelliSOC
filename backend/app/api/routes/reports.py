import json

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse, Response
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_user
from app.database import get_db
from app.models.incident import Incident
from app.models.report import Report
from app.schemas.report import ReportOut, ReportRequest
from app.services.reporting.service import generate_report

router = APIRouter(prefix="/api/reports", tags=["reports"])


@router.get("", response_model=list[ReportOut])
def list_reports(
    incident_id: str | None = None,
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    _user=Depends(get_current_user),
):
    query = db.query(Report)
    if incident_id:
        query = query.filter(Report.incident_id == incident_id)
    return query.order_by(Report.created_at.desc()).offset(skip).limit(limit).all()


@router.post("/{incident_id}", response_model=ReportOut)
def create_report(
    incident_id: str, payload: ReportRequest = ReportRequest(), db: Session = Depends(get_db), _user=Depends(get_current_user)
):
    incident = db.query(Incident).filter(Incident.id == incident_id).first()
    if not incident:
        raise HTTPException(status_code=404, detail="Incident not found")
    if payload.format not in ("json", "pdf"):
        raise HTTPException(status_code=400, detail="format must be 'json' or 'pdf'")

    return generate_report(db, incident, report_format=payload.format)


@router.get("/{report_id}", response_model=ReportOut)
def get_report(report_id: str, db: Session = Depends(get_db), _user=Depends(get_current_user)):
    report = db.query(Report).filter(Report.id == report_id).first()
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")
    return report


@router.get("/{report_id}/download")
def download_report(report_id: str, db: Session = Depends(get_db), _user=Depends(get_current_user)):
    report = db.query(Report).filter(Report.id == report_id).first()
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")

    if report.format == "pdf":
        if not report.file_path:
            raise HTTPException(status_code=404, detail="Report file not found")
        return FileResponse(
            report.file_path,
            media_type="application/pdf",
            filename=f"incident_report_{report.incident_id}.pdf",
        )

    filename = f"incident_report_{report.incident_id}.json"
    return Response(
        content=json.dumps(report.content, indent=2),
        media_type="application/json",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
