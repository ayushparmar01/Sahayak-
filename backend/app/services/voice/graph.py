"""LangGraph Multi-Agent Voice Orchestration for SAHAYAK.

Orchestrates voice intake, Indic NLP extraction, user confirmation gating,
deterministic eligibility evaluation, and speech synthesis without LLM hallucinations.
"""
import base64
from typing import Any, Callable, Coroutine, Literal, TypedDict
from langgraph.graph import StateGraph, START, END

from app.schemas.eligibility import AssessmentStatus, EligibilityAssessResponse
from app.knowledge.foundation_schemes import FOUNDATION_SCHEMES_KNOWLEDGE
from app.services.eligibility_engine import EligibilityEngine
from app.services.voice import get_stt_provider, get_tts_provider, get_extraction_provider
from app.services.voice.session_manager import VoiceSessionState


class VoiceGraphState(TypedDict, total=False):
    """Explicitly typed state flowing through the LangGraph voice workflow."""
    session_id: str
    citizen_id: str
    preferred_language: str
    consent_given: bool
    input_mode: Literal["voice", "text"]
    user_input_text: str | None
    audio_bytes: bytes | None
    audio_mime_type: str | None
    request_tts: bool
    
    # Session limits & counters
    turn_count: int
    max_turns: int
    
    # Speech-to-Text outputs
    transcript: str | None
    transcript_confidence: float
    stt_is_mock: bool
    
    # NLP & Profile extraction
    intent: str | None
    extracted_fields: dict[str, Any]
    current_profile: dict[str, Any]
    proposed_profile_updates: dict[str, Any]
    persisted_profile_updates: dict[str, Any]
    is_profile_confirmed: bool
    is_cancelled: bool
    
    # Follow-up & Missing information
    missing_fields: list[str]
    follow_up_field: str | None
    last_asked_field: str | None
    skipped_fields: list[str]
    follow_up_question_hi: str | None
    follow_up_question_en: str | None
    
    # Scheme Discovery & Deterministic Assessments
    relevant_scheme_ids: list[str]
    evaluated_schemes: list[EligibilityAssessResponse]
    
    # Final Response Texts & Spoken Audio
    response_text_hi: str
    response_text_en: str
    spoken_audio_base64: str | None
    spoken_audio_format: str
    browser_tts_recommended: bool
    
    # Workflow Status
    status: Literal["ready", "awaiting_consent", "needs_confirmation", "needs_follow_up", "completed", "error"]
    error_message: str | None
    
    # Provider transparency
    provider_info: dict[str, str]


# Map profile fields to citizen-friendly bilingual labels
FIELD_LABELS: dict[str, tuple[str, str]] = {
    "age": ("आयु (वर्ष)", "Age (Years)"),
    "owns_agricultural_land": ("कृषि भूमि स्वामित्व", "Owns Agricultural Land"),
    "land_acres": ("कृषि भूमि रकबा (एकड़)", "Land Area (Acres)"),
    "has_pucca_house": ("पक्का मकान", "Owns Pucca House"),
    "residence_type": ("निवास क्षेत्र", "Residence Type"),
    "annual_income": ("वार्षिक आय (₹)", "Annual Income (₹)"),
    "ration_card_type": ("राशन कार्ड श्रेणी", "Ration Card Type"),
    "occupation": ("व्यवसाय", "Occupation"),
    "is_income_tax_payer": ("आयकर दाता", "Income Tax Payer"),
    "gender": ("लिंग", "Gender"),
    "has_girl_child_under_10": ("10 वर्ष तक की बालिका", "Girl Child <= 10 yrs"),
    "has_existing_lpg": ("पूर्व एलपीजी कनेक्शन", "Existing LPG Connection"),
    "district": ("जिला", "District"),
    "state": ("राज्य", "State"),
}


def _format_updates_summary(updates: dict[str, Any], lang: str = "hi") -> tuple[str, str]:
    """Formats proposed profile updates into a concise bullet list."""
    lines_hi = []
    lines_en = []
    for k, v in updates.items():
        lbl_hi, lbl_en = FIELD_LABELS.get(k, (k, k))
        # Format human-readable boolean / string values
        val_hi = "हाँ" if v is True else ("नहीं" if v is False else str(v))
        val_en = "Yes" if v is True else ("No" if v is False else str(v))
        if k == "residence_type":
            val_hi = "ग्रामीण (Gram Panchayat)" if v == "RURAL" else "शहरी (Urban)"
            val_en = "Rural (Gram Panchayat)" if v == "RURAL" else "Urban"
        elif k == "occupation":
            val_hi = "किसान (Farmer)" if v == "farmer" else str(v)
        elif k == "annual_income" and isinstance(v, (int, float)):
            val_hi = f"₹{v:,.0f}"
            val_en = f"₹{v:,.0f}"
        elif k == "land_acres" and isinstance(v, (int, float)):
            val_hi = f"{v} एकड़"
            val_en = f"{v} acres"

        lines_hi.append(f"• {lbl_hi}: {val_hi}")
        lines_en.append(f"• {lbl_en}: {val_en}")

    return "\n".join(lines_hi), "\n".join(lines_en)


# -----------------------------------------------------------------------------
# GRAPH NODE IMPLEMENTATIONS
# -----------------------------------------------------------------------------

async def session_guard_node(state: VoiceGraphState) -> dict[str, Any]:
    """Validates citizen consent and enforces loop-guard turn limits."""
    if not state.get("consent_given"):
        return {
            "status": "awaiting_consent",
            "response_text_hi": "नमस्ते! सहायक आवाज सेवा का उपयोग करने के लिए कृपया पहले माइक्रोफोन एवं सत्र सहमति (Consent) प्रदान करें।",
            "response_text_en": "Welcome! Please grant microphone and session consent before starting your voice interaction.",
            "error_message": "CONSENT_REQUIRED",
        }

    turn = state.get("turn_count", 0)
    max_t = state.get("max_turns", 15)
    if turn >= max_t:
        return {
            "status": "completed",
            "response_text_hi": "इस सत्र की बातचीत सीमा पूरी हो चुकी है। यदि आपको और जानकारी चाहिए, तो कृपया ऊपर 'सत्र समाप्त करें' दबाकर नया सत्र शुरू करें।",
            "response_text_en": "Conversation limit reached for this session. Please end session and start a new one to continue.",
            "error_message": "LOOP_GUARD_MAX_TURNS_REACHED",
        }

    return {"status": "ready"}


async def transcribe_node(state: VoiceGraphState) -> dict[str, Any]:
    """Performs Speech-to-Text transcription via configured provider or uses text fallback."""
    if state.get("status") in ("awaiting_consent", "completed"):
        return {}

    audio_bytes = state.get("audio_bytes")
    input_mode = state.get("input_mode", "text")
    user_text = state.get("user_input_text")

    stt = get_stt_provider()
    provider_name = type(stt).__name__

    if input_mode == "voice" and audio_bytes:
        res = await stt.transcribe(
            audio_bytes=audio_bytes,
            mime_type=state.get("audio_mime_type", "audio/webm"),
            language=state.get("preferred_language", "hi"),
        )
        if not res.transcript.strip():
            return {
                "transcript": "",
                "transcript_confidence": 0.0,
                "stt_is_mock": res.is_mock,
                "status": "ready",
                "response_text_hi": "माफ़ कीजिए, आपकी आवाज़ स्पष्ट नहीं आई। कृपया शांत वातावरण में पुनः बोलें या नीचे लिखकर बताएं।",
                "response_text_en": "Could not recognize audio clearly. Please speak again in a quiet environment or type below.",
                "error_message": "AUDIO_LOW_CONFIDENCE",
                "provider_info": {"stt": provider_name},
            }

        return {
            "transcript": res.transcript,
            "transcript_confidence": res.confidence,
            "stt_is_mock": res.is_mock,
            "provider_info": {"stt": provider_name},
        }

    # Text input fallback
    clean_text = (user_text or "").strip()
    return {
        "transcript": clean_text,
        "transcript_confidence": 1.0,
        "stt_is_mock": False,
        "provider_info": {"stt": "direct_text_input"},
    }


async def extraction_node(state: VoiceGraphState) -> dict[str, Any]:
    """Extracts intent and demographic profile fields using deterministic Indic NLP."""
    if state.get("status") in ("awaiting_consent", "completed") or state.get("error_message"):
        return {}

    transcript = state.get("transcript") or ""
    current_prof = state.get("current_profile") or {}
    extractor = get_extraction_provider()

    result = await extractor.extract_intent_and_fields(
        text=transcript,
        current_profile=current_prof,
        language=state.get("preferred_language", "hi"),
    )

    # Check if user had pending proposed updates from previous turn
    existing_proposed = dict(state.get("proposed_profile_updates") or {})

    # If user explicitly confirmed via text/voice ("हाँ", "पुष्टि करें") or button
    is_confirmed = result.is_confirmed or bool(state.get("is_profile_confirmed"))
    is_cancelled = result.is_cancelled

    # Detect new fields extracted in this turn
    new_extracted = dict(result.extracted_fields)
    combined_proposed = dict(existing_proposed)
    combined_proposed.update(new_extracted)

    return {
        "intent": result.intent,
        "extracted_fields": new_extracted,
        "proposed_profile_updates": combined_proposed,
        "is_profile_confirmed": is_confirmed,
        "is_cancelled": is_cancelled,
    }


def should_route_after_extraction(state: VoiceGraphState) -> str:
    """Conditional router determining next agent node."""
    status = state.get("status")
    if status in ("awaiting_consent", "completed") or state.get("error_message"):
        return "speech_node"

    if state.get("is_cancelled"):
        return "cancel_updates_node"

    intent = state.get("intent")
    if intent == "greeting":
        return "greeting_node"
    if intent == "out_of_scope":
        return "out_of_scope_node"
    if intent == "dont_know":
        return "handle_unknown_node"

    # If proposed updates exist and citizen just confirmed
    if state.get("proposed_profile_updates") and state.get("is_profile_confirmed"):
        return "persist_profile_node"

    # If new updates were proposed this turn and not yet confirmed, require confirmation
    if state.get("extracted_fields") and not state.get("is_profile_confirmed"):
        return "confirm_prompt_node"

    # If user wants eligibility check or has confirmed profile
    if intent in ("check_eligibility", "confirm_changes"):
        return "assess_schemes_node"

    # Check for missing critical fields
    return "check_missing_fields_node"


async def greeting_node(state: VoiceGraphState) -> dict[str, Any]:
    """Provides a warm citizen-service greeting and instructions on how to interact."""
    return {
        "status": "ready",
        "response_text_hi": "नमस्ते! मैं सहायक (SAHAYAK) हूँ — आपका सरकारी योजना मार्गदर्शक। आप अपनी उम्र, व्यवसाय (जैसे किसान या मजदूर), जमीन या परिवार का विवरण बताकर अपने लिए उपलब्ध सरकारी योजनाओं की जानकारी प्राप्त कर सकते हैं।",
        "response_text_en": "Namaste! I am SAHAYAK — your government scheme guide. You can share your age, occupation (e.g., farmer or laborer), landholding, or family details to discover schemes you may be eligible for.",
    }


async def out_of_scope_node(state: VoiceGraphState) -> dict[str, Any]:
    """Politely guides the citizen back to the domain of Indian welfare schemes."""
    return {
        "status": "ready",
        "response_text_hi": "माफ़ कीजिए, मैं केवल भारत सरकार की कल्याणकारी योजनाओं (जैसे पीएम-किसान, आयुष्मान भारत, पीएम आवास आदि) की जानकारी एवं पात्रता जांचने में सहायता कर सकता हूँ। कृपया योजना संबंधी कोई विवरण बताएं।",
        "response_text_en": "I apologize, but I can only assist with Indian government welfare schemes (such as PM-Kisan, Ayushman Bharat, PMAY-G). Please share scheme-related information or questions.",
    }


async def handle_unknown_node(state: VoiceGraphState) -> dict[str, Any]:
    """Handles citizen uncertainty ('don't know') by marking the pending field as skipped."""
    last_field = state.get("last_asked_field")
    skipped = list(state.get("skipped_fields") or [])
    if last_field and last_field not in skipped:
        skipped.append(last_field)

    return {
        "skipped_fields": skipped,
        "follow_up_field": None,
        "follow_up_question_hi": None,
        "follow_up_question_en": None,
        "status": "ready",
        "response_text_hi": "कोई बात नहीं। हम इस जानकारी के बिना ही उपलब्ध विवरण के आधार पर आपके लिए योजनाओं की जांच कर रहे हैं।",
        "response_text_en": "No problem. We will assess available schemes based on your existing details without this information.",
    }


async def cancel_updates_node(state: VoiceGraphState) -> dict[str, Any]:
    """Discards proposed profile updates when citizen states cancellation."""
    return {
        "proposed_profile_updates": {},
        "status": "ready",
        "response_text_hi": "प्रस्तावित जानकारी रद्द कर दी गई है। आप अपनी सही जानकारी फिर से बोलकर या लिखकर दर्ज कर सकते हैं।",
        "response_text_en": "Proposed details have been discarded. You can speak or type your correct details again.",
    }


async def confirm_prompt_node(state: VoiceGraphState) -> dict[str, Any]:
    """Prompts citizen to review and confirm proposed profile updates before persisting."""
    proposed = state.get("proposed_profile_updates") or {}
    if not proposed:
        return {"status": "ready"}

    sum_hi, sum_en = _format_updates_summary(proposed)
    q_hi = (
        f"मैंने आपकी यह जानकारी समझी है:\n{sum_hi}\n\n"
        "क्या यह जानकारी सही है? पुष्टि के लिए 'हाँ' कहें अथवा 'पुष्टि करें' बटन दबाएं।"
    )
    q_en = (
        f"I understood the following profile details:\n{sum_en}\n\n"
        "Is this information correct? Say 'yes' or click 'Confirm Profile'."
    )

    return {
        "status": "needs_confirmation",
        "response_text_hi": q_hi,
        "response_text_en": q_en,
        "follow_up_question_hi": "क्या आप इस जानकारी की पुष्टि करते हैं?",
        "follow_up_question_en": "Do you confirm this information?",
    }


async def persist_profile_node(state: VoiceGraphState) -> dict[str, Any]:
    """Applies confirmed profile updates to the active working profile."""
    proposed = dict(state.get("proposed_profile_updates") or {})
    current = dict(state.get("current_profile") or {})
    current.update(proposed)
    current["is_confirmed"] = True

    return {
        "current_profile": current,
        "persisted_profile_updates": proposed,
        "proposed_profile_updates": {},
        "is_profile_confirmed": True,
        "status": "ready",
    }


async def check_missing_fields_node(state: VoiceGraphState) -> dict[str, Any]:
    """Identifies the most consequential missing profile field and formulates one polite question."""
    prof = state.get("current_profile") or {}
    occ = (prof.get("occupation") or "").lower()
    skipped = set(state.get("skipped_fields") or [])

    # Prioritize missing fields logically based on occupation and high-value schemes
    missing_key = None
    q_hi = None
    q_en = None

    if occ == "farmer" and prof.get("owns_agricultural_land") is None and "owns_agricultural_land" not in skipped:
        missing_key = "owns_agricultural_land"
        q_hi = "क्या आपके या आपके परिवार के नाम पर कृषि भूमि (खेत) दर्ज है? कृपया 'हाँ' या 'नहीं' बताएं।"
        q_en = "Do you or your family own agricultural land? Please reply 'yes' or 'no'."
    elif occ == "farmer" and prof.get("owns_agricultural_land") is True and not prof.get("land_acres") and "land_acres" not in skipped:
        missing_key = "land_acres"
        q_hi = "आपके पास कुल कितने एकड़ कृषि भूमि है? (उदा. 2 एकड़, 3.5 एकड़)"
        q_en = "How many acres of agricultural land do you own? (e.g. 2 acres, 3.5 acres)"
    elif prof.get("residence_type") is None and "residence_type" not in skipped:
        missing_key = "residence_type"
        q_hi = "आप ग्रामीण क्षेत्र (गांव / ग्राम पंचायत) में रहते हैं अथवा शहरी क्षेत्र में?"
        q_en = "Do you reside in a rural village (Gram Panchayat) or an urban town/city?"
    elif prof.get("has_pucca_house") is None and "has_pucca_house" not in skipped:
        missing_key = "has_pucca_house"
        q_hi = "क्या आपके परिवार के पास पहले से पक्का मकान उपलब्ध है या आप कच्चे मकान में रहते हैं?"
        q_en = "Does your family already own a pucca house, or do you live in a kutcha shelter?"
    elif prof.get("ration_card_type") is None and "ration_card_type" not in skipped:
        missing_key = "ration_card_type"
        q_hi = "आपके पास किस प्रकार का राशन कार्ड है? (बीपीएल, अंत्योदय, एपीएल या कोई नहीं)"
        q_en = "What type of ration card do you hold? (BPL, Antyodaya, APL, or None)"
    elif prof.get("is_income_tax_payer") is None and "is_income_tax_payer" not in skipped:
        missing_key = "is_income_tax_payer"
        q_hi = "क्या आपके परिवार का कोई सदस्य आयकर (Income Tax) भरता है?"
        q_en = "Does any member of your family pay income tax?"

    if missing_key:
        return {
            "status": "needs_follow_up",
            "follow_up_field": missing_key,
            "last_asked_field": missing_key,
            "follow_up_question_hi": q_hi,
            "follow_up_question_en": q_en,
            "response_text_hi": q_hi,
            "response_text_en": q_en,
        }

    return {"status": "ready"}


def should_route_after_missing_check(state: VoiceGraphState) -> str:
    """Routes to speech if follow-up asked, else evaluates schemes."""
    if state.get("status") == "needs_follow_up":
        return "speech_node"
    return "assess_schemes_node"


async def assess_schemes_node(state: VoiceGraphState) -> dict[str, Any]:
    """Invokes the deterministic eligibility engine for all relevant schemes.
    
    CRITICAL SAFETY RULES:
    1. Zero LLM hallucinated eligibility decisions.
    2. Preserves exact engine outputs: ELIGIBLE, POTENTIALLY_ELIGIBLE, INELIGIBLE, NEEDS_MORE_INFO.
    3. Accurately explains benefit classifications (concessional loan vs grant vs insurance cover).
    """
    prof = dict(state.get("current_profile") or {})
    assessments: list[EligibilityAssessResponse] = []

    # Evaluate schemes deterministically
    for scheme in FOUNDATION_SCHEMES_KNOWLEDGE:
        res = EligibilityEngine.evaluate(scheme, prof)
        assessments.append(res)

    # Sort results: ELIGIBLE first, then POTENTIALLY_ELIGIBLE, then NEEDS_MORE_INFO, then INELIGIBLE
    priority_order = {
        AssessmentStatus.ELIGIBLE: 0,
        AssessmentStatus.POTENTIALLY_ELIGIBLE: 1,
        AssessmentStatus.NEEDS_MORE_INFO: 2,
        AssessmentStatus.INELIGIBLE: 3,
    }
    assessments.sort(key=lambda a: priority_order.get(a.status, 99))

    # Formulate citizen-friendly Hindi explanation
    eligible_or_potential = [a for a in assessments if a.status in (AssessmentStatus.ELIGIBLE, AssessmentStatus.POTENTIALLY_ELIGIBLE)]
    needs_info = [a for a in assessments if a.status == AssessmentStatus.NEEDS_MORE_INFO]

    lines_hi = []
    lines_en = []

    if eligible_or_potential:
        lines_hi.append(f"आपकी दर्ज प्रोफ़ाइल के अनुसार आप {len(eligible_or_potential)} सरकारी योजनाओं के लिए पात्र या संभावित पात्र पाए गए हैं:")
        lines_en.append(f"Based on your profile, you are eligible or potentially eligible for {len(eligible_or_potential)} government schemes:")
        
        for idx, a in enumerate(eligible_or_potential[:3], 1):
            stat_hi = "पात्र" if a.status == AssessmentStatus.ELIGIBLE else "संभावित पात्र (सत्यापन आवश्यक)"
            stat_en = "Eligible" if a.status == AssessmentStatus.ELIGIBLE else "Potentially Eligible (Verification Required)"
            metric_hi = a.benefit_summary.benefit_metric_label_hi
            metric_en = a.benefit_summary.benefit_metric_label_en
            amt_hi = a.benefit_summary.benefit_amount_display_hi
            amt_en = a.benefit_summary.benefit_amount_display_en
            
            lines_hi.append(f"{idx}. {a.scheme_name_hi} — स्थिति: {stat_hi} ({metric_hi}: {amt_hi})")
            lines_en.append(f"{idx}. {a.scheme_name_en} — Status: {stat_en} ({metric_en}: {amt_en})")
            
        lines_hi.append("\nमहत्वपूर्ण सूचना: आयुष्मान भारत एवं पीएम आवास योजनाओं में अंतिम लाभ आधिकारिक सरकारी सूची (BIS / आवास+) सत्यापन के बाद ही मिलता है।")
        lines_en.append("\nImportant note: Ayushman Bharat and PMAY-G benefits require official government database (BIS / Awaas+) verification before disbursement.")
    elif needs_info:
        lines_hi.append("आपकी पात्रता का सटीक निर्धारण करने के लिए कुछ अतिरिक्त विवरण आवश्यक हैं। कृपया ऊपर पूछे गए प्रश्नों का उत्तर दें।")
        lines_en.append("Additional profile details are required to accurately evaluate your eligibility. Please answer the questions above.")
    else:
        lines_hi.append("वर्तमान दर्ज जानकारी के अनुसार मुख्य केंद्रीय योजनाओं के पात्रता मानदंड संतुष्ट नहीं हो रहे हैं। कृपया अपने विवरण की पुनः जांच करें।")
        lines_en.append("Based on current details, criteria for main central schemes are not satisfied. Please review your details.")

    resp_hi = "\n".join(lines_hi)
    resp_en = "\n".join(lines_en)

    return {
        "status": "completed",
        "evaluated_schemes": assessments,
        "response_text_hi": resp_hi,
        "response_text_en": resp_en,
    }


async def speech_node(state: VoiceGraphState) -> dict[str, Any]:
    """Generates Text-to-Speech audio if requested, providing visible text alongside."""
    text_hi = state.get("response_text_hi") or ""
    request_tts = state.get("request_tts", True)

    tts = get_tts_provider()
    provider_name = type(tts).__name__

    existing_info = dict(state.get("provider_info") or {})
    existing_info["tts"] = provider_name

    if not request_tts or not text_hi.strip():
        return {
            "spoken_audio_base64": None,
            "browser_tts_recommended": True,
            "provider_info": existing_info,
        }

    tts_res = await tts.synthesize(text=text_hi, language="hi")
    return {
        "spoken_audio_base64": tts_res.audio_base64,
        "spoken_audio_format": tts_res.audio_format,
        "browser_tts_recommended": tts_res.browser_fallback_recommended,
        "provider_info": existing_info,
    }


# -----------------------------------------------------------------------------
# GRAPH COMPILATION
# -----------------------------------------------------------------------------

def build_voice_assistant_graph():
    """Builds and compiles the SAHAYAK Voice Assistant LangGraph workflow."""
    workflow = StateGraph(VoiceGraphState)

    # Add agent nodes
    workflow.add_node("session_guard_node", session_guard_node)
    workflow.add_node("transcribe_node", transcribe_node)
    workflow.add_node("extraction_node", extraction_node)
    workflow.add_node("greeting_node", greeting_node)
    workflow.add_node("out_of_scope_node", out_of_scope_node)
    workflow.add_node("handle_unknown_node", handle_unknown_node)
    workflow.add_node("cancel_updates_node", cancel_updates_node)
    workflow.add_node("confirm_prompt_node", confirm_prompt_node)
    workflow.add_node("persist_profile_node", persist_profile_node)
    workflow.add_node("check_missing_fields_node", check_missing_fields_node)
    workflow.add_node("assess_schemes_node", assess_schemes_node)
    workflow.add_node("speech_node", speech_node)

    # Edge connections
    workflow.add_edge(START, "session_guard_node")
    workflow.add_edge("session_guard_node", "transcribe_node")
    workflow.add_edge("transcribe_node", "extraction_node")

    # Conditional branching after extraction
    workflow.add_conditional_edges(
        "extraction_node",
        should_route_after_extraction,
        {
            "greeting_node": "greeting_node",
            "out_of_scope_node": "out_of_scope_node",
            "handle_unknown_node": "handle_unknown_node",
            "cancel_updates_node": "cancel_updates_node",
            "confirm_prompt_node": "confirm_prompt_node",
            "persist_profile_node": "persist_profile_node",
            "check_missing_fields_node": "check_missing_fields_node",
            "assess_schemes_node": "assess_schemes_node",
            "speech_node": "speech_node",
        },
    )

    workflow.add_edge("greeting_node", "speech_node")
    workflow.add_edge("out_of_scope_node", "speech_node")
    workflow.add_edge("handle_unknown_node", "assess_schemes_node")
    workflow.add_edge("cancel_updates_node", "speech_node")
    workflow.add_edge("confirm_prompt_node", "speech_node")
    workflow.add_edge("persist_profile_node", "assess_schemes_node")

    # Conditional branching after checking missing fields
    workflow.add_conditional_edges(
        "check_missing_fields_node",
        should_route_after_missing_check,
        {
            "speech_node": "speech_node",
            "assess_schemes_node": "assess_schemes_node",
        },
    )

    workflow.add_edge("assess_schemes_node", "speech_node")
    workflow.add_edge("speech_node", END)

    return workflow.compile()


# Global pre-compiled graph instance
voice_assistant_graph = build_voice_assistant_graph()
