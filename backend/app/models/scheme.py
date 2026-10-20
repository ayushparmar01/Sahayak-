"""Scheme and SchemeRule models."""
import uuid
from datetime import date
from sqlalchemy import String, Float, Boolean, Date, Integer, ForeignKey, JSON, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base


class Scheme(Base):
    __tablename__ = "schemes"

    id: Mapped[str] = mapped_column(String(50), primary_key=True)  # e.g., "pm-kisan"
    code: Mapped[str] = mapped_column(String(50), unique=True, index=True)  # e.g., "PM_KISAN"
    name_hi: Mapped[str] = mapped_column(String(200))
    name_en: Mapped[str] = mapped_column(String(200))
    ministry: Mapped[str] = mapped_column(String(200))
    official_portal_url: Mapped[str] = mapped_column(String(500))
    benefit_summary_hi: Mapped[str] = mapped_column(Text)
    benefit_summary_en: Mapped[str] = mapped_column(Text)
    max_annual_benefit_inr: Mapped[float] = mapped_column(Float, default=0.0)
    benefit_type: Mapped[str] = mapped_column(String(50), default="DIRECT_CASH_TRANSFER")  # DIRECT_CASH_TRANSFER, HEALTH_INSURANCE_COVER, CONCESSIONAL_CREDIT_LIMIT, ONE_TIME_ASSISTANCE, CROP_INSURANCE_COVER, SOCIAL_PENSION, SMALL_SAVINGS_DEPOSIT_LIMIT
    benefit_metric_label_hi: Mapped[str] = mapped_column(String(100), default="अधिकतम वार्षिक लाभ")
    benefit_metric_label_en: Mapped[str] = mapped_column(String(100), default="Max Annual Benefit")
    benefit_amount_display_hi: Mapped[str] = mapped_column(String(100), default="₹6,000")
    benefit_amount_display_en: Mapped[str] = mapped_column(String(100), default="₹6,000")
    jurisdiction: Mapped[str] = mapped_column(String(50), default="CENTRAL_SECTOR")  # CENTRAL_SECTOR, CENTRALLY_SPONSORED, STATE_GOVT
    category: Mapped[str] = mapped_column(String(50), default="GENERAL")  # AGRICULTURE, HEALTHCARE, HOUSING, WOMEN_CHILD, FINANCIAL_SECURITY, SOCIAL_WELFARE
    target_group_hi: Mapped[str] = mapped_column(String(200), default="")
    target_group_en: Mapped[str] = mapped_column(String(200), default="")
    application_process_hi: Mapped[str] = mapped_column(Text, default="")
    application_process_en: Mapped[str] = mapped_column(Text, default="")
    documents_required_json: Mapped[list] = mapped_column(JSON, default=list)
    caveats_hi: Mapped[str] = mapped_column(Text, default="")
    caveats_en: Mapped[str] = mapped_column(Text, default="")
    
    last_verified_date: Mapped[date] = mapped_column(Date)
    verification_source: Mapped[str] = mapped_column(String(200))
    verification_status: Mapped[str] = mapped_column(String(50), default="VERIFIED")  # VERIFIED, REVISION_PENDING, OUTDATED, UNKNOWN
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    rule_version: Mapped[int] = mapped_column(Integer, default=1)

    # Relationships
    rules: Mapped[list["SchemeRule"]] = relationship("SchemeRule", back_populates="scheme", cascade="all, delete-orphan")
    applications: Mapped[list["ApplicationDraft"]] = relationship("ApplicationDraft", back_populates="scheme")


class SchemeRule(Base):
    __tablename__ = "scheme_rules"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    scheme_id: Mapped[str] = mapped_column(String(50), ForeignKey("schemes.id", ondelete="CASCADE"))
    rule_code: Mapped[str] = mapped_column(String(50), default="RULE_DEFAULT")  # e.g. PMK_LAND_REQ
    rule_type: Mapped[str] = mapped_column(String(50))  # MANDATORY_CRITERION, EXCLUSION, DOCUMENT_REQ, EXTERNAL_VERIFICATION
    description_hi: Mapped[str] = mapped_column(Text, default="")
    description_en: Mapped[str] = mapped_column(Text, default="")
    source_citation: Mapped[str] = mapped_column(String(255), default="")
    rule_criteria_json: Mapped[dict] = mapped_column(JSON)
    failure_message_hi: Mapped[str] = mapped_column(Text)
    failure_message_en: Mapped[str] = mapped_column(Text)

    # Relationships
    scheme: Mapped["Scheme"] = relationship("Scheme", back_populates="rules")
