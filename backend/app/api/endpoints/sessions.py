import os
import uuid
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.database.session import get_db
from app.models.citizen import Citizen, CitizenProfile
from app.models.document import DocumentRecord
from app.models.application import ApplicationDraft

from app.schemas.session import (
    SessionInitRequest,
    SessionInitResponse,
    SessionTerminateRequest,
    SessionTerminateResponse,
)
from app.services.voice.session_manager import VoiceSessionManager


router = APIRouter(prefix="/sessions", tags=["Sessions & Consent"])


@router.post("/init", response_model=SessionInitResponse)
async def init_session(
    payload: SessionInitRequest,
    db: AsyncSession = Depends(get_db),
) -> SessionInitResponse:
    """Initialize a citizen session with explicit consent tracking."""
    session_id = f"sess_{uuid.uuid4().hex[:12]}"
    now = datetime.now(timezone.utc)
    
    citizen = Citizen(
        id=str(uuid.uuid4()),
        session_id=session_id,
        preferred_language=payload.preferred_language,
        consent_granted_at=now if payload.consent_given else None,
        created_at=now,
    )
    db.add(citizen)
    
    # Also initialize an empty profile for this citizen
    profile = CitizenProfile(
        id=str(uuid.uuid4()),
        citizen_id=citizen.id,
        is_confirmed=False,
    )
    db.add(profile)
    
    await db.commit()
    await db.refresh(citizen)

    return SessionInitResponse(
        session_id=session_id,
        citizen_id=citizen.id,
        preferred_language=citizen.preferred_language,
        consent_granted_at=citizen.consent_granted_at,
        status="active",
        message="नागरिक सत्र सफलतापूर्वक प्रारंभ हुआ (Citizen session initialized)",
    )


@router.post("/terminate", response_model=SessionTerminateResponse)
async def terminate_session(
    payload: SessionTerminateRequest,
    db: AsyncSession = Depends(get_db),
) -> SessionTerminateResponse:
    """Purge citizen session data immediately (Shared Kiosk / End Session action)."""
    # Genuinely locate and delete the citizen record and all cascaded data
    result = await db.execute(select(Citizen).where(Citizen.session_id == payload.session_id))
    citizen = result.scalar_one_or_none()

    if citizen:
        # Purge citizen document files from disk
        doc_res = await db.execute(select(DocumentRecord).where(DocumentRecord.citizen_id == citizen.id))
        for d in doc_res.scalars().all():
            if d.storage_path and os.path.exists(d.storage_path):
                try:
                    os.remove(d.storage_path)
                except OSError:
                    pass

        # Purge generated application package PDFs from disk
        draft_res = await db.execute(select(ApplicationDraft).where(ApplicationDraft.citizen_id == citizen.id))
        for dr in draft_res.scalars().all():
            if dr.pdf_export_path and os.path.exists(dr.pdf_export_path):
                try:
                    os.remove(dr.pdf_export_path)
                except OSError:
                    pass

        await db.delete(citizen)
        await db.commit()

    # Purge volatile voice session state
    VoiceSessionManager.clear_session(payload.session_id)


    return SessionTerminateResponse(
        session_id=payload.session_id,
        status="terminated",
        message="सत्र समाप्त और डेटा सफलतापूर्वक हटा दिया गया (Session ended and data wiped)",
        data_purged=True,
    )
