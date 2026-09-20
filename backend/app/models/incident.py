import uuid
from datetime import datetime

from app.utils.time import utc_now

from sqlalchemy import DateTime, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.session import Base
from app.models.enums import IncidentStatus, Severity


class Incident(Base):
    __tablename__ = "incidents"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False, default="")
    severity: Mapped[str] = mapped_column(String(16), default=Severity.LOW.value, nullable=False)
    status: Mapped[str] = mapped_column(String(20), default=IncidentStatus.OPEN.value, nullable=False, index=True)
    correlation_key: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)

    alerts: Mapped[list["Alert"]] = relationship(back_populates="incident")
    investigations: Mapped[list["Investigation"]] = relationship(back_populates="incident")
    reports: Mapped[list["Report"]] = relationship(back_populates="incident")

    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=utc_now, onupdate=utc_now
    )
