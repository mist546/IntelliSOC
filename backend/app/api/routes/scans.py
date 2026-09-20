from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_user
from app.database import get_db
from app.models.website_scan import WebsiteScan
from app.schemas.website_scan import ScanOut, ScanRequest
from app.services.scanning.scanner import run_scan
from app.utils.time import utc_now

router = APIRouter(prefix="/api/scans", tags=["scans"])


@router.post("", response_model=ScanOut)
def create_scan(payload: ScanRequest, db: Session = Depends(get_db), _user=Depends(get_current_user)):
    scan = WebsiteScan(target_url=payload.target_url, status="RUNNING")
    db.add(scan)
    db.commit()
    db.refresh(scan)

    outcome = run_scan(payload.target_url)

    scan.checks_run = outcome.checks_run
    scan.findings = [f.__dict__ for f in outcome.findings]
    scan.error_message = outcome.error
    scan.status = "FAILED" if outcome.error else "COMPLETED"
    scan.completed_at = utc_now()
    db.commit()
    db.refresh(scan)
    return scan


@router.get("", response_model=list[ScanOut])
def list_scans(skip: int = 0, limit: int = 50, db: Session = Depends(get_db), _user=Depends(get_current_user)):
    return db.query(WebsiteScan).order_by(WebsiteScan.started_at.desc()).offset(skip).limit(limit).all()


@router.get("/{scan_id}", response_model=ScanOut)
def get_scan(scan_id: str, db: Session = Depends(get_db), _user=Depends(get_current_user)):
    scan = db.query(WebsiteScan).filter(WebsiteScan.id == scan_id).first()
    if not scan:
        raise HTTPException(status_code=404, detail="Scan not found")
    return scan
