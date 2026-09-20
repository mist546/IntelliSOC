from pydantic import BaseModel


class SeverityCounts(BaseModel):
    CRITICAL: int = 0
    HIGH: int = 0
    MEDIUM: int = 0
    LOW: int = 0


class DashboardStatistics(BaseModel):
    alert_counts_by_severity: SeverityCounts
    open_incidents: int
    active_agents: int
    total_alerts: int
    total_log_events: int
    recent_investigations: list[dict]
    alerts_over_time: list[dict]
    top_source_ips: list[dict]
    event_type_distribution: list[dict]
    incident_status_distribution: list[dict]
    recent_website_scans: list[dict]
