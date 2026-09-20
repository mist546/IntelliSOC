from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_user
from app.database import get_db
from app.models.alert import Alert
from app.schemas.alert import AlertOut, AlertStatusUpdate
from app.schemas.investigation import InvestigateRequest, InvestigationOut

router = APIRouter(prefix="/api/alerts", tags=["alerts"])

VALID_STATUSES = {"NEW", "ACKNOWLEDGED", "INVESTIGATING", "RESOLVED", "FALSE_POSITIVE"}


@router.get("", response_model=list[AlertOut])
def list_alerts(
    severity: str | None = None,
    status: str | None = None,
    source_ip: str | None = None,
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    _user=Depends(get_current_user),
):
    query = db.query(Alert)
    if severity:
        query = query.filter(Alert.severity == severity.upper())
    if status:
        query = query.filter(Alert.status == status.upper())
    if source_ip:
        query = query.filter(Alert.source_ip == source_ip)
    return query.order_by(Alert.timestamp.desc()).offset(skip).limit(limit).all()


@router.get("/{alert_id}", response_model=AlertOut)
def get_alert(alert_id: str, db: Session = Depends(get_db), _user=Depends(get_current_user)):
    alert = db.query(Alert).filter(Alert.id == alert_id).first()
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")
    return alert


@router.patch("/{alert_id}/status", response_model=AlertOut)
def update_alert_status(
    alert_id: str, payload: AlertStatusUpdate, db: Session = Depends(get_db), _user=Depends(get_current_user)
):
    alert = db.query(Alert).filter(Alert.id == alert_id).first()
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")
    new_status = payload.status.upper()
    if new_status not in VALID_STATUSES:
        raise HTTPException(status_code=400, detail=f"Invalid status. Allowed: {sorted(VALID_STATUSES)}")
    alert.status = new_status
    db.commit()
    db.refresh(alert)
    return alert


@router.post("/{alert_id}/investigate", response_model=InvestigationOut)
def investigate_alert(
    alert_id: str,
    payload: InvestigateRequest = InvestigateRequest(),
    db: Session = Depends(get_db),
    _user=Depends(get_current_user),
):
    from app.agents.investigator import investigate_alert as run_investigation

    alert = db.query(Alert).filter(Alert.id == alert_id).first()
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")

    investigation = run_investigation(db, alert, force=payload.force)
    if alert.status == "NEW":
        alert.status = "INVESTIGATING"
        db.commit()
    return investigation
