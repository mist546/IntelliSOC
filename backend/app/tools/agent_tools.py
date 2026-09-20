from sqlalchemy.orm import Session

from app.models.agent import Agent


def get_agent_info(db: Session, agent_id: str | None) -> dict | None:
    if not agent_id:
        return None
    agent = db.query(Agent).filter(Agent.id == agent_id).first()
    if not agent:
        return None
    return {
        "id": agent.id,
        "name": agent.name,
        "hostname": agent.hostname,
        "is_active": agent.is_active,
        "last_seen_at": agent.last_seen_at.isoformat() if agent.last_seen_at else None,
    }
