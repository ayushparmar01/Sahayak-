"""FollowUpRecord model for application timeline, follow-up tasks, and reminders."""
import uuid
from datetime import datetime, timezone
from sqlalchemy import String, Boolean, DateTime, ForeignKey, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base


class FollowUpRecord(Base):
    __tablename__ = "follow_up_records"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    citizen_id: Mapped[str] = mapped_column(String(36), ForeignKey("citizens.id", ondelete="CASCADE"), index=True)
    application_draft_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("application_drafts.id", ondelete="CASCADE"), nullable=True, index=True)
    scheme_id: Mapped[str | None] = mapped_column(String(50), nullable=True)

    task_type: Mapped[str] = mapped_column(String(50), default="CHECKLIST_GAP")  # CHECKLIST_GAP, DOCUMENT_CORRECTION, OPERATOR_REVIEW, STATUS_CHECK, CITIZEN_ACTION
    title_hi: Mapped[str] = mapped_column(String(200))
    title_en: Mapped[str] = mapped_column(String(200))
    description_hi: Mapped[str | None] = mapped_column(Text, nullable=True)
    description_en: Mapped[str | None] = mapped_column(Text, nullable=True)
    reason: Mapped[str | None] = mapped_column(String(255), nullable=True)

    status: Mapped[str] = mapped_column(String(50), default="PENDING")  # PENDING, COMPLETED, CANCELLED, OVERDUE
    due_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    is_suggested_date: Mapped[bool] = mapped_column(Boolean, default=True)

    origin: Mapped[str] = mapped_column(String(50), default="CHECKLIST_GAP")  # CHECKLIST_GAP, DOCUMENT_CORRECTION, OPERATOR_MANUAL, CITIZEN_REQUEST
    dedup_key: Mapped[str | None] = mapped_column(String(100), nullable=True, index=True)

    reminder_channel: Mapped[str] = mapped_column(String(50), default="IN_APP")  # IN_APP, SMS_MOCK, WHATSAPP_MOCK
    reminder_dispatched: Mapped[bool] = mapped_column(Boolean, default=False)
    delivery_status: Mapped[str] = mapped_column(String(50), default="SCHEDULED")  # SCHEDULED, DELIVERED_IN_APP, SIMULATED_MOCK_DISPATCH, FAILED

    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completion_notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc)
    )

    # Relationships
    citizen: Mapped["Citizen"] = relationship("Citizen", back_populates="follow_ups")
    draft: Mapped["ApplicationDraft | None"] = relationship("ApplicationDraft", back_populates="follow_ups")
