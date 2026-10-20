"""Multi-page digital PDF text extractor using PyPDF2."""
import re
from pathlib import Path
from typing import Any
import PyPDF2

from app.core.config import settings
from app.services.ocr.base import (
    BaseOCRProvider,
    FieldExtractionResult,
    OCRExtractionResult,
    PageExtractionResult,
)
from app.services.ocr.classifier import classify_document_text


def _mask_aadhaar_text(text: str) -> str:
    """Masks all 12-digit Aadhaar number occurrences in free text to XXXX-XXXX-NNNN.
    
    Protects bank account numbers from accidental over-masking while strictly
    scrubbing any 12-digit Aadhaar pattern (standard 4-4-4 grouped or Aadhaar-labeled).
    """
    if not text:
        return ""
    # Mask standard 4-4-4 spaced/hyphenated numbers starting with 2-9 (standard Aadhaar format)
    masked = re.sub(
        r"\b([2-9]\d{3})[\s-](\d{4})[\s-](\d{4})\b",
        r"XXXX-XXXX-\3",
        text,
    )
    # Also mask contiguous or spaced 12 digits explicitly labeled with Aadhaar/UID
    masked = re.sub(
        r"((?:Aadhaar|आधार|UID)[^\n\d]{0,20})([2-9]\d{3})[\s-]?(\d{4})[\s-]?(\d{4})\b",
        r"\1XXXX-XXXX-\4",
        masked,
        flags=re.IGNORECASE,
    )
    return masked


class LocalPDFTextOCRProvider(BaseOCRProvider):
    """Extracts text and key fields directly from digital multi-page PDFs using PyPDF2.
    
    Reports is_mock=False and provider_name='LocalPDFTextOCRProvider'.
    Strictly masks all Aadhaar occurrences across all page and summary representations.
    """

    def __init__(self, max_pages: int = settings.MAX_DOCUMENT_PAGE_COUNT):
        self.max_pages = max_pages

    async def process_document(
        self,
        file_path: Path,
        mime_type: str,
        hint_document_type: str | None = None,
    ) -> OCRExtractionResult:
        if not file_path.exists():
            raise FileNotFoundError(f"PDF file not found at: {file_path}")

        pages_extracted: list[PageExtractionResult] = []
        all_text = []
        overall_fields: dict[str, Any] = {}
        masked_identifier: str | None = None
        warnings: list[str] = []

        try:
            with open(file_path, "rb") as f:
                reader = PyPDF2.PdfReader(f)

                if reader.is_encrypted:
                    raise ValueError("सुरक्षित/पासवर्ड-संरक्षित पीडीएफ समर्थित नहीं है (Password protected PDF is not supported)")

                num_pages = len(reader.pages)
                if num_pages > self.max_pages:
                    warnings.append(
                        f"दस्तावेज़ में {num_pages} पृष्ठ हैं, केवल पहले {self.max_pages} पृष्ठ संसाधित किए गए (Truncated to first {self.max_pages} pages)"
                    )

                pages_to_process = min(num_pages, self.max_pages)

                for page_idx in range(pages_to_process):
                    page = reader.pages[page_idx]
                    raw_extracted = page.extract_text() or ""
                    # Zero Aadhaar retention: mask immediately at page level
                    page_text = _mask_aadhaar_text(raw_extracted)
                    all_text.append(page_text)

                    page_fields = self._extract_page_fields(raw_extracted, page_idx + 1)
                    pages_extracted.append(
                        PageExtractionResult(
                            page_number=page_idx + 1,
                            raw_text=page_text.strip(),
                            fields=page_fields,
                        )
                    )
                    # Merge page fields into overall
                    for k, v in page_fields.items():
                        if k not in overall_fields or not overall_fields[k]:
                            overall_fields[k] = v

        except Exception as e:
            if isinstance(e, (ValueError, FileNotFoundError)):
                raise
            raise RuntimeError(f"पीडीएफ पढ़ने में त्रुटि (PDF read error): {str(e)}")

        combined_text = "\n\n--- Page Break ---\n\n".join(all_text)
        doc_type, confidence = classify_document_text(combined_text, hint=hint_document_type)

        # Aadhaar masking enforcement across overall fields
        masked_identifier = None
        aadhaar_match = re.search(r"\b(?:\d{4}|XXXX)[\s-](?:\d{4}|XXXX)[\s-](\d{4})\b", combined_text, re.IGNORECASE)
        if aadhaar_match:
            masked_identifier = f"XXXX-XXXX-{aadhaar_match.group(1)}"
            overall_fields["aadhaar_number_masked"] = masked_identifier
            if "aadhaar_number" in overall_fields:
                del overall_fields["aadhaar_number"]

        return OCRExtractionResult(
            provider_name="LocalPDFTextOCRProvider",
            is_mock=False,
            document_type=doc_type,
            overall_confidence=confidence if combined_text.strip() else 0.40,
            pages=pages_extracted,
            extracted_fields=overall_fields,
            masked_identifier=masked_identifier or overall_fields.get("masked_identifier") or overall_fields.get("aadhaar_number_masked"),
            raw_text_summary=_mask_aadhaar_text(combined_text[:1000]) if combined_text else "",
            warnings=warnings,
        )


    def _extract_page_fields(self, text: str, page_num: int) -> dict[str, Any]:
        """Extracts standard government document patterns from raw text."""
        fields: dict[str, Any] = {}

        # 1. Bank Account Number & IFSC
        ifsc_match = re.search(r"\b([A-Z]{4}0[A-Z0-9]{6})\b", text)
        if ifsc_match:
            fields["ifsc_code"] = ifsc_match.group(1)

        acc_match = re.search(r"(?:Account|खाता\s*(?:संख्या|नं))\s*[:\-]?\s*([0-9]{9,18})", text, re.IGNORECASE)
        if acc_match:
            full_acc = acc_match.group(1)
            fields["account_number_masked"] = f"XXXXXX{full_acc[-4:]}"

        # 2. Land Khatauni details
        khata_match = re.search(r"(?:खाता\s*संख्या|Khata\s*No\.?)\s*[:\-]?\s*([0-9/\-]+)", text, re.IGNORECASE)
        if khata_match:
            fields["khata_number"] = khata_match.group(1).strip()

        khasra_match = re.search(r"(?:खसरा|गाटा\s*संख्या|Khasra\s*No\.?)\s*[:\-]?\s*([0-9/,\-\s]+)", text, re.IGNORECASE)
        if khasra_match:
            fields["khasra_number"] = khasra_match.group(1).strip()

        area_match = re.search(r"(?:क्षेत्रफल|Area)\s*[:\-]?\s*([0-9]+(?:\.[0-9]+)?)\s*(?:हेक्टेयर|Hectare|Acre|एकड़)", text, re.IGNORECASE)
        if area_match:
            try:
                fields["land_area_hectares"] = float(area_match.group(1))
            except ValueError:
                pass

        # 3. Income details
        income_match = re.search(r"(?:वार्षिक\s*आय|Annual\s*Income)\s*[:\-]?\s*(?:₹|Rs\.?)?\s*([0-9,]+)", text, re.IGNORECASE)
        if income_match:
            try:
                val = float(income_match.group(1).replace(",", ""))
                fields["annual_income"] = val
            except ValueError:
                pass

        # 4. Beneficiary Name
        name_match = re.search(r"(?:नाम|Name|खातेदार)\s*[:\-]?\s*([A-Za-z\u0900-\u097F\s]{3,35})(?:\n|$)", text)
        if name_match:
            extracted_name = name_match.group(1).strip()
            # Filter noise
            if not any(token in extracted_name.lower() for token in ["government", "bharat", "portal", "digital"]):
                fields["beneficiary_name"] = extracted_name

        # 5. Date of Birth / Age
        dob_match = re.search(r"(?:जन्म\s*तिथि|DOB|Date of Birth)\s*[:\-]?\s*([0-9]{2}[/-][0-9]{2}[/-][0-9]{4})", text, re.IGNORECASE)
        if dob_match:
            fields["date_of_birth"] = dob_match.group(1)

        # 6. Ration Card Number
        rc_match = re.search(r"(?:राशन\s*कार्ड\s*संख्या|Ration\s*Card\s*No\.?)\s*[:\-]?\s*([0-9]{10,14})", text, re.IGNORECASE)
        if rc_match:
            full_rc = rc_match.group(1)
            fields["ration_card_number_masked"] = f"XXXXXX{full_rc[-4:]}"

        return fields
