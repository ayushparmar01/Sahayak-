"""ApplicationDraft and DraftDocumentLink models."""
import uuid
from datetime import datetime, timezone
from sqlalchemy import String, Float, Boolean, DateTime, ForeignKey, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base


class ApplicationDraft(Base):
    __tablename__ = "application_drafts"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    citizen_id: Mapped[str] = mapped_column(String(36), ForeignKey("citizens.id", ondelete="CASCADE"))
    scheme_id: Mapped[str] = mapped_column(String(50), ForeignKey("schemes.id", ondelete="CASCADE"))
    
    status: Mapped[str] = mapped_column(String(50), default="DRAFT_IN_PROGRESS")  # DRAFT_IN_PROGRESS, DRAFT_READY, CITIZEN_SUBMITTED
    prefilled_data: Mapped[dict] = mapped_column(JSON, default=dict)
    completeness_percentage: Mapped[float] = mapped_column(Float, default=0.0)
    
    checklist_status: Mapped[dict] = mapped_column(JSON, default=dict)
    cross_document_checks: Mapped[list] = mapped_column(JSON, default=list)
    package_summary: Mapped[dict] = mapped_column(JSON, default=dict)
    pdf_export_path: Mapped[str | None] = mapped_column(String(500), nullable=True)
    disclaimer_ack: Mapped[bool] = mapped_column(Boolean, default=True)
    
    status_history: Mapped[list] = mapped_column(JSON, default=list)
    external_submission_details: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    operator_notes: Mapped[str | None] = mapped_column(String(500), nullable=True)
    
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc)
    )


    # Relationships
    citizen: Mapped["Citizen"] = relationship("Citizen", back_populates="applications")
    scheme: Mapped["Scheme"] = relationship("Scheme", back_populates="applications")
    document_links: Mapped[list["DraftDocumentLink"]] = relationship("DraftDocumentLink", back_populates="draft", cascade="all, delete-orphan")
    follow_ups: Mapped[list["FollowUpRecord"]] = relationship("FollowUpRecord", back_populates="draft", cascade="all, delete-orphan")


class DraftDocumentLink(Base):
    __tablename__ = "draft_document_links"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    application_draft_id: Mapped[str] = mapped_column(String(36), ForeignKey("application_drafts.id", ondelete="CASCADE"))
    document_record_id: Mapped[str] = mapped_column(String(36), ForeignKey("document_records.id", ondelete="CASCADE"))
    attached_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    # Relationships
    draft: Mapped["ApplicationDraft"] = relationship("ApplicationDraft", back_populates="document_links")
    document: Mapped["DocumentRecord"] = relationship("DocumentRecord", back_populates="draft_links")
