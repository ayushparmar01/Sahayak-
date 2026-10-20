"""CitizenProfile schemas."""
from datetime import datetime
from pydantic import BaseModel, Field


class CitizenProfileDTO(BaseModel):
    id: str | None = None
    citizen_id: str | None = None
    age: int | None = Field(default=None, ge=0, le=120)
    state: str | None = None
    district: str | None = None
    land_acres: float | None = Field(default=None, ge=0.0)
    land_type: str | None = None
    annual_income: float | None = Field(default=None, ge=0.0)
    ration_card_type: str | None = None
    occupation: str | None = None
    social_category: str | None = None
    gender: str | None = None
    is_income_tax_payer: bool | None = None
    has_pucca_house: bool | None = None
    owns_agricultural_land: bool | None = None
    has_girl_child_under_10: bool | None = None
    has_existing_lpg: bool | None = None
    enrolled_in_crop_insurance: bool | None = None
    residence_type: str | None = None
    bis_verified: bool | None = None
    awaas_plus_verified: bool | None = None
    is_confirmed: bool = False
    updated_at: datetime | None = None


class ProfileUpdateRequest(BaseModel):
    age: int | None = Field(default=None, ge=0, le=120)
    state: str | None = None
    district: str | None = None
    land_acres: float | None = Field(default=None, ge=0.0)
    land_type: str | None = None
    annual_income: float | None = Field(default=None, ge=0.0)
    ration_card_type: str | None = None
    occupation: str | None = None
    social_category: str | None = None
    gender: str | None = None
    is_income_tax_payer: bool | None = None
    has_pucca_house: bool | None = None
    owns_agricultural_land: bool | None = None
    has_girl_child_under_10: bool | None = None
    has_existing_lpg: bool | None = None
    enrolled_in_crop_insurance: bool | None = None
    residence_type: str | None = None
    bis_verified: bool | None = None
    awaas_plus_verified: bool | None = None
    is_confirmed: bool = False


class ProfileUpdateResponse(BaseModel):
    status: str = "success"
    profile: CitizenProfileDTO
