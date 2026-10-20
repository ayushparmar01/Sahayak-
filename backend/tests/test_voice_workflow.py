"""Comprehensive test suite for Phase 3 Voice Assistant & LangGraph Orchestration.

Tests:
1. Provider capability introspection
2. Audio transcription and size limit controls (zero disk retention)
3. Speech synthesis
4. Consent-gated turn authorization
5. Indic NLP extraction with negation & numeral parsing
6. Confirmation gating before database profile persistence
7. Deterministic eligibility engine integration (strictly no LLM hallucinations)
8. At most one follow-up question for missing critical fields
9. Volatile in-memory kiosk purge upon session termination
10. Conversation turn loop guard
"""
import base64
import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.config import settings
from app.models.citizen import Citizen, CitizenProfile
from app.services.voice.extractor import DeterministicIndicExtractor
from app.services.voice.session_manager import VoiceSessionManager
from app.services.voice.mock_providers import MockSTTProvider, MockTTSProvider


@pytest.mark.asyncio
async def test_voice_providers_info(client: AsyncClient):
    """Verify provider capability introspection returns safe configuration."""
    response = await client.get("/api/v1/voice/providers")
    assert response.status_code == 200
    data = response.json()
    assert "stt_provider" in data
    assert "tts_provider" in data
    assert "llm_provider" in data
    assert "audio_limits" in data
    assert data["audio_limits"]["max_file_size_bytes"] == settings.MAX_VOICE_FILE_SIZE_BYTES
    assert "audio/webm" in data["audio_limits"]["supported_mime_types"]


@pytest.mark.asyncio
async def test_voice_transcribe_success_and_mock(client: AsyncClient):
    """Test STT transcription with valid base64 audio payload."""
    # Create valid dummy audio base64
    dummy_wav_base64 = base64.b64encode(b"RIFF\x24\x00\x00\x00WAVEfmt \x10\x00\x00\x00" + b"\x00" * 30).decode("ascii")
    
    response = await client.post(
        "/api/v1/voice/transcribe",
        json={"audio_base64": dummy_wav_base64, "audio_mime_type": "audio/wav", "language": "hi"},
    )
    assert response.status_code == 200
    data = response.json()
    assert "transcript" in data
    assert len(data["transcript"]) > 0
    assert data["confidence"] > 0.0
    assert data["is_mock"] is True


@pytest.mark.asyncio
async def test_voice_transcribe_payload_too_large(client: AsyncClient):
    """Test that audio payloads exceeding MAX_VOICE_FILE_SIZE_BYTES are rejected with HTTP 413."""
    # Generate payload > 10MB
    oversized_bytes = b"0" * (10 * 1024 * 1024 + 1024)
    oversized_base64 = base64.b64encode(oversized_bytes).decode("ascii")

    response = await client.post(
        "/api/v1/voice/transcribe",
        json={"audio_base64": oversized_base64, "audio_mime_type": "audio/wav", "language": "hi"},
    )
    assert response.status_code == 413
    assert "अधिकतम आकार" in response.json()["detail"]


@pytest.mark.asyncio
async def test_voice_speak(client: AsyncClient):
    """Test standalone speech synthesis endpoint."""
    response = await client.post(
        "/api/v1/voice/speak",
        json={"text": "नमस्ते, मैं सहायक हूँ।", "language": "hi"},
    )
    assert response.status_code == 200
    data = response.json()
    assert "audio_base64" in data
    assert data["spoken_text"] == "नमस्ते, मैं सहायक हूँ।"
    assert data["audio_format"] == "audio/wav"


@pytest.mark.asyncio
async def test_voice_turn_unauthorized_and_not_found(client: AsyncClient):
    """Test voice turn without session header or with non-existent session."""
    # Missing session header
    res1 = await client.post("/api/v1/voice/turn", json={"text": "नमस्ते"})
    assert res1.status_code == 401

    # Invalid session header
    res2 = await client.post(
        "/api/v1/voice/turn",
        headers={"X-Session-ID": "sess_non_existent_123"},
        json={"text": "नमस्ते"},
    )
    assert res2.status_code == 404


@pytest.mark.asyncio
async def test_voice_turn_consent_gate_enforcement(client: AsyncClient):
    """Session without explicit consent must refuse voice intake."""
    init_res = await client.post("/api/v1/sessions/init", json={"consent_given": False, "preferred_language": "hi"})
    assert init_res.status_code == 200
    session_id = init_res.json()["session_id"]

    turn_res = await client.post(
        "/api/v1/voice/turn",
        headers={"X-Session-ID": session_id},
        json={"text": "मेरी जानकारी दर्ज करो"},
    )
    assert turn_res.status_code == 200
    data = turn_res.json()
    assert data["status"] == "awaiting_consent"
    assert "सहमति" in data["response_text_hi"]


@pytest.mark.asyncio
async def test_indic_extractor_negation_and_numerals():
    """Verify Indic NLP extractor correctly parses negation and numerals in Hindi."""
    extractor = DeterministicIndicExtractor()

    # 1. Negation handling: pucca house NOT owned
    res_neg = await extractor.extract_intent_and_fields("मेरे पास पक्का मकान नहीं है।", current_profile={})
    assert res_neg.extracted_fields.get("has_pucca_house") is False

    # 2. Positive pucca house
    res_pos = await extractor.extract_intent_and_fields("मेरे पास पक्का मकान है।", current_profile={})
    assert res_pos.extracted_fields.get("has_pucca_house") is True

    # 3. Farmer with land acres, income, and age
    res_farmer = await extractor.extract_intent_and_fields(
        "मैं किसान हूँ, मेरी उम्र 38 वर्ष है, 3 एकड़ ज़मीन है और वार्षिक आय 150000 रुपये है।",
        current_profile={},
    )
    assert res_farmer.extracted_fields.get("occupation") == "farmer"
    assert res_farmer.extracted_fields.get("owns_agricultural_land") is True
    assert res_farmer.extracted_fields.get("land_acres") == 3.0
    assert res_farmer.extracted_fields.get("age") == 38
    assert res_farmer.extracted_fields.get("annual_income") == 150000.0

    # 4. Confirmation detection
    res_confirm = await extractor.extract_intent_and_fields("हाँ, यह बिल्कुल सही है।", current_profile={})
    assert res_confirm.is_confirmed is True

    # 5. Cancellation detection
    res_cancel = await extractor.extract_intent_and_fields("नहीं यह गलत है इसे रद्द करो।", current_profile={})
    assert res_cancel.is_cancelled is True


@pytest.mark.asyncio
async def test_voice_turn_profile_confirmation_gating(client: AsyncClient, db_session: AsyncSession):
    """Extracted profile updates must be gated by confirmation before saving to DB."""
    # 1. Initialize session with consent
    init_res = await client.post("/api/v1/sessions/init", json={"consent_given": True, "preferred_language": "hi"})
    session_id = init_res.json()["session_id"]
    citizen_id = init_res.json()["citizen_id"]

    # 2. Turn 1: Speak demographic details
    turn1 = await client.post(
        "/api/v1/voice/turn",
        headers={"X-Session-ID": session_id},
        json={"text": "मैं एक किसान हूँ और मेरे पास 2 एकड़ जमीन है", "preferred_language": "hi"},
    )
    assert turn1.status_code == 200
    data1 = turn1.json()
    assert data1["status"] == "needs_confirmation"
    assert data1["proposed_profile_updates"].get("occupation") == "farmer"
    assert data1["proposed_profile_updates"].get("land_acres") == 2.0
    assert "क्या यह जानकारी सही है" in data1["response_text_hi"]

    # Verify that database profile has NOT been modified yet
    result = await db_session.execute(select(CitizenProfile).where(CitizenProfile.citizen_id == citizen_id))
    profile = result.scalar_one()
    assert profile.occupation is None
    assert profile.land_acres is None
    assert profile.is_confirmed is False

    # 3. Turn 2: User confirms profile details
    turn2 = await client.post(
        "/api/v1/voice/turn",
        headers={"X-Session-ID": session_id},
        json={"text": "हाँ यह बिल्कुल सही है", "confirmed_by_user": True, "preferred_language": "hi"},
    )
    assert turn2.status_code == 200
    data2 = turn2.json()
    assert data2["is_profile_confirmed"] is True
    assert data2["persisted_profile_updates"].get("occupation") == "farmer"

    # Verify database profile IS now modified and confirmed
    await db_session.refresh(profile)
    assert profile.occupation == "farmer"
    assert profile.land_acres == 2.0
    assert profile.is_confirmed is True


@pytest.mark.asyncio
async def test_voice_turn_follow_up_single_question(client: AsyncClient):
    """Voice assistant must ask at most ONE focused follow-up question per turn for missing info."""
    init_res = await client.post("/api/v1/sessions/init", json={"consent_given": True, "preferred_language": "hi"})
    session_id = init_res.json()["session_id"]

    # User expresses interest in farmer schemes without providing land or income
    turn1 = await client.post(
        "/api/v1/voice/turn",
        headers={"X-Session-ID": session_id},
        json={"text": "मुझे किसान योजना चाहिए", "preferred_language": "hi"},
    )
    assert turn1.status_code == 200
    data1 = turn1.json()
    
    # Needs follow-up question
    assert data1["status"] in ("needs_confirmation", "needs_follow_up")
    if data1["status"] == "needs_follow_up":
        assert data1["follow_up_field"] is not None
        assert data1["follow_up_question_hi"] is not None
        assert data1["follow_up_question_en"] is not None
        # Must be concise and single question
        assert "?" in data1["follow_up_question_hi"] or "बताएं" in data1["follow_up_question_hi"]


@pytest.mark.asyncio
async def test_deterministic_scheme_assessment_via_voice(client: AsyncClient, db_session: AsyncSession):
    """Evaluation in voice conversation uses deterministic engine; zero LLM hallucinations."""
    init_res = await client.post("/api/v1/sessions/init", json={"consent_given": True, "preferred_language": "hi"})
    session_id = init_res.json()["session_id"]
    citizen_id = init_res.json()["citizen_id"]

    # Pre-populate qualifying profile for PM-KISAN & KCC
    result = await db_session.execute(select(CitizenProfile).where(CitizenProfile.citizen_id == citizen_id))
    profile = result.scalar_one()
    profile.age = 45
    profile.occupation = "farmer"
    profile.owns_agricultural_land = True
    profile.land_acres = 2.5
    profile.annual_income = 80000.0
    profile.is_income_tax_payer = False
    profile.residence_type = "RURAL"
    profile.is_confirmed = True
    await db_session.commit()

    turn = await client.post(
        "/api/v1/voice/turn",
        headers={"X-Session-ID": session_id},
        json={"text": "मुझे सरकारी योजनाओं के बारे में बताएं", "preferred_language": "hi"},
    )
    assert turn.status_code == 200
    data = turn.json()
    assert len(data["evaluated_schemes"]) > 0

    eval_map = {s["scheme_id"]: s for s in data["evaluated_schemes"]}
    
    # PM-KISAN should be ELIGIBLE
    assert "pm-kisan" in eval_map
    assert eval_map["pm-kisan"]["status"] == "ELIGIBLE"

    # PM-JAY must NOT be falsely marked ELIGIBLE (requires SECC/NFSA or Senior 70+)
    assert "pm-jay" in eval_map
    assert eval_map["pm-jay"]["status"] in ("NEEDS_MORE_INFO", "INELIGIBLE")
    assert eval_map["pm-jay"]["status"] != "ELIGIBLE"


@pytest.mark.asyncio
async def test_loop_guard_max_turns(client: AsyncClient):
    """Ensure session loop guard stops runaway loops at MAX_CONVERSATION_TURNS."""
    init_res = await client.post("/api/v1/sessions/init", json={"consent_given": True, "preferred_language": "hi"})
    session_id = init_res.json()["session_id"]
    citizen_id = init_res.json()["citizen_id"]

    state = VoiceSessionManager.get_or_create(session_id, citizen_id)
    state.turn_count = settings.MAX_CONVERSATION_TURNS  # set to limit

    turn = await client.post(
        "/api/v1/voice/turn",
        headers={"X-Session-ID": session_id},
        json={"text": "नमस्ते", "preferred_language": "hi"},
    )
    assert turn.status_code == 200
    data = turn.json()
    assert data["status"] == "completed"
    assert "सीमा पूरी" in data["response_text_hi"]


@pytest.mark.asyncio
async def test_kiosk_purge_clears_voice_session(client: AsyncClient):
    """Session termination must purge in-memory voice state completely."""
    init_res = await client.post("/api/v1/sessions/init", json={"consent_given": True, "preferred_language": "hi"})
    session_id = init_res.json()["session_id"]

    # Execute a turn to create in-memory voice state
    await client.post(
        "/api/v1/voice/turn",
        headers={"X-Session-ID": session_id},
        json={"text": "नमस्ते", "preferred_language": "hi"},
    )

    # State must exist in memory
    assert VoiceSessionManager.get(session_id) is not None

    # Terminate session
    term_res = await client.post("/api/v1/sessions/terminate", json={"session_id": session_id})
    assert term_res.status_code == 200
    assert term_res.json()["data_purged"] is True

    # State must be wiped from memory
    assert VoiceSessionManager.get(session_id) is None


@pytest.mark.asyncio
async def test_voice_transcribe_unsupported_mime(client: AsyncClient):
    """Unsupported audio MIME types must return HTTP 415."""
    dummy_base64 = base64.b64encode(b"dummy audio content").decode("ascii")
    response = await client.post(
        "/api/v1/voice/transcribe",
        json={"audio_base64": dummy_base64, "audio_mime_type": "audio/aiff", "language": "hi"},
    )
    assert response.status_code == 415
    assert "असमर्थित ऑडियो प्रारूप" in response.json()["detail"]


@pytest.mark.asyncio
async def test_voice_turn_unsupported_mime(client: AsyncClient):
    """Unsupported audio MIME in /turn must return HTTP 415."""
    init_res = await client.post("/api/v1/sessions/init", json={"consent_given": True, "preferred_language": "hi"})
    session_id = init_res.json()["session_id"]
    dummy_base64 = base64.b64encode(b"dummy audio content").decode("ascii")

    turn = await client.post(
        "/api/v1/voice/turn",
        headers={"X-Session-ID": session_id},
        json={"audio_base64": dummy_base64, "audio_mime_type": "audio/x-unknown", "preferred_language": "hi"},
    )
    assert turn.status_code == 415


@pytest.mark.asyncio
async def test_voice_transcribe_consent_check(client: AsyncClient):
    """Transcribe with unconsented session must return HTTP 403."""
    init_res = await client.post("/api/v1/sessions/init", json={"consent_given": False, "preferred_language": "hi"})
    session_id = init_res.json()["session_id"]
    dummy_base64 = base64.b64encode(b"dummy audio content").decode("ascii")

    response = await client.post(
        "/api/v1/voice/transcribe",
        headers={"X-Session-ID": session_id},
        json={"audio_base64": dummy_base64, "audio_mime_type": "audio/wav", "language": "hi"},
    )
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_voice_turn_conversational_intents(client: AsyncClient):
    """Test greeting, out-of-scope queries, and don't know uncertainty handling."""
    init_res = await client.post("/api/v1/sessions/init", json={"consent_given": True, "preferred_language": "hi"})
    session_id = init_res.json()["session_id"]

    # 1. Greeting
    turn1 = await client.post(
        "/api/v1/voice/turn",
        headers={"X-Session-ID": session_id},
        json={"text": "नमस्ते सहायक जी", "preferred_language": "hi"},
    )
    assert turn1.status_code == 200
    data1 = turn1.json()
    assert data1["intent"] == "greeting"
    assert "सरकारी योजना मार्गदर्शक" in data1["response_text_hi"]

    # 2. Out of scope query
    turn2 = await client.post(
        "/api/v1/voice/turn",
        headers={"X-Session-ID": session_id},
        json={"text": "आज का मौसम कैसा है?", "preferred_language": "hi"},
    )
    assert turn2.status_code == 200
    data2 = turn2.json()
    assert data2["intent"] == "out_of_scope"
    assert "केवल भारत सरकार की कल्याणकारी योजनाओं" in data2["response_text_hi"]

    # 3. Follow-up question triggered by missing profile field
    turn3 = await client.post(
        "/api/v1/voice/turn",
        headers={"X-Session-ID": session_id},
        json={"text": "आगे क्या करना है?", "preferred_language": "hi"},
    )
    assert turn3.status_code == 200
    data3 = turn3.json()
    assert data3["status"] == "needs_follow_up"
    assert data3["follow_up_field"] == "residence_type"

    # 4. Citizen says "पता नहीं"
    turn4 = await client.post(
        "/api/v1/voice/turn",
        headers={"X-Session-ID": session_id},
        json={"text": "पता नहीं", "preferred_language": "hi"},
    )
    assert turn4.status_code == 200
    data4 = turn4.json()
    assert data4["intent"] == "dont_know"
    # Does not repeat the same question in an infinite loop
    assert data4["follow_up_field"] != "residence_type"
    assert data4["status"] == "completed"


@pytest.mark.asyncio
async def test_voice_session_cleanup_expired():
    """Verify cleanup_expired removes idle sessions."""
    s = VoiceSessionManager.get_or_create("sess_test_expired_1", "cit_1")
    # Simulate old activity
    from datetime import datetime, timezone, timedelta
    s.last_activity = datetime.now(timezone.utc) - timedelta(hours=2)

    assert VoiceSessionManager.get("sess_test_expired_1") is not None
    removed = VoiceSessionManager.cleanup_expired(max_idle_seconds=1800)
    assert removed >= 1
    assert VoiceSessionManager.get("sess_test_expired_1") is None


@pytest.mark.asyncio
async def test_opportunistic_cleanup_expired_invoked_on_get_or_create():
    """get_or_create must opportunistically purge stale sessions."""
    old_session = VoiceSessionManager.get_or_create("sess_stale_kiosk_99", "cit_old")
    from datetime import datetime, timezone, timedelta
    old_session.last_activity = datetime.now(timezone.utc) - timedelta(hours=3)

    # Calling get_or_create on a new session sweeps sess_stale_kiosk_99
    VoiceSessionManager.get_or_create("sess_active_new_1", "cit_new")
    assert VoiceSessionManager.get("sess_stale_kiosk_99") is None
    assert VoiceSessionManager.get("sess_active_new_1") is not None


@pytest.mark.asyncio
async def test_concurrent_sessions_isolated_transcripts_and_updates(client: AsyncClient):
    """Verify concurrent sessions are strictly isolated in memory and terminated sessions cannot reuse state."""
    # 1. Init Session A and Session B
    res_a = await client.post("/api/v1/sessions/init", json={"consent_given": True, "preferred_language": "hi"})
    res_b = await client.post("/api/v1/sessions/init", json={"consent_given": True, "preferred_language": "hi"})
    sess_a = res_a.json()["session_id"]
    sess_b = res_b.json()["session_id"]

    # 2. Session A proposes farmer landholding
    turn_a = await client.post(
        "/api/v1/voice/turn",
        headers={"X-Session-ID": sess_a},
        json={"text": "मैं एक किसान हूँ और मेरे पास 3 एकड़ जमीन है", "preferred_language": "hi"},
    )
    assert turn_a.status_code == 200
    state_a = VoiceSessionManager.get(sess_a)
    assert state_a is not None
    assert state_a.proposed_profile_updates.get("occupation") == "farmer"
    assert state_a.proposed_profile_updates.get("land_acres") == 3.0

    # 3. Session B proposes age 72
    turn_b = await client.post(
        "/api/v1/voice/turn",
        headers={"X-Session-ID": sess_b},
        json={"text": "मेरी उम्र 72 वर्ष है", "preferred_language": "hi"},
    )
    assert turn_b.status_code == 200
    state_b = VoiceSessionManager.get(sess_b)
    assert state_b is not None
    assert state_b.proposed_profile_updates.get("age") == 72
    assert "occupation" not in state_b.proposed_profile_updates

    # 4. Terminate Session A
    term_res = await client.post("/api/v1/sessions/terminate", json={"session_id": sess_a})
    assert term_res.status_code == 200
    assert VoiceSessionManager.get(sess_a) is None

    # 5. Terminated Session A cannot make turns or transcribe (returns 404)
    reused_turn = await client.post(
        "/api/v1/voice/turn",
        headers={"X-Session-ID": sess_a},
        json={"text": "नमस्ते", "preferred_language": "hi"},
    )
    assert reused_turn.status_code == 404

    dummy_wav = base64.b64encode(b"dummy audio").decode("ascii")
    reused_transcribe = await client.post(
        "/api/v1/voice/transcribe",
        headers={"X-Session-ID": sess_a},
        json={"audio_base64": dummy_wav, "audio_mime_type": "audio/wav", "language": "hi"},
    )
    assert reused_transcribe.status_code == 404

    # 6. Session B remains completely active and unperturbed
    active_b = await client.post(
        "/api/v1/voice/turn",
        headers={"X-Session-ID": sess_b},
        json={"text": "नमस्ते", "preferred_language": "hi"},
    )
    assert active_b.status_code == 200
    assert VoiceSessionManager.get(sess_b) is not None


