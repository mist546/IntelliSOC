from collections import Counter
from datetime import timedelta

from fastapi import APIRouter, Depends
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_user
from app.database import get_db
from app.models.agent import Agent
from app.models.alert import Alert
from app.models.incident import Incident
from app.models.investigation import Investigation
from app.models.log_event import LogEvent
from app.models.website_scan import WebsiteScan
from app.schemas.dashboard import DashboardStatistics, SeverityCounts
from app.utils.time import utc_now

router = APIRouter(prefix="/api/dashboard", tags=["dashboard"])


@router.get("/statistics", response_model=DashboardStatistics)
def get_statistics(db: Session = Depends(get_db), _user=Depends(get_current_user)):
    severity_rows = db.query(Alert.severity, func.count(Alert.id)).group_by(Alert.severity).all()
    severity_counts = SeverityCounts(**{sev: count for sev, count in severity_rows if sev in SeverityCounts.model_fields})

    open_incidents = db.query(Incident).filter(Incident.status.in_(["OPEN", "INVESTIGATING"])).count()
    active_agents = db.query(Agent).filter(Agent.is_active.is_(True)).count()
    total_alerts = db.query(Alert).count()
    total_log_events = db.query(LogEvent).count()

    recent_investigations = [
        {
            "id": i.id,
            "alert_id": i.alert_id,
            "incident_id": i.incident_id,
            "status": i.status,
            "risk_score": i.risk_score,
            "created_at": i.created_at.isoformat(),
        }
        for i in db.query(Investigation).order_by(Investigation.created_at.desc()).limit(5).all()
    ]

    since = utc_now() - timedelta(days=7)
    alerts_last_week = db.query(Alert).filter(Alert.timestamp >= since).all()
    by_day = Counter(a.timestamp.strftime("%Y-%m-%d") for a in alerts_last_week)
    alerts_over_time = [{"date": d, "count": c} for d, c in sorted(by_day.items())]

    ip_counts = Counter(a.source_ip for a in db.query(Alert).all() if a.source_ip)
    top_source_ips = [{"source_ip": ip, "count": c} for ip, c in ip_counts.most_common(10)]

    event_type_rows = db.query(LogEvent.event_type, func.count(LogEvent.id)).group_by(LogEvent.event_type).all()
    event_type_distribution = [{"event_type": et, "count": c} for et, c in event_type_rows]

    incident_status_rows = db.query(Incident.status, func.count(Incident.id)).group_by(Incident.status).all()
    incident_status_distribution = [{"status": s, "count": c} for s, c in incident_status_rows]

    recent_scans = [
        {"id": s.id, "target_url": s.target_url, "status": s.status, "started_at": s.started_at.isoformat()}
        for s in db.query(WebsiteScan).order_by(WebsiteScan.started_at.desc()).limit(5).all()
    ]

    return DashboardStatistics(
        alert_counts_by_severity=severity_counts,
        open_incidents=open_incidents,
        active_agents=active_agents,
        total_alerts=total_alerts,
        total_log_events=total_log_events,
        recent_investigations=recent_investigations,
        alerts_over_time=alerts_over_time,
        top_source_ips=top_source_ips,
        event_type_distribution=event_type_distribution,
        incident_status_distribution=incident_status_distribution,
        recent_website_scans=recent_scans,
    )
