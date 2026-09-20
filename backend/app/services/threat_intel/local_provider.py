import ipaddress
import json
from pathlib import Path

from app.config import get_settings
from app.services.threat_intel.base import ThreatIntelProvider, ThreatIntelResult
from app.utils.logging import get_logger

logger = get_logger(__name__)
settings = get_settings()

PRIVATE_NETWORKS = [
    ipaddress.ip_network("10.0.0.0/8"),
    ipaddress.ip_network("172.16.0.0/12"),
    ipaddress.ip_network("192.168.0.0/16"),
    ipaddress.ip_network("127.0.0.0/8"),
]


def _load_json(filename: str) -> dict:
    path = Path(settings.THREAT_INTEL_DIR) / filename
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text())
    except (json.JSONDecodeError, OSError) as exc:
        logger.warning("Could not load threat intel file %s: %s", filename, exc)
        return {}


class LocalThreatIntelProvider(ThreatIntelProvider):
    """Mandatory offline threat intel source backed by curated synthetic/local data.

    Guarantees the system can produce threat intelligence even with no
    internet access or external API keys configured.
    """

    name = "local"

    def __init__(self) -> None:
        self._ips = _load_json("known_ips.json")
        self._domains = _load_json("known_domains.json")

    def lookup_ip(self, ip: str) -> ThreatIntelResult | None:
        try:
            addr = ipaddress.ip_address(ip)
            if any(addr in net for net in PRIVATE_NETWORKS):
                return ThreatIntelResult(
                    indicator=ip,
                    indicator_type="ip",
                    reputation="clean",
                    classification="Private network range (RFC1918/loopback)",
                    source=self.name,
                    confidence=0.99,
                    details={"notes": "Private address space; not internet-routable."},
                )
        except ValueError:
            pass

        entry = self._ips.get(ip)
        if entry:
            return ThreatIntelResult(
                indicator=ip,
                indicator_type="ip",
                reputation=entry["reputation"],
                classification=entry.get("classification"),
                source=self.name,
                confidence=entry.get("confidence", 0.5),
                details=entry.get("details", {}),
            )

        return ThreatIntelResult(
            indicator=ip,
            indicator_type="ip",
            reputation="unknown",
            classification=None,
            source=self.name,
            confidence=0.3,
            details={"notes": "No local threat intelligence record found for this indicator."},
        )

    def lookup_domain(self, domain: str) -> ThreatIntelResult | None:
        entry = self._domains.get(domain.lower())
        if entry:
            return ThreatIntelResult(
                indicator=domain,
                indicator_type="domain",
                reputation=entry["reputation"],
                classification=entry.get("classification"),
                source=self.name,
                confidence=entry.get("confidence", 0.5),
                details=entry.get("details", {}),
            )
        return ThreatIntelResult(
            indicator=domain,
            indicator_type="domain",
            reputation="unknown",
            classification=None,
            source=self.name,
            confidence=0.3,
            details={"notes": "No local threat intelligence record found for this indicator."},
        )

    def lookup_hash(self, file_hash: str) -> ThreatIntelResult | None:
        return ThreatIntelResult(
            indicator=file_hash,
            indicator_type="hash",
            reputation="unknown",
            classification=None,
            source=self.name,
            confidence=0.2,
            details={"notes": "Local provider has no file hash database; configure VirusTotal for hash lookups."},
        )

    def lookup_cve(self, cve_id: str) -> ThreatIntelResult | None:
        return ThreatIntelResult(
            indicator=cve_id,
            indicator_type="cve",
            reputation="unknown",
            classification=None,
            source=self.name,
            confidence=0.2,
            details={"notes": "Local provider has no CVE database; configure NVD_API_KEY for CVE lookups."},
        )
