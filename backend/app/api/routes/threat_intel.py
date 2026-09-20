import ipaddress
import re

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_user
from app.database import get_db
from app.schemas.threat_intel import ThreatIntelOut
from app.services.threat_intel.service import enrich_indicator

router = APIRouter(prefix="/api/threat-intel", tags=["threat-intel"])

CVE_RE = re.compile(r"^CVE-\d{4}-\d{4,}$", re.IGNORECASE)
HASH_RE = re.compile(r"^[a-fA-F0-9]{32,64}$")


def _detect_indicator_type(indicator: str) -> str:
    try:
        ipaddress.ip_address(indicator)
        return "ip"
    except ValueError:
        pass
    if CVE_RE.match(indicator):
        return "cve"
    if HASH_RE.match(indicator):
        return "hash"
    return "domain"


@router.get("/{indicator}", response_model=list[ThreatIntelOut])
def get_threat_intel(
    indicator: str,
    indicator_type: str | None = Query(default=None, alias="type"),
    db: Session = Depends(get_db),
    _user=Depends(get_current_user),
):
    detected_type = indicator_type or _detect_indicator_type(indicator)
    results = enrich_indicator(indicator, detected_type, db=db)
    db.commit()
    return [
        ThreatIntelOut(
            indicator=r.indicator,
            indicator_type=r.indicator_type,
            reputation=r.reputation,
            classification=r.classification,
            source=r.source,
            confidence=r.confidence,
            details=r.details,
            timestamp=r.timestamp,
        )
        for r in results
    ]
