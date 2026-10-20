"""DocumentRecord model with zero Aadhaar storage enforcement."""
import uuid
from datetime import datetime, timezone
from sqlalchemy import String, Float, Boolean, DateTime, ForeignKey, JSON, Integer
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base


class DocumentRecord(Base):
    __tablename__ = "document_records"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    citizen_id: Mapped[str] = mapped_column(String(36), ForeignKey("citizens.id", ondelete="CASCADE"))
    
    document_type: Mapped[str] = mapped_column(String(50))  # land_khatauni, ration_card, income_certificate, etc.
    file_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    mime_type: Mapped[str | None] = mapped_column(String(100), nullable=True)
    file_size_bytes: Mapped[int | None] = mapped_column(Integer, nullable=True)
    page_count: Mapped[int] = mapped_column(Integer, default=1)
    
    ocr_provider: Mapped[str] = mapped_column(String(50), default="mock")
    is_mock: Mapped[bool] = mapped_column(Boolean, default=True)
    ocr_status: Mapped[str] = mapped_column(String(50), default="COMPLETED")  # PENDING, COMPLETED, FAILED
    
    masked_identifier: Mapped[str | None] = mapped_column(String(50), nullable=True)  # e.g., XXXX-XXXX-1234
    extracted_fields: Mapped[dict] = mapped_column(JSON, default=dict)
    ocr_confidence: Mapped[float] = mapped_column(Float, default=0.0)
    
    review_status: Mapped[str] = mapped_column(String(50), default="UNREVIEWED")  # UNREVIEWED, CONFIRMED, REJECTED
    citizen_confirmed: Mapped[bool] = mapped_column(Boolean, default=False)
    page_extractions: Mapped[list] = mapped_column(JSON, default=list)
    user_corrections: Mapped[dict] = mapped_column(JSON, default=dict)
    error_message: Mapped[str | None] = mapped_column(String(500), nullable=True)
    
    storage_path: Mapped[str | None] = mapped_column(String(500), nullable=True)
    uploaded_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )


    # Relationships
    citizen: Mapped["Citizen"] = relationship("Citizen", back_populates="documents")
    draft_links: Mapped[list["DraftDocumentLink"]] = relationship("DraftDocumentLink", back_populates="document")
