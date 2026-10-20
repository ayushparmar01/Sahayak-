# SAHAYAK Privacy & Security Specification

## 1. Regulatory Alignment: DPDP Act 2023 & UIDAI Guidelines

SAHAYAK establishes architectural standards aligned with India's **Digital Personal Data Protection (DPDP) Act, 2023** and **UIDAI Privacy Guidelines**. In Phase 0, these are defined as strict implementation constraints and testable verification gates. Formal compliance cannot be claimed on documentation alone; it requires functional verification and security testing scheduled for Phase 6.

---

## 2. Core Security & Privacy Principles

### 2.1 The Zero-Aadhaar Storage Rule
- **Absolute Architectural Rule:** SAHAYAK **NEVER** stores 12-digit Aadhaar numbers, biometric data, or unredacted Aadhaar card photos in the application database or persistent disk storage.
- **Immediate In-Memory Redaction Filter:** Any uploaded image or document scanned by the OCR pipeline passes through an in-memory redaction sanitizer before processing:
  ```python
  AADHAAR_REGEX = r"\b[2-9]{1}[0-9]{3}[-\s]?[0-9]{4}[-\s]?[0-9]{4}\b"
  # Any matched string is masked to XXXX-XXXX-Last4 or rejected
  ```
- **Temporary In-Memory Processing:** Document images are processed in ephemeral memory buffers and deleted immediately after citizen confirmation and draft generation.

### 2.2 Affirmative Citizen Consent
- Before any personal data (age, income, land, documents) is collected or processed, citizens must give affirmative, clear consent.
- Consent is captured via voice (*"हाँ, मैं सहमत हूँ"*) or clear UI checkbox with plain language explanation in Hindi.
- The timestamp and version of consent are recorded with the session.

### 2.3 Role Separation & Data Minimization
- The system only requests attributes that are directly referenced by the rules of the selected schemes (e.g., if a scheme only needs age and state, land acreage is optional).
- Citizens can browse schemes anonymously without registering or providing phone numbers.

### 2.4 Server-Side Validation & Sanitization
- All client inputs (text, numbers, document types) are validated against strict Pydantic schemas.
- File uploads are validated by magic number byte inspection (MIME type verification), file size limits (max 5 MB for documents, max 10 MB for voice clips), and extension whitelisting (`.jpg`, `.jpeg`, `.png`, `.pdf`, `.webm`, `.wav`).
- Path traversal protection ensures uploads cannot overwrite system files.

### 2.5 Voice Zero-Audio-Retention Pipeline & Ephemeral Memory Purge (Phase 3)
- **Zero Raw Audio Retention:** Raw citizen voice audio received via `/api/v1/voice/transcribe` or `/api/v1/voice/turn` is processed exclusively in ephemeral memory buffers. Audio byte arrays are purged in `finally:` blocks (`del audio_bytes`). No audio files are ever written to persistent disk storage.
- **Volatile Conversation State:** LangGraph conversation history resides in `VoiceSessionManager` in memory, capped to the last 5 turns to minimize memory footprint.
- **Kiosk Purge Integration:** Calling `POST /api/v1/sessions/terminate` immediately invokes `VoiceSessionManager.clear_session(session_id)`, erasing all conversational memory, turn counters, and proposed updates alongside the SQLite citizen and profile records.
- **Microphone Consent Barrier:** Microphone access and turn processing are strictly blocked until affirmative consent is granted. If a request is submitted without consent, the assistant responds with `status: "awaiting_consent"` and refuses to process speech.
- **Explicit Confirmation Gating:** NLP-extracted demographic attributes are never written directly to the database. They are held in `proposed_profile_updates` and only committed to the database after the citizen explicitly confirms via voice (*"हाँ यह सही है"*) or UI confirmation button.
- **Conversation Turn Loop Guard:** A hard cap of 15 conversational turns per session prevents runaway loops and API exhaustion.


---

## 3. Data Retention and Deletion Lifecycle

| Data Type | Storage Location | Retention Duration | Deletion Trigger |
| :--- | :--- | :--- | :--- |
| **Voice Audio Stream** | Ephemeral memory buffer | 0 seconds (discarded immediately after ASR transcription) | End of transcription stream |
| **Document Image Uploads** | Local temporary scratch / volatile storage | 24 hours max | Explicit citizen button "Delete my documents" or automated cleanup job |
| **Citizen Demographic Profile** | Encrypted DB (`citizen_profile`) | Until user session termination or requested deletion | Citizen "Clear Profile" action |
| **Application Drafts** | Encrypted DB (`application_draft`) | 90 days for reminder tracking | Citizen deletion request |
| **Application Audit Logs** | Sanitized log files | 30 days | Automated log rotation (PII strictly redacted) |

### 3.1 Shared Device & Rural Kiosk Security (Browser Storage Policy)
Rural citizens frequently access services via shared smartphones, CSC kiosks, or community tablets. Storing sensitive demographic details, land records, or session tokens in unencrypted `localStorage` exposes data to subsequent users.
- **Prohibition on Persistent LocalStorage for PII:** No demographic profile data, unmasked names, land records, or income figures may be written to browser `localStorage`.
- **Ephemeral In-Memory / Session State:** Citizen session state is maintained strictly in React in-memory state or volatile `sessionStorage` (which self-destructs upon closing the tab/browser).
- **One-Tap Kiosk Session Purge:** A prominent, persistent button (*"सत्र समाप्त करें / डेटा हटाएं"* - *"End Session / Wipe Data"*) allows citizens or kiosk operators to instantly purge all in-memory state, wipe session storage, and call `/api/v1/sessions/terminate`.

---

## 4. Public Service Integrity & Anti-Fabrication Rules

As a civic-tech tool built for national hackathons and real citizens:
1. **No Fake Government Approvals:** The system will never display "Application Approved by Ministry of Agriculture" or simulate official stamps.
2. **Honest Status Distinctions:**
   - Clearly label all generated forms as:  
     *“नागरिक सहायता ड्राफ्ट — कृपया आधिकारिक पोर्टल या सीएससी केंद्र पर जमा करें”*  
     *(“Citizen Assistance Draft — Please submit at official portal or CSC center”)*
   - Application reference numbers generated by SAHAYAK are explicitly prefixed with `DRAFT-SAHAYAK-` to prevent confusion with official government acknowledgment numbers.
3. **No Fabricated Compliance Claims:** Avoid misleading marketing statements such as "100% Guaranteed Scheme Approval" or "Official Government Partner".

---

## 5. Security & Privacy Implementation Verification Gates

The following requirements are architectural constraints established in Phase 0. Each item must be explicitly tested and verified in Phase 6 prior to public demonstration:

- [ ] **Gate 6.1 (Zero Aadhaar Storage):** Verify via automated DB inspection tests that no 12-digit Aadhaar pattern or raw identity card photo is stored anywhere in the database or filesystem.
- [ ] **Gate 6.2 (In-Memory Redaction):** Unit test the OCR redaction filter against synthetic Aadhaar images to verify masking to `XXXX-XXXX-Last4`.
- [ ] **Gate 6.3 (Shared Device Hygiene):** Verify via browser tests that closing the tab or tapping "End Session" leaves zero PII in `localStorage` or `sessionStorage`.
- [ ] **Gate 6.4 (Secret Isolation):** Verify frontend production bundle scan to confirm zero API keys or server secrets are present.
- [ ] **Gate 6.5 (Server Input Validation):** Verify all FastAPI endpoints reject non-whitelisted MIME types, file sizes > 5 MB, and malformed demographic payloads.
- [ ] **Gate 6.6 (SQL Injection & XSS):** Automated security scan verifying ORM parameterization and React DOM escaping.
- [ ] **Gate 6.7 (Ephemeral Cleanup):** Automated job test verifying temporary files older than 24 hours are deleted.
