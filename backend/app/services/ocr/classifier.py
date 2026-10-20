"""Rule-based document classifier detecting standard Indian citizen document types."""
import re
from typing import Any

# Keywords in Hindi (Devanagari) and English for document detection
CLASSIFICATION_RULES = [
    {
        "type": "aadhaar_card_masked",
        "keywords": [
            "आधार", "uidai", "unique identification", "मेरा आधार", "aadhaar",
            "भारत सरकार", "government of india", "mera aadhaar", "आम आदमी का अधिकार"
        ],
        "weight": 2.0,
    },
    {
        "type": "land_khatauni",
        "keywords": [
            "खतौनी", "भूलेख", "खसरा", "गाटा", "खाता संख्या", "भू-अभिलेख", "खातेदार",
            "क्षेत्रफल", "हेक्टेयर", "राजस्व परिषद", "khatauni", "khasra", "ror",
            "record of rights", "land record", "bhulekh"
        ],
        "weight": 2.5,
    },
    {
        "type": "ration_card",
        "keywords": [
            "राशन कार्ड", "खाद्य एवं रसद", "राष्ट्रीय खाद्य सुरक्षा", "nfsa", "ration card",
            "अंत्योदय", "antyodaya", "aay", "phh", "पात्र गृहस्थी", "bpl राशन", "fair price shop",
            "उचित दर दुकान"
        ],
        "weight": 2.0,
    },
    {
        "type": "income_certificate",
        "keywords": [
            "आय प्रमाण पत्र", "income certificate", "वार्षिक आय", "तहसीलदार", "tehsildar",
            "राजस्व विभाग", "प्रमाणित किया जाता है कि", "annual income", "सत्यापित आय"
        ],
        "weight": 2.5,
    },
    {
        "type": "bank_passbook",
        "keywords": [
            "पासबुक", "passbook", "खाता संख्या", "account no", "ifsc", "शाखा", "branch",
            "state bank", "punjab national bank", "bank of baroda", "saving bank",
            "बचत खाता", "current account"
        ],
        "weight": 2.0,
    },
    {
        "type": "birth_certificate",
        "keywords": [
            "जन्म प्रमाण पत्र", "birth certificate", "नगर निगम", "नगर पालिका", "जन्म तिथि",
            "date of birth", "registrar", "पंजीयक", "प्रपत्र संख्या 5"
        ],
        "weight": 2.5,
    },
    {
        "type": "crop_sowing_record",
        "keywords": [
            "बोआई प्रमाण", "फसल", "गिरदावरी", "girdawari", "crop sowing", "पटवारी",
            "रकबा", "खरीफ", "रबी", "patwari report"
        ],
        "weight": 2.5,
    },
    {
        "type": "bpl_certificate",
        "keywords": [
            "बीपीएल प्रमाण पत्र", "bpl certificate", "गरीबी रेखा से नीचे", "below poverty line",
            "bpl सर्वे", "bpl सूची"
        ],
        "weight": 2.0,
    },
]


def classify_document_text(text: str, hint: str | None = None) -> tuple[str, float]:
    """Classifies document type using weighted keyword matching.
    
    Returns:
        tuple[document_type, confidence_score]
    """
    if not text or not text.strip():
        return (hint or "other", 0.3 if hint else 0.1)

    lowered = text.lower()
    scores: dict[str, float] = {}

    for rule in CLASSIFICATION_RULES:
        doc_type = rule["type"]
        weight = float(rule["weight"])
        match_count = 0
        for kw in rule["keywords"]:
            if kw in lowered:
                match_count += 1
        if match_count > 0:
            scores[doc_type] = scores.get(doc_type, 0.0) + (match_count * weight)

    # If hint was provided, give it a small boost if keywords also present
    if hint and hint in scores:
        scores[hint] += 2.0

    if not scores:
        return (hint or "other", 0.4 if hint else 0.2)

    best_type = max(scores, key=scores.get)
    best_score = scores[best_type]
    # Normalize confidence to [0.5, 0.98]
    confidence = min(0.98, max(0.50, 0.50 + (best_score * 0.08)))
    return (best_type, round(confidence, 2))
