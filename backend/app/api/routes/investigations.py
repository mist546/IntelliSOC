from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_user
from app.database import get_db
from app.models.investigation import Investigation
from app.schemas.investigation import InvestigationOut, InvestigationSummaryOut, InvestigationTraceOut

router = APIRouter(prefix="/api/investigations", tags=["investigations"])


@router.get("", response_model=list[InvestigationSummaryOut])
def list_investigations(
    status: str | None = None,
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    _user=Depends(get_current_user),
):
    query = db.query(Investigation)
    if status:
        query = query.filter(Investigation.status == status.upper())
    return query.order_by(Investigation.created_at.desc()).offset(skip).limit(limit).all()


@router.get("/{investigation_id}", response_model=InvestigationOut)
def get_investigation(investigation_id: str, db: Session = Depends(get_db), _user=Depends(get_current_user)):
    investigation = db.query(Investigation).filter(Investigation.id == investigation_id).first()
    if not investigation:
        raise HTTPException(status_code=404, detail="Investigation not found")
    return investigation


@router.get("/{investigation_id}/trace", response_model=InvestigationTraceOut)
def get_investigation_trace(investigation_id: str, db: Session = Depends(get_db), _user=Depends(get_current_user)):
    investigation = db.query(Investigation).filter(Investigation.id == investigation_id).first()
    if not investigation:
        raise HTTPException(status_code=404, detail="Investigation not found")
    return InvestigationTraceOut(id=investigation.id, status=investigation.status, trace=investigation.trace)
