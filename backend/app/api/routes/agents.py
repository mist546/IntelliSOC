import secrets

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_agent, get_current_user, require_admin
from app.database import get_db
from app.models.agent import Agent
from app.models.log_event import LogEvent
from app.schemas.agent import AgentOut, AgentRegister, AgentRegisterResponse
from app.services.live_events import publish_event
from app.utils.security import hash_password
from app.utils.time import utc_now

router = APIRouter(prefix="/api/agents", tags=["agents"])


@router.post("/register", response_model=AgentRegisterResponse)
def register_agent(payload: AgentRegister, db: Session = Depends(get_db), _admin=Depends(require_admin)):
    api_key = secrets.token_urlsafe(32)
    agent = Agent(name=payload.name, hostname=payload.hostname, api_key_hash=hash_password(api_key))
    db.add(agent)
    db.commit()
    db.refresh(agent)
    return AgentRegisterResponse(id=agent.id, name=agent.name, api_key=api_key)


@router.get("", response_model=list[AgentOut])
def list_agents(db: Session = Depends(get_db), _user=Depends(get_current_user)):
    return db.query(Agent).order_by(Agent.created_at.desc()).all()


@router.delete("/{agent_id}")
def delete_agent(agent_id: str, db: Session = Depends(get_db), _admin=Depends(require_admin)):
    """Remove an agent, revoking its API key. Logs it already shipped are
    kept as evidence, just no longer linked to an agent."""
    agent = db.query(Agent).filter(Agent.id == agent_id).first()
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    db.query(LogEvent).filter(LogEvent.agent_id == agent_id).update({LogEvent.agent_id: None}, synchronize_session=False)
    db.delete(agent)
    db.commit()
    publish_event("agent.deleted", {"id": agent_id, "name": agent.name})
    return {"id": agent_id, "deleted": True}


@router.post("/heartbeat")
def agent_heartbeat(db: Session = Depends(get_db), agent: Agent = Depends(get_current_agent)):
    """Called periodically by the endpoint agent so a quiet host (no new
    logs) is still shown as online, and a dead agent shows as offline."""
    agent.last_seen_at = utc_now()
    db.commit()
    publish_event("agent.heartbeat", {"id": agent.id, "name": agent.name})
    return {"status": "ok", "server_time": agent.last_seen_at.isoformat()}
