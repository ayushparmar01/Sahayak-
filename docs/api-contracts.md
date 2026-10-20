# SAHAYAK API & Interface Contracts

## 1. REST API Endpoints

All REST APIs are served under `/api/v1` and follow standard JSON request/response formats.

### 1.1 Citizen & Session Management

#### `POST /api/v1/sessions/init`
Initializes a new citizen session (or restores an existing session by phone hash or anonymous token).
- **Request:**
  ```json
  {
    "preferred_language": "hi",
    "consent_given": true,
    "consent_timestamp": "2026-10-18T09:30:00Z"
  }
  ```
- **Response:**
  ```json
  {
    "session_id": "sess_89a3f2b1c4e6",
    "citizen_id": "cit_550e8400e29b",
    "preferred_language": "hi",
    "active_agent": "voice",
    "profile_state": {
      "is_confirmed": false
    }
  }
  ```

---

### 1.2 Citizen Profile Management

#### `GET /api/v1/profile`
Fetches current demographic profile state for the active session.

#### `PUT /api/v1/profile`
Updates demographic profile attributes with server-side validation.
- **Request:**
  ```json
  {
    "age": 42,
    "state": "Uttar Pradesh",
    "district": "Mathura",
    "land_acres": 2.0,
    "land_type": "irrigated",
    "annual_income": 85000,
    "ration_card_type": "BPL",
    "occupation": "farmer",
    "social_category": "OBC",
    "is_confirmed": true
  }
  ```
- **Response:**
  ```json
  {
    "status": "success",
    "profile": {
      "age": 42,
      "state": "Uttar Pradesh",
      "district": "Mathura",
      "land_acres": 2.0,
      "land_type": "irrigated",
      "annual_income": 85000.0,
      "ration_card_type": "BPL",
      "occupation": "farmer",
      "social_category": "OBC",
      "is_confirmed": true,
      "updated_at": "2026-10-18T09:35:12Z"
    }
  }
  ```

---

### 1.3 Schemes Catalogue & Deterministic Eligibility

#### `GET /api/v1/schemes`
Returns the verified government schemes catalogue with safe filtering.
- **Query Parameters (Optional):**
  - `category`: string (e.g. `AGRICULTURE`, `HEALTHCARE`, `HOUSING`, `WOMEN_CHILD`, `FINANCIAL_SECURITY`, `SOCIAL_WELFARE`)
  - `jurisdiction`: string (`CENTRAL_SECTOR`, `CENTRALLY_SPONSORED`)
  - `verification_status`: string (`VERIFIED`, `REVISION_PENDING`, `OUTDATED`)
  - `is_active`: boolean
- **Response:**
  ```json
  {
    "total": 8,
    "schemes": [
      {
        "id": "pm-kisan",
        "code": "PM_KISAN",
        "name_hi": "प्रधानमंत्री किसान सम्मान निधि",
        "name_en": "PM Kisan Samman Nidhi",
        "ministry": "कृषि एवं किसान कल्याण मंत्रालय",
        "category": "AGRICULTURE",
        "target_group_hi": "पंजीकृत कृषि भूमि धारक किसान परिवार",
        "target_group_en": "Small, marginal, and all cultivable landholding farmer families",
        "official_portal_url": "https://pmkisan.gov.in",
        "benefit_summary_hi": "₹6,000 प्रति वर्ष 3 समान किस्तों में प्रत्यक्ष लाभ अंतरण (DBT)",
        "benefit_summary_en": "₹6,000 per year in 3 equal four-monthly installments via Direct Benefit Transfer",
        "max_annual_benefit_inr": 6000.0,
        "jurisdiction": "CENTRAL_SECTOR",
        "last_verified_date": "2026-10-15",
        "verification_source": "pmkisan.gov.in / MoA&FW Guidelines 2024",
        "verification_status": "VERIFIED",
        "is_active": true,
        "rule_version": 1
      }
    ]
  }
  ```

#### `GET /api/v1/schemes/{scheme_id}`
Retrieves complete, verified scheme details, application steps, required documents, caveats, and structured evaluation rules.
- **Path Parameters:**
  - `scheme_id`: string (e.g. `pm-kisan`, `pm-jay`, `kcc`, `pmay-g`, `pm-ujjwala`, `pmfby`, `nsap-oap`, `ssy`)
- **Response:**
  ```json
  {
    "id": "pm-kisan",
    "code": "PM_KISAN",
    "name_hi": "प्रधानमंत्री किसान सम्मान निधि",
    "name_en": "PM Kisan Samman Nidhi",
    "ministry": "कृषि एवं किसान कल्याण मंत्रालय",
    "category": "AGRICULTURE",
    "official_portal_url": "https://pmkisan.gov.in",
    "benefit_summary_hi": "₹6,000 प्रति वर्ष 3 समान किस्तों में प्रत्यक्ष लाभ अंतरण (DBT)",
    "benefit_summary_en": "₹6,000 per year in 3 equal four-monthly installments via Direct Benefit Transfer",
    "max_annual_benefit_inr": 6000.0,
    "jurisdiction": "CENTRAL_SECTOR",
    "application_process_hi": "1. pmkisan.gov.in पर 'Farmers Corner' में जाएं...",
    "application_process_en": "1. Visit pmkisan.gov.in and click 'New Farmer Registration'...",
    "documents_required": ["land_khatauni", "aadhaar_linked_bank_account"],
    "caveats_hi": "यदि परिवार का कोई सदस्य आयकर दाता है अथवा संवैधानिक पद पर है तो अपात्र होंगे।",
    "caveats_en": "Institutional landholders and income-tax paying households are excluded.",
    "last_verified_date": "2026-10-15",
    "verification_source": "pmkisan.gov.in / MoA&FW Guidelines 2024",
    "verification_status": "VERIFIED",
    "is_active": true,
    "rule_version": 1,
    "rules": [
      {
        "id": "rule_pmk_1",
        "rule_code": "PMK_MANDATORY_LAND",
        "rule_type": "MANDATORY_CRITERION",
        "description_hi": "आवेदक किसान परिवार के नाम पर कृषि योग्य भूमि दर्ज होनी चाहिए।",
        "description_en": "Applicant farmer family must own cultivable agricultural land.",
        "source_citation": "PM-KISAN Operational Guidelines Clause 2.1",
        "failure_message_hi": "कृषि भूमि का स्वामित्व दर्ज न होने पर योजना लागू नहीं होती।",
        "failure_message_en": "Ineligible: No cultivable agricultural landholding recorded."
      }
    ]
  }
  ```

#### `POST /api/v1/eligibility/assess`
Evaluates citizen eligibility for a specific scheme using deterministic backend rules.
Requires an authorized session ID (`X-Session-ID` header) to prevent unauthorized profile evaluation.
Supports temporary simulation parameters via `profile_override`.
- **Headers:**
  - `X-Session-ID`: string (Required active session ID)
- **Request:**
  ```json
  {
    "scheme_id": "pm-kisan",
    "profile_override": {
      "is_income_tax_payer": false
    }
  }
  ```
- **Response:**
  ```json
  {
    "scheme_id": "pm-kisan",
    "scheme_name_hi": "प्रधानमंत्री किसान सम्मान निधि",
    "scheme_name_en": "PM Kisan Samman Nidhi",
    "rule_version": 1,
    "evaluated_at": "2026-10-18T12:00:00Z",
    "status": "ELIGIBLE",
    "status_label_hi": "पात्र (Eligible)",
    "status_label_en": "Eligible",
    "summary_explanation_hi": "आपकी दी गई जानकारी के अनुसार आप पीएम-किसान के लिए पात्र हैं।",
    "summary_explanation_en": "Based on verified details, you are eligible for PM-Kisan.",
    "conditions_satisfied": [
      {
        "id": "PMK_LAND_OWNERSHIP",
        "title_hi": "कृषि भूमि का मालिकाना हक",
        "title_en": "Agricultural Land Ownership",
        "outcome": "PASS",
        "outcome_detail_hi": "कृषि भूमि दर्ज है (2.5 एकड़)।",
        "outcome_detail_en": "Cultivable agricultural land recorded (2.5 acres).",
        "source_citation": "PM-KISAN Guidelines para 2.1"
      }
    ],
    "conditions_failed": [],
    "missing_information": [],
    "applicable_exclusions": [],
    "pending_verifications": [
      {
        "id": "PMK_EXT_KHATAUNI_MUTATION",
        "title_hi": "राज्य भू-अभिलेख (खतौनी) में नाम दर्ज होने की आधिकारिक पुष्टि",
        "title_en": "Official State Land Records (Khatauni) Mutation Verification",
        "outcome": "PENDING_VERIFICATION",
        "outcome_detail_hi": "राज्य के भूलेख पोर्टल पर खतौनी में नाम और आधार-लिंक्ड बैंक खाता सक्रिय होना अनिवार्य है।",
        "outcome_detail_en": "Name in State Bhulekh portal and Aadhaar-seeded NPCI bank account must be verified by District Agriculture Dept.",
        "source_citation": "PM-KISAN Guidelines Section 4"
      }
    ],
    "benefit_summary": {
      "amount_inr": 6000.0,
      "description_hi": "₹6,000 प्रति वर्ष 3 समान किस्तों में प्रत्यक्ष लाभ अंतरण (DBT)",
      "description_en": "₹6,000 per year in 3 equal four-monthly installments via Direct Benefit Transfer",
      "caveats_hi": "यदि परिवार का कोई सदस्य आयकर दाता है अथवा संवैधानिक पद पर है तो अपात्र होंगे।",
      "caveats_en": "Institutional landholders and income-tax paying households are excluded."
    },
    "required_documents": [
      "land_khatauni",
      "aadhaar_linked_bank_account"
    ],
    "official_sources": [
      {
        "title": "pmkisan.gov.in / MoA&FW Guidelines 2024",
        "url": "https://pmkisan.gov.in"
      }
    ],
    "next_recommended_action_hi": "खतौनी की प्रति और आधार कार्ड के साथ pmkisan.gov.in या नजदीकी सीएससी केंद्र पर नया किसान पंजीकरण करें।",
    "next_recommended_action_en": "Apply via 'New Farmer Registration' at pmkisan.gov.in or nearest CSC with Khatauni and Aadhaar.",
    "disclaimer_hi": "सार्वजनिक सेवा सूचना: यह एक प्रारंभिक और सूचनात्मक आकलन है, कोई अंतिम सरकारी स्वीकृति नहीं। योजना का अंतिम लाभ संबंधित विभाग/बैंक द्वारा भौतिक दस्तावेज़ सत्यापन के बाद ही मान्य होता है।",
    "disclaimer_en": "Public Service Notice: This is an informational preliminary assessment, not an official government approval. Final scheme benefits are subject to physical document verification and sanction by the competent authority/bank."
  }
  ```

---

### 1.4 Document Processing & OCR

#### `POST /api/v1/documents/upload`
Uploads a document photograph for OCR verification with automatic Aadhaar redaction.
- **Form Data:**
  - `file`: image/jpeg, image/png, or application/pdf
  - `doc_type`: "ration_card" | "kisan_credit_card" | "land_khatauni" | "income_certificate"
- **Response:**
  ```json
  {
    "document_id": "doc_991823ab",
    "document_type": "land_khatauni",
    "ocr_confidence": 0.94,
    "extracted_fields": {
      "owner_name": "रामेश कुमार",
      "khasra_number": "142/2",
      "area_acres": 2.0,
      "village": "बरसाना",
      "district": "Mathura"
    },
    "masked_identifier": "XXXX-XXXX-4912",
    "requires_citizen_confirmation": true,
    "issues_found": []
  }
  ```

#### `POST /api/v1/documents/{document_id}/confirm`
Citizen confirms or edits OCR-extracted fields.
- **Request:**
  ```json
  {
    "confirmed_fields": {
      "owner_name": "रमेश कुमार",
      "area_acres": 2.0
    },
    "is_confirmed": true
  }
  ```

---

### 1.5 Application Draft & Follow-up

#### `POST /api/v1/applications/draft`
Generates a structured, pre-filled application draft for a selected scheme.
- **Response:**
  ```json
  {
    "draft_id": "app_2026_00192",
    "scheme_id": "pm-kisan",
    "status": "DRAFT_IN_PROGRESS",
    "readiness_score": 75.0,
    "readiness_breakdown": {
      "mandatory_fields_completed": 4,
      "mandatory_fields_required": 4,
      "verified_documents": 1,
      "required_documents": 2,
      "pending_items": [
        "बैंक पासबुक / बैंक विवरण सत्यापन लंबित"
      ]
    },
    "prefilled_form": {
      "applicant_name": "रमेश कुमार",
      "state": "Uttar Pradesh",
      "district": "Mathura",
      "land_area": "2.0 Acres",
      "bank_account_verified": false
    },
    "step_by_step_submission_guide": [
      "1. इस ड्राफ्ट फॉर्म का प्रिंट निकालें या मोबाइल पर सुरक्षित रखें।",
      "2. खतौनी और बैंक पासबुक की प्रति संलग्न करें।",
      "3. अपने निकटतम CSC केंद्र या ग्राम पंचायत कार्यालय में जमा करें।"
    ],
    "official_disclaimer": "यह आधिकारिक सरकारी आवेदन नहीं है। यह सीएससी केंद्र अथवा आधिकारिक पोर्टल पर जमा करने हेतु तैयार किया गया सहायता ड्राफ्ट है।"
  }
  ```

#### `GET /api/v1/followups/{draft_id}`
Returns timeline reminders and tracked stage.
- **Response:**
  ```json
  {
    "draft_id": "app_2026_00192",
    "status_category": "CITIZEN_REPORTED",
    "current_stage": "SUBMITTED_AT_CSC",
    "next_installment_date": "2026-12-01",
    "reminders": [
      {
        "title_hi": "पीएम किसान ई-केवाईसी नवीनीकरण",
        "due_date": "2026-11-15",
        "action_required": "बायोमेट्रिक ई-केवाईसी सत्यापित कराएं"
      }
    ]
  }
  ```

---

## 2. WebSocket Real-Time Conversation Contract

Endpoint: `ws://localhost:8000/ws/agent/converse/{session_id}`

### Message Framing:
All frames are UTF-8 JSON.

#### Client to Server (Voice Audio / Text Chunk):
```json
{
  "type": "audio_chunk",
  "mime_type": "audio/webm;codecs=opus",
  "data_base64": "GkXfo59ChoEBQveBAULygQ8...",
  "is_final": true,
  "language": "hi"
}
```
Or for text input:
```json
{
  "type": "user_text",
  "text": "मेरे पास 2 एकड़ जमीन है यूपी में, क्या मुझे मदद मिल सकती है?",
  "language": "hi"
}
```

#### Server to Client (Agent Responses):
```json
{
  "type": "agent_message",
  "agent": "eligibility_agent",
  "text_hi": "रमेश जी, उत्तर प्रदेश में 2 एकड़ कृषि भूमि के आधार पर आप प्रधानमंत्री किसान सम्मान निधि योजना के संभावित पात्र हैं। पात्रता सुनिश्चित करने के लिए यह आवश्यक है कि परिवार में कोई आयकर दाता या सरकारी सेवा में न हो। क्या हम दस्तावेज़ और पात्रता की पुष्टि आगे बढ़ाएं?",
  "audio_url": "/api/v1/voice/stream/audio_resp_9238.mp3",
  "active_agent": "eligibility_agent",
  "suggested_actions": [
    {
      "label_hi": "शर्तें सत्यापित करें",
      "action_code": "VERIFY_EXCLUSIONS"
    },
    {
      "label_hi": "दस्तावेज़ सूची देखें",
      "action_code": "VIEW_REQUIRED_DOCUMENTS"
    }
  ]
}
```

### 1.5 Voice Assistant & LangGraph Orchestration (Phase 3)

#### `GET /api/v1/voice/providers`
Returns current runtime provider status, configured STT/TTS engines, supported languages, and safety constraints.
- **Response:**
  ```json
  {
    "stt_provider": "mock",
    "tts_provider": "mock",
    "llm_provider": "mock",
    "is_mock": true,
    "supported_languages": ["hi", "en"],
    "audio_limits": {
      "max_file_size_bytes": 10485760,
      "max_duration_seconds": 60,
      "max_conversation_turns": 15,
      "supported_mime_types": ["audio/webm", "audio/wav", "audio/mp3", "audio/ogg", "audio/m4a"]
    }
  }
  ```

#### `POST /api/v1/voice/transcribe`
Converts citizen audio bytes to Indic/Devanagari text with zero audio retention.
- **Request:** (JSON or Multipart Form)
  ```json
  {
    "audio_base64": "UklGRiQAAABXQVZFZm10...",
    "audio_mime_type": "audio/webm",
    "language": "hi"
  }
  ```
- **Response:**
  ```json
  {
    "transcript": "मैं किसान हूँ और मेरे पास 2 एकड़ जमीन है",
    "confidence": 0.95,
    "language": "hi",
    "is_mock": true,
    "duration_seconds": 3.2
  }
  ```

#### `POST /api/v1/voice/turn`
Executes one conversational step in the LangGraph Voice Assistant state machine. Requires `X-Session-ID` header.
- **Headers:** `X-Session-ID: sess_...`
- **Request:**
  ```json
  {
    "text": "मैं एक किसान हूँ और मेरे पास 2 एकड़ जमीन है",
    "audio_base64": null,
    "audio_mime_type": "audio/webm",
    "confirmed_by_user": null,
    "request_tts": true,
    "preferred_language": "hi"
  }
  ```
- **Response (Needs Confirmation):**
  ```json
  {
    "session_id": "sess_89a3f2b1c4e6",
    "citizen_id": "cit_550e8400e29b",
    "turn_count": 1,
    "status": "needs_confirmation",
    "transcript": "मैं एक किसान हूँ और मेरे पास 2 एकड़ जमीन है",
    "transcript_confidence": 1.0,
    "intent": "general_query",
    "proposed_profile_updates": {
      "occupation": "farmer",
      "owns_agricultural_land": true,
      "land_acres": 2.0
    },
    "persisted_profile_updates": {},
    "is_profile_confirmed": false,
    "follow_up_field": null,
    "follow_up_question_hi": null,
    "follow_up_question_en": null,
    "evaluated_schemes": [],
    "response_text_hi": "मैंने आपकी यह जानकारी समझी है:\n- व्यवसाय: किसान\n- कृषि भूमि रकबा: 2.0 एकड़\n\nक्या यह जानकारी सही है? पुष्टि के लिए 'हाँ' कहें अथवा 'पुष्टि करें' बटन दबाएं।",
    "response_text_en": "I understood the following profile details:\n- Occupation: farmer\n- Land Area: 2.0 acres\n\nIs this information correct? Say 'yes' or click 'Confirm Profile'.",
    "audio_base64": "UklGRiQAAABXQVZFZm10...",
    "audio_format": "audio/wav",
    "browser_tts_recommended": true,
    "provider_info": { "workflow": "LangGraph", "stt": "direct_text_input" },
    "error_message": null
  }
  ```

#### `POST /api/v1/voice/speak`
Standalone Text-to-Speech synthesis endpoint.
- **Request:**
  ```json
  {
    "text": "नमस्ते, मैं सहायक हूँ।",
    "language": "hi"
  }
  ```
- **Response:**
  ```json
  {
    "audio_base64": "UklGRiQAAABXQVZFZm10...",
    "audio_format": "audio/wav",
    "spoken_text": "नमस्ते, मैं सहायक हूँ।",
    "browser_tts_recommended": true
  }
  ```

---


## 3. Python Service & Adapter Interfaces

### 3.1 Speech Adapter (`SpeechProviderAdapter`)
```python
class SpeechProviderAdapter(ABC):
    @abstractmethod
    async def speech_to_text(self, audio_bytes: bytes, language: str = "hi") -> ASRResult:
        """Transcribes Indic audio into normalized UTF-8 text with confidence score."""
        pass

    @abstractmethod
    async def text_to_speech(self, text: str, language: str = "hi", voice_gender: str = "female") -> bytes:
        """Synthesizes Hindi/Indic speech audio bytes."""
        pass
```

### 3.2 Vision OCR Adapter (`DocumentOCRAdapter`)
```python
class DocumentOCRAdapter(ABC):
    @abstractmethod
    async def extract_and_verify(self, file_bytes: bytes, doc_type: str) -> OCRExtractionResult:
        """Extracts text, identifies key-values, and applies automatic PII masking."""
        pass
```

### 3.3 Deterministic Rule Engine (`SchemeRulesEngine`)
```python
class SchemeRulesEngine:
    def evaluate_profile(self, profile: CitizenProfile, scheme: Scheme) -> SchemeEvaluationResult:
        """Executes 100% deterministic boolean rules. Does not call external LLMs."""
        pass
```
