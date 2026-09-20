from sqlalchemy.orm import Session

from app.models.threat_intel import ThreatIntel
from app.services.threat_intel.base import ThreatIntelResult
from app.services.threat_intel.local_provider import LocalThreatIntelProvider
from app.services.threat_intel.nvd_provider import NVDProvider
from app.services.threat_intel.virustotal_provider import VirusTotalProvider
from app.utils.logging import get_logger

logger = get_logger(__name__)

_local = LocalThreatIntelProvider()
_virustotal = VirusTotalProvider()
_nvd = NVDProvider()


def _persist(db: Session | None, result: ThreatIntelResult) -> None:
    if db is None:
        return
    try:
        db.add(
            ThreatIntel(
                indicator=result.indicator,
                indicator_type=result.indicator_type,
                reputation=result.reputation,
                classification=result.classification,
                source=result.source,
                confidence=result.confidence,
                details=result.details,
            )
        )
        db.flush()
    except Exception:  # noqa: BLE001
        logger.exception("Failed to persist threat intel result")


def _safe_call(provider_name: str, fn, *args) -> ThreatIntelResult | None:
    try:
        return fn(*args)
    except Exception:  # noqa: BLE001
        logger.warning("Threat intel provider %s failed; continuing without it", provider_name)
        return None


def enrich_ip(ip: str, db: Session | None = None) -> list[ThreatIntelResult]:
    results = []
    local = _safe_call("local", _local.lookup_ip, ip)
    if local:
        results.append(local)
        _persist(db, local)

    if _virustotal.enabled:
        vt = _safe_call("virustotal", _virustotal.lookup_ip, ip)
        if vt:
            results.append(vt)
            _persist(db, vt)

    return results


def enrich_domain(domain: str, db: Session | None = None) -> list[ThreatIntelResult]:
    results = []
    local = _safe_call("local", _local.lookup_domain, domain)
    if local:
        results.append(local)
        _persist(db, local)

    if _virustotal.enabled:
        vt = _safe_call("virustotal", _virustotal.lookup_domain, domain)
        if vt:
            results.append(vt)
            _persist(db, vt)

    return results


def enrich_hash(file_hash: str, db: Session | None = None) -> list[ThreatIntelResult]:
    results = []
    if _virustotal.enabled:
        vt = _safe_call("virustotal", _virustotal.lookup_hash, file_hash)
        if vt:
            results.append(vt)
            _persist(db, vt)
    if not results:
        local = _safe_call("local", _local.lookup_hash, file_hash)
        if local:
            results.append(local)
    return results


def enrich_cve(cve_id: str, db: Session | None = None) -> list[ThreatIntelResult]:
    results = []
    nvd = _safe_call("nvd", _nvd.lookup_cve, cve_id)
    if nvd:
        results.append(nvd)
        _persist(db, nvd)
    if not results:
        local = _safe_call("local", _local.lookup_cve, cve_id)
        if local:
            results.append(local)
    return results


def enrich_indicator(indicator: str, indicator_type: str, db: Session | None = None) -> list[ThreatIntelResult]:
    if indicator_type == "ip":
        return enrich_ip(indicator, db)
    if indicator_type == "domain":
        return enrich_domain(indicator, db)
    if indicator_type == "hash":
        return enrich_hash(indicator, db)
    if indicator_type == "cve":
        return enrich_cve(indicator, db)
    return []
