"""Deterministic Mock OCR Provider simulating realistic Indian citizen documents.

Explicitly reports is_mock=True and provider_name='MockOCRProvider'.
Never masquerades as a live cloud OCR service.
"""
from pathlib import Path
from typing import Any
from app.services.ocr.base import (
    BaseOCRProvider,
    OCRExtractionResult,
    PageExtractionResult,
)

# Realistic templates for Indian governance documents
MOCK_TEMPLATES: dict[str, dict[str, Any]] = {
    "land_khatauni": {
        "document_type": "land_khatauni",
        "confidence": 0.94,
        "masked_identifier": "KHAT-2024-8891",
        "fields": {
            "beneficiary_name": "राम कुमार (Ram Kumar)",
            "father_name": "श्याम लाल (Shyam Lal)",
            "khata_number": "00142",
            "khasra_numbers": "142/1, 234/2",
            "land_area_hectares": 1.45,
            "village": "रामपुर (Rampur)",
            "tehsil": "सदर (Sadar)",
            "district": "वाराणसी (Varanasi)",
            "state": "उत्तर प्रदेश (Uttar Pradesh)",
            "mutation_status": "प्रमाणित (Verified)",
        },
        "raw_text": (
            "[SIMULATED MOCK OCR - DEMO ONLY]\n"
            "उत्तर प्रदेश राजस्व परिषद - उद्धरण खतौनी (Bhulekh)\n"
            "ग्राम: रामपुर, तहसील: सदर, जनपद: वाराणसी\n"
            "खाता संख्या: 00142\n"
            "खातेदार का नाम: राम कुमार सुपुत्र श्याम लाल\n"
            "खसरा संख्या: 142/1 (0.8500 हे.), 234/2 (0.6000 हे.)\n"
            "कुल क्षेत्रफल: 1.4500 हेक्टेयर\n"
            "हस्ताक्षर: राजस्व निरीक्षक / लेखपाल"
        ),
    },
    "aadhaar_card_masked": {
        "document_type": "aadhaar_card_masked",
        "confidence": 0.96,
        "masked_identifier": "XXXX-XXXX-4819",
        "fields": {
            "beneficiary_name": "राम कुमार (Ram Kumar)",
            "date_of_birth": "15/07/1982",
            "gender": "MALE",
            "aadhaar_number_masked": "XXXX-XXXX-4819",
            "address": "ग्राम रामपुर, पोस्ट बिलसपुर, वाराणसी, उत्तर प्रदेश - 221001",
            "district": "वाराणसी (Varanasi)",
            "state": "उत्तर प्रदेश (Uttar Pradesh)",
        },
        "raw_text": (
            "[SIMULATED MOCK OCR - DEMO ONLY]\n"
            "भारत सरकार / Government of India\n"
            "भारतीय विशिष्ट पहचान प्राधिकरण / UIDAI\n"
            "नाम / Name: राम कुमार (Ram Kumar)\n"
            "जन्म तिथि / DOB: 15/07/1982\n"
            "लिंग / Gender: पुरुष / MALE\n"
            "आधार संख्या: XXXX XXXX 4819\n"
            "मेरा आधार, मेरी पहचान"
        ),
    },
    "income_certificate": {
        "document_type": "income_certificate",
        "confidence": 0.92,
        "masked_identifier": "INC-2026-9021",
        "fields": {
            "beneficiary_name": "राम कुमार (Ram Kumar)",
            "father_name": "श्याम लाल (Shyam Lal)",
            "annual_income": 65000.0,
            "income_in_words": "पैंसठ हज़ार रुपये मात्र (Sixty Five Thousand Rupees Only)",
            "issuing_authority": "कार्यालय तहसीलदार (Office of Tehsildar)",
            "issue_date": "10/01/2026",
            "valid_until": "09/01/2029",
            "district": "वाराणसी (Varanasi)",
        },
        "raw_text": (
            "[SIMULATED MOCK OCR - DEMO ONLY]\n"
            "कार्यालय तहसीलदार, सदर, जनपद वाराणसी (उत्तर प्रदेश)\n"
            "प्रमाण पत्र क्रमांक: INC/2026/9021\n"
            "आय प्रमाण पत्र (Income Certificate)\n"
            "प्रमाणित किया जाता है कि श्री राम कुमार पुत्र श्री श्याम लाल, निवासी ग्राम रामपुर\n"
            "की समस्त स्रोतों से कुल पारिवारिक वार्षिक आय ₹65,000 (पैंसठ हज़ार रुपये) है।\n"
            "सक्षम अधिकारी: तहसीलदार सदर"
        ),
    },
    "ration_card": {
        "document_type": "ration_card",
        "confidence": 0.91,
        "masked_identifier": "RC-XXXXXX4512",
        "fields": {
            "beneficiary_name": "राम कुमार (Ram Kumar)",
            "card_type": "PHH (पात्र गृहस्थी)",
            "ration_card_number_masked": "XXXXXX4512",
            "family_members_count": 4,
            "fair_price_shop_code": "FPS-0912",
            "village": "रामपुर",
            "district": "वाराणसी",
        },
        "raw_text": (
            "[SIMULATED MOCK OCR - DEMO ONLY]\n"
            "खाद्य एवं रसद विभाग, उत्तर प्रदेश\n"
            "राष्ट्रीय खाद्य सुरक्षा अधिनियम (NFSA) राशन कार्ड\n"
            "राशन कार्ड संख्या: 215400234512\n"
            "कार्ड का प्रकार: पात्र गृहस्थी (PHH)\n"
            "मुखिया का नाम: राम कुमार\n"
            "सदस्यों की कुल संख्या: 4\n"
            "उचित दर दुकान कोड: FPS-0912"
        ),
    },
    "bank_passbook": {
        "document_type": "bank_passbook",
        "confidence": 0.95,
        "masked_identifier": "XXXXXX3489",
        "fields": {
            "beneficiary_name": "राम कुमार (Ram Kumar)",
            "bank_name": "भारतीय स्टेट बैंक (State Bank of India)",
            "account_number_masked": "XXXXXX3489",
            "ifsc_code": "SBIN0001234",
            "branch": "वाराणसी मुख्य शाखा (Varanasi Main Branch)",
            "dbt_enabled": True,
        },
        "raw_text": (
            "[SIMULATED MOCK OCR - DEMO ONLY]\n"
            "भारतीय स्टेट बैंक / STATE BANK OF INDIA\n"
            "बचत बैंक खाता पासबुक (Savings Bank Passbook)\n"
            "खातेदार: राम कुमार (Ram Kumar)\n"
            "खाता संख्या: XXXXXX3489\n"
            "आईएफएससी (IFSC): SBIN0001234\n"
            "शाखा: वाराणसी मुख्य (01234)\n"
            "आधार सीडिंग स्थिति: सक्रिय (Aadhaar Seeded / DBT Active)"
        ),
    },
    "birth_certificate": {
        "document_type": "birth_certificate",
        "confidence": 0.93,
        "masked_identifier": "BIRTH-2022-7712",
        "fields": {
            "child_name": "प्रिया कुमारी (Priya Kumari)",
            "date_of_birth": "12/04/2022",
            "gender": "FEMALE",
            "father_name": "राम कुमार (Ram Kumar)",
            "mother_name": "सुनीता देवी (Sunita Devi)",
            "registration_number": "B-2022-7712",
        },
        "raw_text": (
            "[SIMULATED MOCK OCR - DEMO ONLY]\n"
            "जन्म एवं मृत्यु पंजीकरण कार्यालय / Office of Registrar of Births\n"
            "जन्म प्रमाण पत्र (Birth Certificate)\n"
            "नाम: प्रिया कुमारी (Priya Kumari)\n"
            "जन्म तिथि: 12/04/2022\n"
            "लिंग: महिला / FEMALE\n"
            "पिता का नाम: राम कुमार\n"
            "माता का नाम: सुनीता देवी\n"
            "पंजीकरण संख्या: B-2022-7712"
        ),
    },
    "crop_sowing_record": {
        "document_type": "crop_sowing_record",
        "confidence": 0.90,
        "masked_identifier": "SOW-2026-KHARIF",
        "fields": {
            "beneficiary_name": "राम कुमार (Ram Kumar)",
            "khasra_number": "142/1",
            "crop_name": "धान (Paddy - Kharif)",
            "sown_area_hectares": 1.20,
            "season": "खरीफ 2026 (Kharif 2026)",
            "patwari_verified": True,
        },
        "raw_text": (
            "[SIMULATED MOCK OCR - DEMO ONLY]\n"
            "राजस्व विभाग - फसल बोआई गिरदावरी प्रमाण पत्र\n"
            "कृषक का नाम: राम कुमार पुत्र श्याम लाल\n"
            "खसरा संख्या: 142/1\n"
            "बोई गई फसल: धान (Paddy)\n"
            "रकबा: 1.20 हेक्टेयर\n"
            "मौसम: खरीफ 2026\n"
            "सत्यापन: हल्का लेखपाल / पटवारी"
        ),
    },
    "bpl_certificate": {
        "document_type": "bpl_certificate",
        "confidence": 0.89,
        "masked_identifier": "BPL-UP-3419",
        "fields": {
            "beneficiary_name": "राम कुमार (Ram Kumar)",
            "bpl_id": "BPL-UP-3419",
            "survey_year": "2002",
            "score": "14",
            "category": "BPL",
        },
        "raw_text": (
            "[SIMULATED MOCK OCR - DEMO ONLY]\n"
            "जिला ग्रामीण विकास अभिकरण (DRDA)\n"
            "बीपीएल प्रमाण पत्र (BPL Certificate)\n"
            "प्रमाणित किया जाता है कि राम कुमार बीपीएल सूची में क्रमांक 3419 पर दर्ज हैं।"
        ),
    },
}


class MockOCRProvider(BaseOCRProvider):
    """Deterministic Mock OCR Provider for tests, demonstrations, and scanned image fallbacks.
    
    Always sets is_mock=True and provider_name='MockOCRProvider'.
    """

    async def process_document(
        self,
        file_path: Path,
        mime_type: str,
        hint_document_type: str | None = None,
    ) -> OCRExtractionResult:
        doc_type = hint_document_type or "land_khatauni"
        if doc_type not in MOCK_TEMPLATES:
            # Fallback to closest or default
            for t in MOCK_TEMPLATES:
                if t in doc_type or doc_type in t:
                    doc_type = t
                    break
            else:
                doc_type = "land_khatauni"

        template = MOCK_TEMPLATES[doc_type]
        raw_text = template["raw_text"]
        fields = dict(template["fields"])
        masked_id = template.get("masked_identifier")

        pages = [
            PageExtractionResult(
                page_number=1,
                raw_text=raw_text,
                fields=fields,
            )
        ]

        return OCRExtractionResult(
            provider_name="MockOCRProvider",
            is_mock=True,
            document_type=doc_type,
            overall_confidence=template["confidence"],
            pages=pages,
            extracted_fields=fields,
            masked_identifier=masked_id,
            raw_text_summary=raw_text[:500],
            warnings=[
                "सिम्युलेटेड मॉक ओसीआर परिणाम (Simulated Mock OCR Result - No live OCR API key)",
                "यह डेटा केवल प्रदर्शन हेतु है, वास्तविक दस्तावेज़ से सत्यापित करें (Demo only - verify against original scan)",
            ],
        )
