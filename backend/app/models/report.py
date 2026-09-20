import uuid
from datetime import datetime

from app.utils.time import utc_now

from sqlalchemy import JSON, DateTime, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.session import Base


class Report(Base):
    __tablename__ = "reports"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    incident_id: Mapped[str] = mapped_column(String(36), ForeignKey("incidents.id"), nullable=False)
    format: Mapped[str] = mapped_column(String(8), default="json", nullable=False)  # json | pdf
    file_path: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    content: Mapped[dict] = mapped_column(JSON, default=dict)

    incident: Mapped["Incident"] = relationship(back_populates="reports")

    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now)
