"""Citizen profile endpoints with session-based authorization guards."""
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, Header, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.database.session import get_db
from app.models.citizen import Citizen, CitizenProfile
from app.schemas.profile import CitizenProfileDTO, ProfileUpdateRequest, ProfileUpdateResponse

router = APIRouter(prefix="/profile", tags=["Profile"])


async def verify_citizen_session(
    citizen_id: str,
    session_id: str | None,
    db: AsyncSession,
) -> Citizen:
    """Verifies that the caller owns the requested citizen record via session token."""
    result = await db.execute(select(Citizen).where(Citizen.id == citizen_id))
    citizen = result.scalar_one_or_none()

    if not citizen:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="नागरिक नहीं मिला (Citizen not found)",
        )

    # Require active session and strictly matching session_id
    if not citizen.session_id or not session_id or citizen.session_id != session_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="अनधिकृत पहुँच: सत्र अमान्य, अनुपस्थित या बेमेल है (Unauthorized: Session ID invalid, missing, or mismatch)",
        )

    return citizen



@router.get("/{citizen_id}", response_model=CitizenProfileDTO)
async def get_profile(
    citizen_id: str,
    x_session_id: str | None = Header(default=None, alias="X-Session-ID"),
    db: AsyncSession = Depends(get_db),
) -> CitizenProfileDTO:
    """Fetch the active demographic profile for a citizen with ownership verification."""
    await verify_citizen_session(citizen_id, x_session_id, db)

    result = await db.execute(select(CitizenProfile).where(CitizenProfile.citizen_id == citizen_id))
    profile = result.scalar_one_or_none()

    if not profile:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="नागरिक प्रोफ़ाइल नहीं मिली (Citizen profile not found)",
        )

    return CitizenProfileDTO(
        id=profile.id,
        citizen_id=profile.citizen_id,
        age=profile.age,
        state=profile.state,
        district=profile.district,
        land_acres=profile.land_acres,
        land_type=profile.land_type,
        annual_income=profile.annual_income,
        ration_card_type=profile.ration_card_type,
        occupation=profile.occupation,
        social_category=profile.social_category,
        gender=profile.gender,
        is_income_tax_payer=profile.is_income_tax_payer,
        has_pucca_house=profile.has_pucca_house,
        owns_agricultural_land=profile.owns_agricultural_land,
        has_girl_child_under_10=profile.has_girl_child_under_10,
        has_existing_lpg=profile.has_existing_lpg,
        enrolled_in_crop_insurance=profile.enrolled_in_crop_insurance,
        residence_type=profile.residence_type,
        bis_verified=profile.bis_verified,
        awaas_plus_verified=profile.awaas_plus_verified,
        is_confirmed=profile.is_confirmed,
        updated_at=profile.updated_at,
    )


@router.put("/{citizen_id}", response_model=ProfileUpdateResponse)
async def update_profile(
    citizen_id: str,
    payload: ProfileUpdateRequest,
    x_session_id: str | None = Header(default=None, alias="X-Session-ID"),
    db: AsyncSession = Depends(get_db),
) -> ProfileUpdateResponse:
    """Update citizen profile attributes with server-side validation and ownership verification."""
    await verify_citizen_session(citizen_id, x_session_id, db)

    result = await db.execute(select(CitizenProfile).where(CitizenProfile.citizen_id == citizen_id))
    profile = result.scalar_one_or_none()

    if not profile:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="नागरिक प्रोफ़ाइल नहीं मिली (Citizen profile not found)",
        )

    # Apply validated updates
    update_data = payload.model_dump(exclude_unset=True)
    for field, val in update_data.items():
        setattr(profile, field, val)

    profile.updated_at = datetime.now(timezone.utc)
    await db.commit()
    await db.refresh(profile)

    dto = CitizenProfileDTO(
        id=profile.id,
        citizen_id=profile.citizen_id,
        age=profile.age,
        state=profile.state,
        district=profile.district,
        land_acres=profile.land_acres,
        land_type=profile.land_type,
        annual_income=profile.annual_income,
        ration_card_type=profile.ration_card_type,
        occupation=profile.occupation,
        social_category=profile.social_category,
        gender=profile.gender,
        is_income_tax_payer=profile.is_income_tax_payer,
        has_pucca_house=profile.has_pucca_house,
        owns_agricultural_land=profile.owns_agricultural_land,
        has_girl_child_under_10=profile.has_girl_child_under_10,
        has_existing_lpg=profile.has_existing_lpg,
        enrolled_in_crop_insurance=profile.enrolled_in_crop_insurance,
        residence_type=profile.residence_type,
        bis_verified=profile.bis_verified,
        awaas_plus_verified=profile.awaas_plus_verified,
        is_confirmed=profile.is_confirmed,
        updated_at=profile.updated_at,
    )

    return ProfileUpdateResponse(status="success", profile=dto)
