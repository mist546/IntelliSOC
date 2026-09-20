from dataclasses import dataclass, field
from datetime import datetime

from app.utils.time import utc_now


@dataclass
class ThreatIntelResult:
    indicator: str
    indicator_type: str  # ip | domain | hash | cve
    reputation: str  # malicious | suspicious | clean | unknown
    classification: str | None
    source: str
    confidence: float
    details: dict = field(default_factory=dict)
    timestamp: datetime = field(default_factory=utc_now)


class ThreatIntelProvider:
    name = "base"

    def lookup_ip(self, ip: str) -> ThreatIntelResult | None:
        raise NotImplementedError

    def lookup_domain(self, domain: str) -> ThreatIntelResult | None:
        raise NotImplementedError

    def lookup_hash(self, file_hash: str) -> ThreatIntelResult | None:
        raise NotImplementedError

    def lookup_cve(self, cve_id: str) -> ThreatIntelResult | None:
        raise NotImplementedError
