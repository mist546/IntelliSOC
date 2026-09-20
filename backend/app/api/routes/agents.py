import secrets

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_user, require_admin
from app.database import get_db
from app.models.agent import Agent
from app.schemas.agent import AgentOut, AgentRegister, AgentRegisterResponse
from app.utils.security import hash_password

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
