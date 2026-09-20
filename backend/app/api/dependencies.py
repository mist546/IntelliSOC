from fastapi import Depends, Header, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from app.config import get_settings
from app.database import get_db
from app.models.agent import Agent
from app.models.user import User
from app.utils.security import decode_access_token

settings = get_settings()
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login", auto_error=False)


def get_current_user(token: str | None = Depends(oauth2_scheme), db: Session = Depends(get_db)) -> User:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    if token is None:
        raise credentials_exception
    payload = decode_access_token(token)
    if payload is None or "sub" not in payload:
        raise credentials_exception
    user = db.query(User).filter(User.id == payload["sub"]).first()
    if user is None or not user.is_active:
        raise credentials_exception
    return user


def require_admin(user: User = Depends(get_current_user)) -> User:
    if user.role != "ADMIN":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin privileges required")
    return user


def get_current_agent(
    x_agent_id: str | None = Header(default=None),
    x_agent_key: str | None = Header(default=None),
    db: Session = Depends(get_db),
) -> Agent:
    from app.utils.security import verify_password

    if not x_agent_id or not x_agent_key:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Agent credentials required")
    agent = db.query(Agent).filter(Agent.id == x_agent_id).first()
    if agent is None or not agent.is_active or not verify_password(x_agent_key, agent.api_key_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid agent credentials")
    return agent
