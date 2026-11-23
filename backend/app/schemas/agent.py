from datetime import datetime, timedelta

from pydantic import BaseModel, Field, computed_field

from app.utils.time import utc_now

# The endpoint agent sends a heartbeat every 30 s by default (soc-agent/config.yaml).
AGENT_ONLINE_WITHIN = timedelta(seconds=90)
AGENT_STALE_WITHIN = timedelta(minutes=10)


class AgentRegister(BaseModel):
    name: str
    hostname: str


class AgentRegisterResponse(BaseModel):
    id: str
    name: str
    api_key: str


class AgentOut(BaseModel):
    id: str
    name: str
    hostname: str
    is_active: bool
    last_seen_at: datetime | None
    created_at: datetime

    model_config = {"from_attributes": True}

    @computed_field
    @property
    def connection_status(self) -> str:
        """ONLINE (recent heartbeat/events), STALE (missed a few), OFFLINE, or NEVER_SEEN."""
        if self.last_seen_at is None:
            return "NEVER_SEEN"
        age = utc_now() - self.last_seen_at
        if age <= AGENT_ONLINE_WITHIN:
            return "ONLINE"
        if age <= AGENT_STALE_WITHIN:
            return "STALE"
        return "OFFLINE"


class EventBatch(BaseModel):
    events: list[dict]


class WazuhAlertBatch(BaseModel):
    """Raw Wazuh alerts (lines of /var/ossec/logs/alerts/alerts.json)."""

    alerts: list[dict] = Field(max_length=1000)
