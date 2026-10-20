"""Voice Assistant API endpoints powered by LangGraph orchestration.

Adheres strictly to:
- Zero raw audio retention (purged immediately in memory/finally blocks)
- Consent-gated execution
- Explicit confirmation gating before profile persistence
- Deterministic scheme eligibility (strictly through EligibilityEngine)
"""
import base64
from datetime import datetime, timezone
from typing import Any
from fastapi import APIRouter, Depends, Header, HTTPException, Request, UploadFile, File, Form, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.config import settings
from app.database.session import get_db
from app.models.citizen import Citizen, CitizenProfile
from app.schemas.voice import (
    VoiceTranscribeRequest,
    VoiceTranscribeResponse,
    VoiceTurnRequest,
    VoiceTurnResponse,
    VoiceSpeakRequest,
    VoiceSpeakResponse,
    VoiceProvidersInfoResponse,
)
from app.services.voice import get_stt_provider, get_tts_provider
from app.services.voice.session_manager import VoiceSessionManager
from app.services.voice.graph import voice_assistant_graph, VoiceGraphState

router = APIRouter(prefix="/voice", tags=["Voice Assistant"])

ALLOWED_AUDIO_MIMES = {
    "audio/webm",
    "audio/wav",
    "audio/x-wav",
    "audio/wave",
    "audio/mp3",
    "audio/mpeg",
    "audio/ogg",
    "audio/x-m4a",
    "audio/m4a",
    "audio/mp4",
}


def _profile_to_dict(profile: CitizenProfile | None) -> dict[str, Any]:
    """Helper to convert CitizenProfile SQLAlchemy instance to clean dictionary."""
    if not profile:
        return {}
    return {
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
        "residence_type": profile.residence_type,
        "bis_verified": profile.bis_verified,
        "awaas_plus_verified": profile.awaas_plus_verified,
        "is_confirmed": profile.is_confirmed,
    }


@router.get("/providers", response_model=VoiceProvidersInfoResponse)
async def get_voice_providers() -> VoiceProvidersInfoResponse:
    """Returns runtime capability and provider information."""
    stt = get_stt_provider()
    tts = get_tts_provider()
    is_mock = getattr(stt, "is_mock", False) or type(stt).__name__ == "MockSTTProvider"
    return VoiceProvidersInfoResponse(
        stt_provider=settings.STT_PROVIDER,
        tts_provider=settings.TTS_PROVIDER,
        llm_provider=settings.LLM_PROVIDER,
        is_mock=is_mock,
        supported_languages=["hi", "en"],
        audio_limits={
            "max_file_size_bytes": settings.MAX_VOICE_FILE_SIZE_BYTES,
            "max_duration_seconds": settings.MAX_VOICE_DURATION_SECONDS,
            "max_conversation_turns": settings.MAX_CONVERSATION_TURNS,
            "supported_mime_types": sorted(list(ALLOWED_AUDIO_MIMES)),
        },
    )


@router.post("/transcribe", response_model=VoiceTranscribeResponse)
async def transcribe_audio(
    request: Request,
    x_session_id: str | None = Header(default=None, alias="X-Session-ID"),
    db: AsyncSession = Depends(get_db),
) -> VoiceTranscribeResponse:
    """Transcribes citizen speech to text with strict audio payload validation."""
    if x_session_id:
        result = await db.execute(select(Citizen).where(Citizen.session_id == x_session_id))
        citizen = result.scalar_one_or_none()
        if not citizen:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="अमान्य या समाप्त सत्र (Citizen session not found)",
            )
        if not citizen.consent_granted_at:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="सहमति आवश्यक है (Consent required before audio transcription)",
            )

    content_type = request.headers.get("content-type", "")
    audio_bytes: bytes | None = None
    mutable_audio: bytearray | None = None
    mime_type: str = "audio/webm"
    lang: str = "hi"

    try:
        if "multipart/form-data" in content_type:
            form = await request.form()
            file = form.get("file")
            lang = str(form.get("language", "hi"))
            if isinstance(file, UploadFile):
                mime_type = file.content_type or "audio/webm"
                audio_bytes = await file.read()
            elif isinstance(file, (bytes, bytearray)):
                audio_bytes = bytes(file)
        else:
            try:
                body = await request.json()
            except Exception:
                body = {}
            if not body or not body.get("audio_base64"):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="ऑडियो डेटा आवश्यक है (Audio data required)",
                )
            mime_type = body.get("audio_mime_type", "audio/webm")
            lang = body.get("language", "hi")
            try:
                audio_bytes = base64.b64decode(body["audio_base64"])
            except Exception as e:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"अमान्य बेस64 ऑडियो डेटा (Invalid base64 audio data): {str(e)}",
                )

        if not audio_bytes:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="ऑडियो डेटा आवश्यक है (Audio data required)",
            )

        # Enforce MIME type validation
        clean_mime = (mime_type or "audio/webm").split(";")[0].strip().lower()
        if clean_mime not in ALLOWED_AUDIO_MIMES:
            raise HTTPException(
                status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
                detail=f"असमर्थित ऑडियो प्रारूप: {clean_mime} (Supported: {', '.join(sorted(ALLOWED_AUDIO_MIMES))})",
            )

        # Enforce size limits
        if len(audio_bytes) > settings.MAX_VOICE_FILE_SIZE_BYTES:
            raise HTTPException(
                status_code=status.HTTP_413_CONTENT_TOO_LARGE,
                detail=f"ऑडियो फ़ाइल अधिकतम आकार ({settings.MAX_VOICE_FILE_SIZE_BYTES // (1024*1024)}MB) से अधिक है",
            )

        mutable_audio = bytearray(audio_bytes)

        stt = get_stt_provider()
        res = await stt.transcribe(
            audio_bytes=bytes(mutable_audio),
            mime_type=clean_mime,
            language=lang,
        )

        return VoiceTranscribeResponse(
            transcript=res.transcript,
            confidence=res.confidence,
            language=res.language,
            is_mock=res.is_mock,
            duration_seconds=res.duration_seconds,
        )
    finally:
        # Ephemeral in-memory mitigation: in-place buffer zero-filling pass to minimize retention exposure
        if mutable_audio is not None:
            for i in range(len(mutable_audio)):
                mutable_audio[i] = 0
            mutable_audio.clear()
        if audio_bytes is not None:
            del audio_bytes


@router.post("/speak", response_model=VoiceSpeakResponse)
async def synthesize_speech(payload: VoiceSpeakRequest) -> VoiceSpeakResponse:
    """Synthesizes text into spoken audio."""
    if not payload.text.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="भाषण के लिए पाठ आवश्यक है (Text required for speech synthesis)",
        )

    tts = get_tts_provider()
    res = await tts.synthesize(text=payload.text, language=payload.language)

    return VoiceSpeakResponse(
        audio_base64=res.audio_base64,
        audio_format=res.audio_format,
        spoken_text=res.spoken_text,
        is_mock=res.is_mock,
        browser_tts_recommended=getattr(res, "browser_tts_recommended", True),
    )



@router.post("/turn", response_model=VoiceTurnResponse)
async def voice_assistant_turn(
    payload: VoiceTurnRequest,
    x_session_id: str | None = Header(default=None, alias="X-Session-ID"),
    db: AsyncSession = Depends(get_db),
) -> VoiceTurnResponse:
    """Executes one step in the LangGraph Voice Assistant conversation.
    
    1. Validates citizen session & consent.
    2. Runs LangGraph state machine.
    3. Persists profile updates only when confirmed.
    4. Evaluates eligibility through deterministic engine.
    5. Returns audio/text bilingual guidance.
    """
    if not x_session_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="सत्र टोकन अनुपस्थित है (X-Session-ID header required)",
        )

    # Fetch citizen
    result = await db.execute(select(Citizen).where(Citizen.session_id == x_session_id))
    citizen = result.scalar_one_or_none()
    if not citizen:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="अमान्य या समाप्त सत्र (Citizen session not found)",
        )

    # Consent validation guard
    if not citizen.consent_granted_at:
        return VoiceTurnResponse(
            session_id=x_session_id,
            citizen_id=citizen.id,
            turn_count=0,
            status="awaiting_consent",
            transcript=None,
            response_text_hi="सहायक वॉइस सेवा का उपयोग करने के लिए कृपया पहले अपनी सहमति प्रदान करें।",
            response_text_en="Please grant consent to access voice assistance.",
            provider_info={"workflow": "LangGraph", "consent": "required"},
        )

    # Fetch citizen profile
    prof_result = await db.execute(select(CitizenProfile).where(CitizenProfile.citizen_id == citizen.id))
    profile = prof_result.scalar_one_or_none()

    current_profile_dict = _profile_to_dict(profile)

    # Retrieve or create session in-memory state
    session_state = VoiceSessionManager.get_or_create(
        session_id=x_session_id,
        citizen_id=citizen.id,
        language=payload.preferred_language,
    )

    # Decode audio if provided
    audio_bytes: bytes | None = None
    mutable_audio: bytearray | None = None
    clean_mime = (payload.audio_mime_type or "audio/webm").split(";")[0].strip().lower()

    if payload.audio_base64:
        if clean_mime not in ALLOWED_AUDIO_MIMES:
            raise HTTPException(
                status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
                detail=f"असमर्थित ऑडियो प्रारूप: {clean_mime} (Supported: {', '.join(sorted(ALLOWED_AUDIO_MIMES))})",
            )
        try:
            raw_decoded = base64.b64decode(payload.audio_base64)
            mutable_audio = bytearray(raw_decoded)
            del raw_decoded
            if len(mutable_audio) > settings.MAX_VOICE_FILE_SIZE_BYTES:
                raise HTTPException(
                    status_code=status.HTTP_413_CONTENT_TOO_LARGE,
                    detail=f"ऑडियो फ़ाइल अधिकतम आकार ({settings.MAX_VOICE_FILE_SIZE_BYTES // (1024*1024)}MB) से अधिक है",
                )
            audio_bytes = bytes(mutable_audio)
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"अमान्य बेस64 ऑडियो डेटा (Invalid audio base64): {str(e)}",
            )

    try:
        initial_state: VoiceGraphState = {
            "session_id": x_session_id,
            "citizen_id": citizen.id,
            "preferred_language": payload.preferred_language,
            "consent_given": True,
            "input_mode": "voice" if audio_bytes else "text",
            "user_input_text": payload.text,
            "audio_bytes": audio_bytes,
            "audio_mime_type": clean_mime,
            "request_tts": payload.request_tts,
            "turn_count": session_state.turn_count,
            "max_turns": session_state.max_turns,
            "last_asked_field": session_state.last_asked_field,
            "skipped_fields": list(session_state.skipped_fields),
            "current_profile": current_profile_dict,
            "proposed_profile_updates": dict(session_state.proposed_profile_updates),
            "is_profile_confirmed": payload.confirmed_by_user is True,
            "status": "ready",
            "evaluated_schemes": [],
        }

        # Run LangGraph workflow
        final_state: dict[str, Any] = await voice_assistant_graph.ainvoke(initial_state)

        # Update in-memory state
        session_state.turn_count = final_state.get("turn_count", session_state.turn_count) + 1
        if final_state.get("last_asked_field"):
            session_state.last_asked_field = final_state.get("last_asked_field")
        if final_state.get("skipped_fields"):
            session_state.skipped_fields = list(final_state.get("skipped_fields"))
        
        # Check proposed profile updates
        proposed = final_state.get("proposed_profile_updates") or {}
        session_state.proposed_profile_updates = dict(proposed)

        # Record conversation history
        user_spoken_or_written = final_state.get("transcript") or payload.text or ""
        assistant_reply = final_state.get("response_text_hi", "")
        session_state.record_turn(
            user_text=user_spoken_or_written,
            assistant_text=assistant_reply,
            updates=final_state.get("persisted_profile_updates", {}),
        )

        # If profile updates were confirmed, persist them to the database
        persisted = final_state.get("persisted_profile_updates") or {}
        if persisted and profile:
            for field, val in persisted.items():
                if hasattr(profile, field):
                    setattr(profile, field, val)
            profile.is_confirmed = True
            profile.updated_at = datetime.now(timezone.utc)
            await db.commit()
            await db.refresh(profile)
            session_state.proposed_profile_updates = {}

        return VoiceTurnResponse(
            session_id=x_session_id,
            citizen_id=citizen.id,
            turn_count=session_state.turn_count,
            status=final_state.get("status", "ready"),
            transcript=final_state.get("transcript"),
            transcript_confidence=final_state.get("transcript_confidence", 1.0),
            intent=final_state.get("intent"),
            proposed_profile_updates=final_state.get("proposed_profile_updates", {}),
            persisted_profile_updates=persisted,
            is_profile_confirmed=bool(final_state.get("is_profile_confirmed", False)),
            follow_up_field=final_state.get("follow_up_field"),
            follow_up_question_hi=final_state.get("follow_up_question_hi"),
            follow_up_question_en=final_state.get("follow_up_question_en"),
            evaluated_schemes=final_state.get("evaluated_schemes", []),
            response_text_hi=final_state.get("response_text_hi", ""),
            response_text_en=final_state.get("response_text_en", ""),
            audio_base64=final_state.get("spoken_audio_base64"),
            audio_format=final_state.get("spoken_audio_format", "audio/wav"),
            browser_tts_recommended=final_state.get("browser_tts_recommended", True),
            provider_info=final_state.get("provider_info", {}),
            error_message=final_state.get("error_message"),
        )
    finally:
        # Ephemeral in-memory mitigation: in-place buffer zero-filling pass to minimize retention exposure
        if mutable_audio is not None:
            for i in range(len(mutable_audio)):
                mutable_audio[i] = 0
            mutable_audio.clear()
        if audio_bytes is not None:
            del audio_bytes
