"""Eligibility assessment API endpoint utilizing the Deterministic Rules Engine."""
from fastapi import APIRouter, Depends, Header, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.database.session import get_db
from app.models.citizen import Citizen, CitizenProfile
from app.models.scheme import Scheme
from app.api.endpoints.schemes import ensure_schemes_seeded
from app.schemas.eligibility import EligibilityAssessRequest, EligibilityAssessResponse
from app.services.eligibility_engine import EligibilityEngine

router = APIRouter(prefix="/eligibility", tags=["Eligibility Engine"])


@router.post("/assess", response_model=EligibilityAssessResponse)
async def assess_scheme_eligibility(
    payload: EligibilityAssessRequest,
    x_session_id: str | None = Header(default=None, alias="X-Session-ID"),
    db: AsyncSession = Depends(get_db),
) -> EligibilityAssessResponse:
    """Evaluates citizen eligibility for a specific scheme using deterministic backend rules.
    Requires an authorized session ID (X-Session-ID header) to prevent unauthorized profile evaluation.
    """
    if not x_session_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="सत्र टोकन अनुपलब्ध (Missing X-Session-ID header)",
        )

    # Verify session ownership
    result = await db.execute(
        select(Citizen).where(Citizen.session_id == x_session_id).options(selectinload(Citizen.profile))
    )
    citizen = result.scalar_one_or_none()

    if not citizen:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="अमान्य या समाप्त सत्र (Invalid or expired session)",
        )

    # Ensure schemes are seeded in database
    await ensure_schemes_seeded(db)

    # Fetch scheme details
    s_result = await db.execute(
        select(Scheme).where(Scheme.id == payload.scheme_id).options(selectinload(Scheme.rules))
    )
    scheme = s_result.scalar_one_or_none()

    if not scheme:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"योजना आईडी '{payload.scheme_id}' नहीं मिली (Scheme not found)",
        )

    # Build profile context
    profile = citizen.profile
    profile_dict = {}
    if profile:
        profile_dict = {
            "age": profile.age,
            "state": profile.state,
            "district": profile.district,
            "land_acres": profile.land_acres,
            "land_type": profile.land_type,
            "annual_income": profile.annual_income,
            "ration_card_type": profile.ration_card_type,
            "occupation": profile.occupation,
            "social_category": profile.social_category,
            "gender": profile.gender,
            "is_income_tax_payer": profile.is_income_tax_payer,
            "has_pucca_house": profile.has_pucca_house,
            "owns_agricultural_land": profile.owns_agricultural_land,
            "has_girl_child_under_10": profile.has_girl_child_under_10,
            "has_existing_lpg": profile.has_existing_lpg,
            "enrolled_in_crop_insurance": profile.enrolled_in_crop_insurance,
            "is_confirmed": profile.is_confirmed,
        }

    # Apply temporary profile override if provided
    if payload.profile_override:
        profile_dict.update(payload.profile_override)

    # Execute deterministic evaluation
    assessment = EligibilityEngine.evaluate(scheme=scheme, profile=profile_dict)

    return assessment
