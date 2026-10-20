"""Citizen and CitizenProfile models."""
import uuid
from datetime import datetime, timezone
from sqlalchemy import String, Integer, Float, Boolean, DateTime, ForeignKey, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base


class Citizen(Base):
    __tablename__ = "citizens"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    session_id: Mapped[str | None] = mapped_column(String(64), unique=True, nullable=True, index=True)
    phone_hash: Mapped[str | None] = mapped_column(String(64), unique=True, nullable=True, index=True)
    preferred_language: Mapped[str] = mapped_column(String(10), default="hi")
    consent_granted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    # Relationships
    profile: Mapped["CitizenProfile | None"] = relationship("CitizenProfile", back_populates="citizen", uselist=False, cascade="all, delete-orphan")
    applications: Mapped[list["ApplicationDraft"]] = relationship("ApplicationDraft", back_populates="citizen", cascade="all, delete-orphan")
    documents: Mapped[list["DocumentRecord"]] = relationship("DocumentRecord", back_populates="citizen", cascade="all, delete-orphan")
    follow_ups: Mapped[list["FollowUpRecord"]] = relationship("FollowUpRecord", back_populates="citizen", cascade="all, delete-orphan")


class CitizenProfile(Base):
    __tablename__ = "citizen_profiles"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    citizen_id: Mapped[str] = mapped_column(String(36), ForeignKey("citizens.id", ondelete="CASCADE"), unique=True)
    
    age: Mapped[int | None] = mapped_column(Integer, nullable=True)
    state: Mapped[str | None] = mapped_column(String(100), nullable=True)
    district: Mapped[str | None] = mapped_column(String(100), nullable=True)
    land_acres: Mapped[float | None] = mapped_column(Float, nullable=True)
    land_type: Mapped[str | None] = mapped_column(String(50), nullable=True)  # irrigated, rainfed
    annual_income: Mapped[float | None] = mapped_column(Float, nullable=True)
    ration_card_type: Mapped[str | None] = mapped_column(String(50), nullable=True)  # BPL, APL, Antyodaya
    occupation: Mapped[str | None] = mapped_column(String(100), nullable=True)  # farmer, artisan, student, etc.
    social_category: Mapped[str | None] = mapped_column(String(50), nullable=True)  # General, OBC, SC, ST
    gender: Mapped[str | None] = mapped_column(String(20), nullable=True)  # female, male, other
    is_income_tax_payer: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    has_pucca_house: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    owns_agricultural_land: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    has_girl_child_under_10: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    has_existing_lpg: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    enrolled_in_crop_insurance: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    residence_type: Mapped[str | None] = mapped_column(String(20), nullable=True)  # RURAL, URBAN
    bis_verified: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    awaas_plus_verified: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    
    is_confirmed: Mapped[bool] = mapped_column(Boolean, default=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc)
    )

    # Relationships
    citizen: Mapped["Citizen"] = relationship("Citizen", back_populates="profile")
