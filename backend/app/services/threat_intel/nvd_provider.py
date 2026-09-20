import httpx

from app.config import get_settings
from app.services.threat_intel.base import ThreatIntelProvider, ThreatIntelResult
from app.utils.logging import get_logger

logger = get_logger(__name__)
settings = get_settings()

BASE_URL = "https://services.nvd.nist.gov/rest/json/cves/2.0"


class NVDProvider(ThreatIntelProvider):
    """Optional CVE lookups via the NVD API. Works without an API key at a
    much lower rate limit; failures never crash an investigation.
    """

    name = "nvd"

    def lookup_ip(self, ip: str) -> ThreatIntelResult | None:
        return None

    def lookup_domain(self, domain: str) -> ThreatIntelResult | None:
        return None

    def lookup_hash(self, file_hash: str) -> ThreatIntelResult | None:
        return None

    def lookup_cve(self, cve_id: str) -> ThreatIntelResult | None:
        headers = {"apiKey": settings.NVD_API_KEY} if settings.NVD_API_KEY else {}
        try:
            resp = httpx.get(BASE_URL, params={"cveId": cve_id}, headers=headers, timeout=8)
            if resp.status_code != 200:
                logger.warning("NVD returned status %s for %s", resp.status_code, cve_id)
                return None
            data = resp.json()
        except httpx.HTTPError as exc:
            logger.warning("NVD request failed: %s", exc)
            return None

        vulns = data.get("vulnerabilities", [])
        if not vulns:
            return None
        cve = vulns[0].get("cve", {})
        descriptions = cve.get("descriptions", [])
        description = next((d["value"] for d in descriptions if d.get("lang") == "en"), "")
        metrics = cve.get("metrics", {})
        severity = "unknown"
        score = None
        for key in ("cvssMetricV31", "cvssMetricV30", "cvssMetricV2"):
            if key in metrics and metrics[key]:
                cvss = metrics[key][0].get("cvssData", {})
                severity = cvss.get("baseSeverity", metrics[key][0].get("baseSeverity", "unknown"))
                score = cvss.get("baseScore")
                break

        return ThreatIntelResult(
            indicator=cve_id,
            indicator_type="cve",
            reputation="malicious" if score and score >= 7 else "suspicious" if score else "unknown",
            classification=f"CVSS severity: {severity}",
            source=self.name,
            confidence=0.9 if score else 0.4,
            details={"description": description, "cvss_score": score, "severity": severity},
        )
