from sqlalchemy.orm import Session

from app.services.threat_intel.base import ThreatIntelResult
from app.services.threat_intel.service import enrich_cve, enrich_domain, enrich_ip


def _serialize(results: list[ThreatIntelResult]) -> list[dict]:
    return [
        {
            "indicator": r.indicator,
            "indicator_type": r.indicator_type,
            "reputation": r.reputation,
            "classification": r.classification,
            "source": r.source,
            "confidence": r.confidence,
            "details": r.details,
            "timestamp": r.timestamp.isoformat(),
        }
        for r in results
    ]


def get_ip_threat_intelligence(db: Session, ip: str) -> list[dict]:
    return _serialize(enrich_ip(ip, db=db))


def get_domain_threat_intelligence(db: Session, domain: str) -> list[dict]:
    return _serialize(enrich_domain(domain, db=db))


def lookup_cve(db: Session, cve_id: str) -> list[dict]:
    return _serialize(enrich_cve(cve_id, db=db))
