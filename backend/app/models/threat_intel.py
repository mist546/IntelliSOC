import uuid
from datetime import datetime

from app.utils.time import utc_now

from sqlalchemy import JSON, DateTime, Float, String
from sqlalchemy.orm import Mapped, mapped_column

from app.database.session import Base


class ThreatIntel(Base):
    __tablename__ = "threat_intel"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    indicator: Mapped[str] = mapped_column(String(512), nullable=False, index=True)
    indicator_type: Mapped[str] = mapped_column(String(16), nullable=False)  # ip | domain | hash | cve
    reputation: Mapped[str] = mapped_column(String(32), nullable=False)  # malicious | suspicious | clean | unknown
    classification: Mapped[str | None] = mapped_column(String(128), nullable=True)
    source: Mapped[str] = mapped_column(String(64), nullable=False)
    confidence: Mapped[float] = mapped_column(Float, default=0.5)
    details: Mapped[dict] = mapped_column(JSON, default=dict)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now)
