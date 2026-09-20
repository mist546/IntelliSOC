import uuid
from datetime import datetime

from app.utils.time import utc_now

from sqlalchemy import JSON, DateTime, Float, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.session import Base
from app.models.enums import InvestigationStatus


class Investigation(Base):
    __tablename__ = "investigations"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    alert_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("alerts.id"), nullable=True)
    incident_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("incidents.id"), nullable=True)

    status: Mapped[str] = mapped_column(String(20), default=InvestigationStatus.PENDING.value, nullable=False)

    trace: Mapped[list] = mapped_column(JSON, default=list)
    evidence: Mapped[dict] = mapped_column(JSON, default=dict)
    threat_intelligence: Mapped[list] = mapped_column(JSON, default=list)
    rag_sources: Mapped[list] = mapped_column(JSON, default=list)

    risk_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    risk_factors: Mapped[list] = mapped_column(JSON, default=list)

    ai_analysis: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    llm_available: Mapped[bool] = mapped_column(default=True)
    error_message: Mapped[str | None] = mapped_column(String(1024), nullable=True)

    incident: Mapped["Incident"] = relationship(back_populates="investigations")

    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
