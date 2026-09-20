import uuid
from datetime import datetime

from app.utils.time import utc_now

from sqlalchemy import JSON, DateTime, Float, ForeignKey, Index, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.session import Base
from app.models.enums import AlertStatus, Severity


class Alert(Base):
    __tablename__ = "alerts"
    __table_args__ = (Index("ix_alerts_severity", "severity"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    severity: Mapped[str] = mapped_column(String(16), default=Severity.LOW.value, nullable=False)
    confidence: Mapped[float] = mapped_column(Float, default=0.5, nullable=False)
    timestamp: Mapped[datetime] = mapped_column(DateTime, default=utc_now)

    source_ip: Mapped[str | None] = mapped_column(String(45), nullable=True, index=True)
    username: Mapped[str | None] = mapped_column(String(128), nullable=True)
    host: Mapped[str | None] = mapped_column(String(255), nullable=True)

    detection_rule: Mapped[str] = mapped_column(String(64), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    evidence: Mapped[list] = mapped_column(JSON, default=list)
    related_event_ids: Mapped[list] = mapped_column(JSON, default=list)

    status: Mapped[str] = mapped_column(String(20), default=AlertStatus.NEW.value, nullable=False, index=True)

    incident_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("incidents.id"), nullable=True)
    incident: Mapped["Incident"] = relationship(back_populates="alerts")

    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=utc_now, onupdate=utc_now
    )
