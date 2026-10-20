"""Test database models and persistence."""
import pytest
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.citizen import Citizen, CitizenProfile
from app.models.scheme import Scheme


@pytest.mark.asyncio
async def test_citizen_and_profile_creation(db_session: AsyncSession):
    citizen = Citizen(preferred_language="hi")
    db_session.add(citizen)
    await db_session.commit()
    await db_session.refresh(citizen)

    profile = CitizenProfile(
        citizen_id=citizen.id,
        age=45,
        state="Uttar Pradesh",
        district="Mathura",
        land_acres=2.0,
        occupation="farmer",
        is_confirmed=True,
    )
    db_session.add(profile)
    await db_session.commit()

    # Query back
    result = await db_session.execute(
        select(CitizenProfile).where(CitizenProfile.citizen_id == citizen.id)
    )
    fetched_profile = result.scalar_one_or_none()
    assert fetched_profile is not None
    assert fetched_profile.age == 45
    assert fetched_profile.state == "Uttar Pradesh"
    assert fetched_profile.land_acres == 2.0
    assert fetched_profile.is_confirmed is True
