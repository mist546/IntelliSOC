from datetime import datetime

from pydantic import BaseModel


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


class EventBatch(BaseModel):
    events: list[dict]
