import httpx

from app.config import get_settings
from app.services.threat_intel.base import ThreatIntelProvider, ThreatIntelResult
from app.utils.logging import get_logger

logger = get_logger(__name__)
settings = get_settings()

BASE_URL = "https://www.virustotal.com/api/v3"


class VirusTotalProvider(ThreatIntelProvider):
    """Optional online provider. Any failure (missing key, timeout, network
    error, rate limit) must never crash an investigation — callers treat a
    None return as 'unavailable' and continue with other evidence.
    """

    name = "virustotal"

    def __init__(self) -> None:
        self.api_key = settings.VIRUSTOTAL_API_KEY
        self.enabled = bool(self.api_key)

    def _get(self, path: str) -> dict | None:
        if not self.enabled:
            return None
        try:
            resp = httpx.get(
                f"{BASE_URL}{path}",
                headers={"x-apikey": self.api_key},
                timeout=8,
            )
            if resp.status_code != 200:
                logger.warning("VirusTotal returned status %s for %s", resp.status_code, path)
                return None
            return resp.json()
        except httpx.HTTPError as exc:
            logger.warning("VirusTotal request failed: %s", exc)
            return None

    def lookup_ip(self, ip: str) -> ThreatIntelResult | None:
        data = self._get(f"/ip_addresses/{ip}")
        if not data:
            return None
        stats = data.get("data", {}).get("attributes", {}).get("last_analysis_stats", {})
        malicious = stats.get("malicious", 0)
        suspicious = stats.get("suspicious", 0)
        reputation = "malicious" if malicious > 0 else "suspicious" if suspicious > 0 else "clean"
        confidence = min(0.95, 0.5 + 0.05 * (malicious + suspicious))
        return ThreatIntelResult(
            indicator=ip,
            indicator_type="ip",
            reputation=reputation,
            classification=f"{malicious} malicious / {suspicious} suspicious vendor flags",
            source=self.name,
            confidence=confidence,
            details={"last_analysis_stats": stats},
        )

    def lookup_domain(self, domain: str) -> ThreatIntelResult | None:
        data = self._get(f"/domains/{domain}")
        if not data:
            return None
        stats = data.get("data", {}).get("attributes", {}).get("last_analysis_stats", {})
        malicious = stats.get("malicious", 0)
        reputation = "malicious" if malicious > 0 else "clean"
        return ThreatIntelResult(
            indicator=domain,
            indicator_type="domain",
            reputation=reputation,
            classification=f"{malicious} malicious vendor flags",
            source=self.name,
            confidence=min(0.95, 0.5 + 0.05 * malicious),
            details={"last_analysis_stats": stats},
        )

    def lookup_hash(self, file_hash: str) -> ThreatIntelResult | None:
        data = self._get(f"/files/{file_hash}")
        if not data:
            return None
        stats = data.get("data", {}).get("attributes", {}).get("last_analysis_stats", {})
        malicious = stats.get("malicious", 0)
        reputation = "malicious" if malicious > 0 else "clean"
        return ThreatIntelResult(
            indicator=file_hash,
            indicator_type="hash",
            reputation=reputation,
            classification=f"{malicious} malicious vendor flags",
            source=self.name,
            confidence=min(0.95, 0.5 + 0.05 * malicious),
            details={"last_analysis_stats": stats},
        )

    def lookup_cve(self, cve_id: str) -> ThreatIntelResult | None:
        return None
