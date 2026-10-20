"""Test that database persistence survives backend application restarts."""
import os
import tempfile
import pytest
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy import select

from app.database.base import Base
from app.models.citizen import Citizen, CitizenProfile
import app.models  # noqa: F401


@pytest.mark.asyncio
async def test_database_persistence_across_restarts():
    # Create a temporary sqlite file
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp:
        db_path = tmp.name

    db_url = f"sqlite+aiosqlite:///{db_path}"

    try:
        # Phase A: First lifecycle of the server
        engine_1 = create_async_engine(db_url, echo=False)
        async_session_maker_1 = async_sessionmaker(engine_1, expire_on_commit=False, class_=AsyncSession)

        async with engine_1.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

        citizen_id = "test-citizen-persistent-uuid"
        session_id = "sess_restart_test_123"

        async with async_session_maker_1() as session:
            citizen = Citizen(
                id=citizen_id,
                session_id=session_id,
                preferred_language="hi",
            )
            session.add(citizen)
            profile = CitizenProfile(
                citizen_id=citizen_id,
                age=50,
                state="Uttar Pradesh",
                district="Mathura",
                land_acres=2.5,
                occupation="farmer",
                is_confirmed=True,
            )
            session.add(profile)
            await session.commit()

        # Simulate shutdown: dispose engine
        await engine_1.dispose()

        # Phase B: Second lifecycle of the server (Application Restart)
        engine_2 = create_async_engine(db_url, echo=False)
        async_session_maker_2 = async_sessionmaker(engine_2, expire_on_commit=False, class_=AsyncSession)

        # Call init_db logic again (CREATE TABLE IF NOT EXISTS)
        async with engine_2.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

        async with async_session_maker_2() as session:
            # Verify record was preserved across restart
            result = await session.execute(select(Citizen).where(Citizen.id == citizen_id))
            saved_citizen = result.scalar_one_or_none()
            assert saved_citizen is not None, "Citizen record must survive server restart"
            assert saved_citizen.session_id == session_id

            prof_result = await session.execute(select(CitizenProfile).where(CitizenProfile.citizen_id == citizen_id))
            saved_profile = prof_result.scalar_one_or_none()
            assert saved_profile is not None, "Profile record must survive server restart"
            assert saved_profile.age == 50
            assert saved_profile.land_acres == 2.5

        await engine_2.dispose()

    finally:
        if os.path.exists(db_path):
            os.remove(db_path)
