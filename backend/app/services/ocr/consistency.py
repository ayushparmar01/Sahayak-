"""Cross-document and citizen profile consistency audit engine."""
import re
from typing import Any
from difflib import SequenceMatcher

HONORIFICS = ["श्री", "श्रीमती", "सुश्री", "कु.", "डॉ.", "shri", "smt", "mr", "mrs", "miss", "dr", "kumar", "kumari"]


def _clean_name(name: str) -> str:
    """Removes honorifics, punctuation, and extra whitespace."""
    if not name:
        return ""
    # Remove parenthesized English/Hindi alternates like 'राम कुमार (Ram Kumar)' -> 'राम कुमार'
    n = re.sub(r"\(.*?\)", "", name)
    tokens = re.split(r"[\s,\.\-]+", n.lower().strip())
    clean_tokens = [t for t in tokens if t and t not in HONORIFICS]
    return " ".join(clean_tokens)


def _fuzzy_similarity(str1: str, str2: str) -> float:
    """Returns ratio between 0.0 and 1.0."""
    c1 = _clean_name(str1)
    c2 = _clean_name(str2)
    if not c1 or not c2:
        return 0.0
    # Check exact token subset
    s1, s2 = set(c1.split()), set(c2.split())
    if s1 and s2 and (s1.issubset(s2) or s2.issubset(s1)):
        return 0.95
    return SequenceMatcher(None, c1, c2).ratio()


def run_cross_document_consistency_checks(
    documents: list[dict[str, Any]],
    profile: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    """Runs cross-document and profile consistency checks.
    
    Generates constructive, non-accusatory review guidance.
    """
    checks: list[dict[str, Any]] = []
    profile_data = profile or {}

    # Extract names from documents
    doc_names: list[tuple[str, str, str]] = []  # (doc_id, doc_type, name)
    for doc in documents:
        fields = doc.get("extracted_fields") or {}
        # Also check user_corrections if present
        corrections = doc.get("user_corrections") or {}
        active_fields = {**fields, **corrections}

        name = active_fields.get("beneficiary_name") or active_fields.get("child_name")
        if name:
            doc_names.append((doc.get("id", "doc"), doc.get("document_type", "unknown"), str(name)))

    profile_name = profile_data.get("full_name") or profile_data.get("name")
    if profile_name and doc_names:
        # Check profile name vs document names
        for doc_id, doc_type, d_name in doc_names:
            sim = _fuzzy_similarity(profile_name, d_name)
            if sim >= 0.80:
                checks.append({
                    "check_id": f"name_match_{doc_id[:8]}",
                    "field_name": "beneficiary_name",
                    "document_type": doc_type,
                    "document_value": d_name,
                    "profile_value": profile_name,
                    "status": "MATCH",
                    "message_hi": f"नाम का मिलान सफल ({doc_type}): '{d_name}' प्रोफ़ाइल नाम '{profile_name}' से मेल खाता है।",
                    "message_en": f"Name matched ({doc_type}): '{d_name}' matches profile name '{profile_name}'.",
                })
            elif sim >= 0.45:
                checks.append({
                    "check_id": f"name_var_{doc_id[:8]}",
                    "field_name": "beneficiary_name",
                    "document_type": doc_type,
                    "document_value": d_name,
                    "profile_value": profile_name,
                    "status": "VARIATION",
                    "message_hi": f"नाम में वर्तनी भिन्नता ({doc_type}): दस्तावेज़ में '{d_name}', प्रोफ़ाइल में '{profile_name}'। सीएससी ऑपरेटर सत्यापन अनुशंसित।",
                    "message_en": f"Spelling variation detected ({doc_type}): document has '{d_name}', profile has '{profile_name}'. CSC operator verification recommended.",
                })
            else:
                checks.append({
                    "check_id": f"name_diff_{doc_id[:8]}",
                    "field_name": "beneficiary_name",
                    "document_type": doc_type,
                    "document_value": d_name,
                    "profile_value": profile_name,
                    "status": "REVIEW_RECOMMENDED",
                    "message_hi": f"नाम में भिन्नता ({doc_type}): कृपया सुनिश्चित करें कि दस्तावेज़ उसी लाभार्थी का है ('{d_name}' बनाम '{profile_name}')।",
                    "message_en": f"Name difference ({doc_type}): Please ensure document belongs to the same applicant ('{d_name}' vs '{profile_name}').",
                })

    # Cross-document name check (between documents)
    if len(doc_names) >= 2:
        base_id, base_type, base_name = doc_names[0]
        for other_id, other_type, other_name in doc_names[1:]:
            sim = _fuzzy_similarity(base_name, other_name)
            if sim < 0.60:
                checks.append({
                    "check_id": f"cross_doc_name_{base_id[:4]}_{other_id[:4]}",
                    "field_name": "cross_document_name",
                    "document_type": f"{base_type} vs {other_type}",
                    "document_value": base_name,
                    "profile_value": other_name,
                    "status": "VARIATION",
                    "message_hi": f"दो दस्तावेज़ों में नाम भिन्न हैं: {base_type} में '{base_name}', {other_type} में '{other_name}'।",
                    "message_en": f"Name variation across documents: '{base_name}' in {base_type} vs '{other_name}' in {other_type}.",
                })

    # Land consistency check
    khatauni_docs = [d for d in documents if d.get("document_type") == "land_khatauni"]
    if khatauni_docs:
        k_fields = khatauni_docs[0].get("extracted_fields") or {}
        k_area = k_fields.get("land_area_hectares")
        profile_owns_land = profile_data.get("owns_agricultural_land")
        if k_area and profile_owns_land is False:
            checks.append({
                "check_id": "land_record_conflict",
                "field_name": "owns_agricultural_land",
                "document_type": "land_khatauni",
                "document_value": f"{k_area} हेक्टेयर",
                "profile_value": "भूमिहीन (No Land)",
                "status": "REVIEW_RECOMMENDED",
                "message_hi": f"खतौनी में {k_area} हे. भूमि दर्ज है, जबकि प्रोफ़ाइल में भूमिहीन चुना गया था। प्रोफ़ाइल अद्यतन अनुशंसित है।",
                "message_en": f"Khatauni shows {k_area} Ha land, whereas profile indicates no agricultural land. Profile update recommended.",
            })
        elif k_area and (profile_owns_land is True or profile_owns_land is None):
            checks.append({
                "check_id": "land_record_verified",
                "field_name": "owns_agricultural_land",
                "document_type": "land_khatauni",
                "document_value": f"{k_area} हेक्टेयर",
                "profile_value": "भूमि स्वामी (Landowner)",
                "status": "MATCH",
                "message_hi": f"खतौनी भूलेख सत्यापन पूर्ण: कुल रकबा {k_area} हेक्टेयर।",
                "message_en": f"Land record verified from Khatauni: Total area {k_area} hectares.",
            })

    # Income certificate consistency check
    inc_docs = [d for d in documents if d.get("document_type") == "income_certificate"]
    if inc_docs:
        inc_fields = inc_docs[0].get("extracted_fields") or {}
        cert_income = inc_fields.get("annual_income")
        prof_income = profile_data.get("annual_income")
        if cert_income and prof_income:
            diff = abs(float(cert_income) - float(prof_income))
            if diff > 25000:
                checks.append({
                    "check_id": "income_variance",
                    "field_name": "annual_income",
                    "document_type": "income_certificate",
                    "document_value": f"₹{cert_income:,.0f}",
                    "profile_value": f"₹{prof_income:,.0f}",
                    "status": "VARIATION",
                    "message_hi": f"आय में भिन्नता: प्रमाण पत्र में ₹{cert_income:,.0f}, प्रोफ़ाइल में ₹{prof_income:,.0f}। प्रमाण पत्र की आय प्राथमिक मानी जाएगी।",
                    "message_en": f"Income variance: ₹{cert_income:,.0f} in certificate vs ₹{prof_income:,.0f} in profile. Certificate value takes precedence.",
                })
            else:
                checks.append({
                    "check_id": "income_verified",
                    "field_name": "annual_income",
                    "document_type": "income_certificate",
                    "document_value": f"₹{cert_income:,.0f}",
                    "profile_value": f"₹{prof_income:,.0f}",
                    "status": "MATCH",
                    "message_hi": f"सत्यापित वार्षिक पारिवारिक आय: ₹{cert_income:,.0f}।",
                    "message_en": f"Verified annual family income: ₹{cert_income:,.0f}.",
                })

    return checks
