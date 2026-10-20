"""Scheme-specific document checklist evaluator against foundation scheme guidelines."""
from typing import Any
from app.knowledge.foundation_schemes import FOUNDATION_SCHEMES_KNOWLEDGE

DOCUMENT_METADATA: dict[str, dict[str, str]] = {
    "land_khatauni": {
        "title_hi": "भूलेख खतौनी / राजस्व अभिलेख",
        "title_en": "Land Khatauni / Revenue Record",
        "citation": "राजस्व संहिता व भू-अभिलेख नियमावली (Land Revenue Code)",
    },
    "bank_passbook": {
        "title_hi": "बैंक पासबुक (आधार-सीडेड डीबीटी खाता)",
        "title_en": "Bank Passbook (Aadhaar Seeded DBT Account)",
        "citation": "डीबीटी दिशा-निर्देश व पीएमएफएस (DBT/PFMS Guidelines)",
    },
    "aadhaar_card_masked": {
        "title_hi": "आधार कार्ड (मास्क्ड प्रति)",
        "title_en": "Aadhaar Card (Masked Copy)",
        "citation": "आधार अधिनियम धारा 7 (Aadhaar Act 2016 Section 7)",
    },
    "ration_card": {
        "title_hi": "राशन कार्ड (एनएफएसए / अंत्योदय / बीपीएल)",
        "title_en": "Ration Card (NFSA / Antyodaya / BPL)",
        "citation": "राष्ट्रीय खाद्य सुरक्षा अधिनियम (NFSA 2013)",
    },
    "bpl_ration_card": {
        "title_hi": "बीपीएल / अंत्योदय राशन कार्ड",
        "title_en": "BPL / Antyodaya Ration Card",
        "citation": "ग्रामीण विकास मंत्रालय बीपीएल सर्वेक्षण सूची",
    },
    "crop_sowing_record": {
        "title_hi": "फसल बोआई गिरदावरी प्रमाण पत्र",
        "title_en": "Crop Sowing Girdawari Certificate",
        "citation": "कृषि सांख्यिकी व फसल ऋण नियमावली",
    },
    "crop_sowing_certificate": {
        "title_hi": "फसल बोआई प्रमाण पत्र (पटवारी/ग्राम सेवक सत्यापित)",
        "title_en": "Crop Sowing Certificate (Patwari Verified)",
        "citation": "पीएमएफबीवाई परिचालन दिशा-निर्देश पैरा 7",
    },
    "land_house_site_proof": {
        "title_hi": "आवास स्थल / भूमि प्रमाण पत्र",
        "title_en": "House Site / Homestead Land Proof",
        "citation": "पीएमएवाई-जी परिचालन दिशा-निर्देश पैरा 4.2",
    },
    "bpl_certificate": {
        "title_hi": "बीपीएल प्रमाण पत्र / एसईसीसी सत्यापन",
        "title_en": "BPL Certificate / SECC Verification",
        "citation": "उज्ज्वला योजना दिशा-निर्देश पैरा 3.1",
    },
    "income_certificate": {
        "title_hi": "आय प्रमाण पत्र (सक्षम राजस्व अधिकारी जारी)",
        "title_en": "Income Certificate (Tehsildar / Revenue Authority)",
        "citation": "राज्य समाज कल्याण / राजस्व विभाग नियमावली",
    },
    "age_proof": {
        "title_hi": "आयु प्रमाण (मतदाता पहचान पत्र / स्कूल प्रमाण / मेडिकल)",
        "title_en": "Age Proof (Voter ID / School Certificate / Medical)",
        "citation": "एनएसएपी दिशा-निर्देश पैरा 2.2 (आयु >= 60 वर्ष)",
    },
    "birth_certificate": {
        "title_hi": "बालिका का जन्म प्रमाण पत्र (अस्पताल / नगर निकाय)",
        "title_en": "Girl Child Birth Certificate (Municipal / Hospital)",
        "citation": "सुकन्या समृद्धि योजना नियम 2019 नियम 3(1)",
    },
    "guardian_id_proof": {
        "title_hi": "अभिभावक का पहचान पत्र (आधार / वोटर आईडी)",
        "title_en": "Guardian Identity Proof (Aadhaar / Voter ID)",
        "citation": "सुकन्या समृद्धि योजना नियम 2019",
    },
    "address_proof": {
        "title_hi": "निवास प्रमाण पत्र (स्थायी पता)",
        "title_en": "Address / Domicile Proof",
        "citation": "डाकघर बचत बैंक सामान्य नियम 2021",
    },
}


def get_scheme_document_checklist(
    scheme_id: str,
    uploaded_documents: list[dict[str, Any]],
) -> dict[str, Any]:
    """Generates a structured checklist of required vs provided documents for a scheme."""
    # Find scheme in foundation knowledge
    scheme = next((s for s in FOUNDATION_SCHEMES_KNOWLEDGE if s["id"] == scheme_id), None)
    if not scheme:
        raise ValueError(f"योजना आईडी '{scheme_id}' नहीं मिली (Scheme ID not found)")

    required_codes: list[str] = scheme.get("documents_required_json", [])
    total_required = len(required_codes)

    # Map uploaded document types
    uploaded_by_type: dict[str, dict[str, Any]] = {}
    for doc in uploaded_documents:
        t = doc.get("document_type")
        if t:
            uploaded_by_type[t] = doc

    # Also map flexible aliases (e.g. crop_sowing_record matches crop_sowing_certificate)
    aliases = {
        "crop_sowing_certificate": ["crop_sowing_record"],
        "crop_sowing_record": ["crop_sowing_certificate"],
        "bpl_ration_card": ["ration_card", "bpl_certificate"],
        "age_proof": ["aadhaar_card_masked", "birth_certificate"],
        "guardian_id_proof": ["aadhaar_card_masked"],
        "address_proof": ["aadhaar_card_masked"],
        "land_house_site_proof": ["land_khatauni"],
    }

    checklist_items: list[dict[str, Any]] = []
    total_present = 0

    for code in required_codes:
        meta = DOCUMENT_METADATA.get(code, {
            "title_hi": code.replace("_", " ").title(),
            "title_en": code.replace("_", " ").title(),
            "citation": "विभागीय दिशा-निर्देश (Departmental Guidelines)",
        })

        # Check if direct or alias match is present
        matching_doc = uploaded_by_type.get(code)
        if not matching_doc and code in aliases:
            for alt in aliases[code]:
                if alt in uploaded_by_type:
                    matching_doc = uploaded_by_type[alt]
                    break

        if matching_doc:
            is_confirmed = matching_doc.get("citizen_confirmed", False)
            status = "PRESENT" if is_confirmed else "PENDING_CONFIRMATION"
            total_present += 1
            doc_id = matching_doc.get("id")
            is_mock_doc = bool(matching_doc.get("is_mock"))
        else:
            status = "MISSING"
            doc_id = None
            is_mock_doc = False

        checklist_items.append({
            "document_code": code,
            "document_title_hi": meta["title_hi"],
            "document_title_en": meta["title_en"],
            "is_mandatory": True,
            "status": status,
            "matching_document_id": doc_id,
            "is_mock": is_mock_doc,
            "statutory_citation": meta["citation"],
        })

    readiness = (total_present / total_required * 100.0) if total_required > 0 else 100.0

    return {
        "scheme_id": scheme["id"],
        "scheme_name_hi": scheme["name_hi"],
        "scheme_name_en": scheme["name_en"],
        "total_required": total_required,
        "total_present": total_present,
        "readiness_percentage": round(readiness, 1),
        "checklist": checklist_items,
        "is_ready_for_packaging": total_present >= total_required,
        "guideline_notes_hi": scheme.get("application_process_hi", ""),
        "guideline_notes_en": scheme.get("application_process_en", ""),
    }
