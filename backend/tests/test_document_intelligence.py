"""Comprehensive tests for Document Intelligence, Multi-Page OCR, Consistency Audit, and CSC Packaging."""
import io
import os
import uuid
import pytest
from httpx import AsyncClient
from PIL import Image
from reportlab.pdfgen import canvas
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.citizen import Citizen, CitizenProfile
from app.models.document import DocumentRecord
from app.services.ocr.base import OCRExtractionResult
from app.services.ocr.classifier import classify_document_text
from app.services.ocr.consistency import run_cross_document_consistency_checks
from app.services.ocr.mock_provider import MockOCRProvider
from app.services.ocr.pdf_extractor import LocalPDFTextOCRProvider


def _create_sample_pdf(text_pages: list[str]) -> bytes:
    """Creates a genuine multi-page digital PDF in memory using ReportLab."""
    buffer = io.BytesIO()
    c = canvas.Canvas(buffer)
    for text in text_pages:
        c.setFont("Helvetica", 10)
        y = 750
        for line in text.split("\n"):
            c.drawString(50, y, line)
            y -= 15
        c.showPage()
    c.save()
    buffer.seek(0)
    return buffer.getvalue()


def _create_sample_image(width: int = 200, height: int = 200, format: str = "PNG") -> bytes:
    """Creates a valid test image."""
    buffer = io.BytesIO()
    img = Image.new("RGB", (width, height), color=(240, 240, 240))
    img.save(buffer, format=format)
    buffer.seek(0)
    return buffer.getvalue()


async def _init_test_citizen(client: AsyncClient) -> dict[str, str]:
    """Helper to initialize a citizen session for testing."""
    init_res = await client.post(
        "/api/v1/sessions/init",
        json={"preferred_language": "hi", "consent_given": True},
    )
    assert init_res.status_code == 200
    data = init_res.json()
    return {
        "session_id": data["session_id"],
        "citizen_id": data["citizen_id"],
    }


@pytest.mark.asyncio
async def test_magic_bytes_validation_and_tampering_rejection(client: AsyncClient):
    """Verifies that uploaded files are validated via magic bytes, not spoofed extensions."""
    sess = await _init_test_citizen(client)
    headers = {"X-Session-ID": sess["session_id"]}

    # 1. Malicious executable disguised as a PDF
    fake_pdf = b"MZ\x90\x00\x03\x00\x00\x00ThisIsAnExecutable"
    res1 = await client.post(
        "/api/v1/documents/upload",
        data={"citizen_id": sess["citizen_id"]},
        files={"file": ("malicious.pdf", fake_pdf, "application/pdf")},
        headers=headers,
    )
    assert res1.status_code == 400
    assert "अमान्य फ़ाइल प्रकार" in res1.json()["detail"]

    # 2. Plain text file disguised as PNG
    fake_png = b"Hello world, I am just a text file"
    res2 = await client.post(
        "/api/v1/documents/upload",
        data={"citizen_id": sess["citizen_id"]},
        files={"file": ("avatar.png", fake_png, "image/png")},
        headers=headers,
    )
    assert res2.status_code == 400
    assert "अमान्य फ़ाइल प्रकार" in res2.json()["detail"]


@pytest.mark.asyncio
async def test_file_size_limit_rejection(client: AsyncClient):
    """Verifies that documents larger than MAX_DOCUMENT_FILE_SIZE_BYTES are rejected."""
    sess = await _init_test_citizen(client)
    headers = {"X-Session-ID": sess["session_id"]}

    # Create 11MB file with valid PDF magic prefix
    oversized = b"%PDF-1.4" + (b"0" * (11 * 1024 * 1024))
    res = await client.post(
        "/api/v1/documents/upload",
        data={"citizen_id": sess["citizen_id"]},
        files={"file": ("large.pdf", oversized, "application/pdf")},
        headers=headers,
    )
    assert res.status_code == 413
    assert "सीमा" in res.json()["detail"]


@pytest.mark.asyncio
async def test_local_pdf_text_ocr_multi_page_and_zero_aadhaar():
    """Verifies multi-page digital PDF text extraction, masking, and truthful non-mock reporting."""
    page1 = (
        "Uttar Pradesh Revenue Council - Khatauni\n"
        "Name: Ram Kumar\n"
        "Khata No: 00142\n"
        "Khasra No: 142/1\n"
        "Area: 1.45 Hectare"
    )
    page2 = (
        "State Bank of India Passbook\n"
        "Account: 123456789012\n"
        "IFSC: SBIN0001234\n"
        "Aadhaar Number: 4819 1234 9999"
    )
    pdf_bytes = _create_sample_pdf([page1, page2])

    test_path = settings.DOCUMENTS_TEMP_DIR / f"test_{uuid.uuid4().hex}.pdf"
    settings.DOCUMENTS_TEMP_DIR.mkdir(parents=True, exist_ok=True)
    with open(test_path, "wb") as f:
        f.write(pdf_bytes)

    try:
        extractor = LocalPDFTextOCRProvider(max_pages=5)
        result = await extractor.process_document(test_path, "application/pdf")

        # 1. Truthful provider reporting
        assert result.is_mock is False
        assert result.provider_name == "LocalPDFTextOCRProvider"

        # 2. Multi-page extracted
        assert len(result.pages) == 2
        assert result.pages[0].page_number == 1
        assert result.pages[1].page_number == 2

        # 3. Extracted fields
        fields = result.extracted_fields
        assert fields.get("ifsc_code") == "SBIN0001234"
        assert fields.get("account_number_masked") == "XXXXXX9012"
        assert fields.get("land_area_hectares") == 1.45

        # 4. Zero Aadhaar storage enforcement: raw Aadhaar deleted, only masked preserved
        assert "aadhaar_number" not in fields
        assert result.masked_identifier == "XXXX-XXXX-9999"
        assert fields.get("aadhaar_number_masked") == "XXXX-XXXX-9999"

    finally:
        if test_path.exists():
            test_path.unlink()


@pytest.mark.asyncio
async def test_mock_ocr_truthful_disclosure():
    """Verifies that MockOCRProvider explicitly sets is_mock=True and provider_name='MockOCRProvider'."""
    provider = MockOCRProvider()
    dummy_path = settings.DOCUMENTS_TEMP_DIR / "dummy.png"
    result = await provider.process_document(dummy_path, "image/png", hint_document_type="land_khatauni")

    assert result.is_mock is True
    assert result.provider_name == "MockOCRProvider"
    assert result.document_type == "land_khatauni"
    assert "land_area_hectares" in result.extracted_fields
    assert len(result.warnings) > 0
    assert "सिम्युलेटेड मॉक ओसीआर" in result.warnings[0]


@pytest.mark.asyncio
async def test_document_upload_and_unconfirmed_gating(client: AsyncClient):
    """Verifies that document uploads start in UNREVIEWED status without modifying the citizen profile."""
    sess = await _init_test_citizen(client)
    headers = {"X-Session-ID": sess["session_id"]}

    img_bytes = _create_sample_image()
    res = await client.post(
        "/api/v1/documents/upload",
        data={"citizen_id": sess["citizen_id"], "document_type": "land_khatauni"},
        files={"file": ("my_khatauni.png", img_bytes, "image/png")},
        headers=headers,
    )
    assert res.status_code == 200
    doc_data = res.json()

    assert doc_data["review_status"] == "UNREVIEWED"
    assert doc_data["citizen_confirmed"] is False
    assert doc_data["document_type"] == "land_khatauni"
    assert doc_data["page_count"] == 1

    # Verify profile was NOT prematurely modified
    prof_res = await client.get(
        f"/api/v1/profile/{sess['citizen_id']}",
        headers=headers,
    )
    assert prof_res.status_code == 200
    prof = prof_res.json()
    assert prof["owns_agricultural_land"] is None or prof["owns_agricultural_land"] is False


@pytest.mark.asyncio
async def test_human_confirmation_and_profile_sync_gating(client: AsyncClient):
    """Verifies that OCR values are gated until citizen confirms, and profile syncs only when apply_to_profile=True."""
    sess = await _init_test_citizen(client)
    headers = {"X-Session-ID": sess["session_id"]}

    img_bytes = _create_sample_image()
    upload_res = await client.post(
        "/api/v1/documents/upload",
        data={"citizen_id": sess["citizen_id"], "document_type": "land_khatauni"},
        files={"file": ("khatauni.png", img_bytes, "image/png")},
        headers=headers,
    )
    doc_id = upload_res.json()["id"]

    # 1. Citizen confirms with manual correction, but WITHOUT profile sync
    confirm_res1 = await client.put(
        f"/api/v1/documents/{doc_id}/confirm",
        json={
            "confirmed": True,
            "corrections": {"land_area_hectares": 2.0},
            "apply_to_profile": False,
        },
        headers=headers,
    )
    assert confirm_res1.status_code == 200
    assert confirm_res1.json()["review_status"] == "CONFIRMED"
    assert confirm_res1.json()["profile_updated"] is False

    # 2. Citizen confirms WITH profile sync
    confirm_res2 = await client.put(
        f"/api/v1/documents/{doc_id}/confirm",
        json={
            "confirmed": True,
            "corrections": {"land_area_hectares": 2.0},
            "apply_to_profile": True,
        },
        headers=headers,
    )
    assert confirm_res2.status_code == 200
    assert confirm_res2.json()["profile_updated"] is True
    assert "owns_agricultural_land" in confirm_res2.json()["updated_profile_fields"]

    # Verify profile now reflects confirmed landholding
    prof_res = await client.get(
        f"/api/v1/profile/{sess['citizen_id']}",
        headers=headers,
    )
    prof = prof_res.json()
    assert prof["owns_agricultural_land"] is True
    assert prof["land_acres"] > 4.0  # 2.0 Ha * 2.47



@pytest.mark.asyncio
async def test_cross_document_consistency_checks():
    """Verifies name variation detection and landholding consistency checks."""
    docs = [
        {
            "id": "doc1",
            "document_type": "land_khatauni",
            "extracted_fields": {"beneficiary_name": "राम कुमार (Ram Kumar)", "land_area_hectares": 1.45},
            "citizen_confirmed": True,
        },
        {
            "id": "doc2",
            "document_type": "aadhaar_card_masked",
            "extracted_fields": {"beneficiary_name": "रामकुमार", "aadhaar_number_masked": "XXXX-XXXX-4819"},
            "citizen_confirmed": True,
        },
    ]
    # Profile with land conflict
    profile = {
        "full_name": "राम कुमार",
        "owns_agricultural_land": False,
    }

    checks = run_cross_document_consistency_checks(docs, profile)

    # 1. Name match should be found
    name_checks = [c for c in checks if c["field_name"] == "beneficiary_name"]
    assert len(name_checks) >= 1
    assert any(c["status"] in ("MATCH", "VARIATION") for c in name_checks)

    # 2. Land conflict should generate REVIEW_RECOMMENDED
    land_checks = [c for c in checks if c["field_name"] == "owns_agricultural_land"]
    assert len(land_checks) == 1
    assert land_checks[0]["status"] == "REVIEW_RECOMMENDED"
    assert "खतौनी में 1.45 हे. भूमि दर्ज है" in land_checks[0]["message_hi"]


@pytest.mark.asyncio
async def test_scheme_document_checklist(client: AsyncClient):
    """Verifies scheme-specific document checklist evaluation against PM-Kisan."""
    sess = await _init_test_citizen(client)
    headers = {"X-Session-ID": sess["session_id"]}

    # Initial checklist: all missing
    chk_res1 = await client.get(
        f"/api/v1/applications/checklist/pm-kisan?citizen_id={sess['citizen_id']}",
        headers=headers,
    )
    assert chk_res1.status_code == 200
    data1 = chk_res1.json()
    assert data1["scheme_id"] == "pm-kisan"
    assert data1["total_required"] == 3
    assert data1["total_present"] == 0
    assert data1["readiness_percentage"] == 0.0

    # Upload and confirm one document
    img_bytes = _create_sample_image()
    up = await client.post(
        "/api/v1/documents/upload",
        data={"citizen_id": sess["citizen_id"], "document_type": "land_khatauni"},
        files={"file": ("khatauni.png", img_bytes, "image/png")},
        headers=headers,
    )
    doc_id = up.json()["id"]
    await client.put(
        f"/api/v1/documents/{doc_id}/confirm",
        json={"confirmed": True, "apply_to_profile": False},
        headers=headers,
    )

    # Re-check checklist: readiness increases
    chk_res2 = await client.get(
        f"/api/v1/applications/checklist/pm-kisan?citizen_id={sess['citizen_id']}",
        headers=headers,
    )
    data2 = chk_res2.json()
    assert data2["total_present"] == 1
    assert data2["readiness_percentage"] > 30.0


@pytest.mark.asyncio
async def test_csc_package_and_pdf_generation(client: AsyncClient):
    """Verifies generation of CSC Application Package draft and printable ReportLab PDF."""
    sess = await _init_test_citizen(client)
    headers = {"X-Session-ID": sess["session_id"]}

    pkg_res = await client.post(
        "/api/v1/applications/package",
        json={
            "citizen_id": sess["citizen_id"],
            "scheme_id": "pm-kisan",
            "operator_notes": "Test packaging run",
            "disclaimer_acknowledged": True,
        },
        headers=headers,
    )
    assert pkg_res.status_code == 200
    pkg_data = pkg_res.json()

    assert pkg_data["status"] == "DRAFT_READY"
    assert "pdf_download_url" in pkg_data
    assert "STATUTORY DISCLAIMER" in pkg_data["disclaimer"].upper() or "अस्वीकरण" in pkg_data["disclaimer"]

    # Download PDF
    draft_id = pkg_data["draft_id"]
    pdf_res = await client.get(
        f"/api/v1/applications/package/{draft_id}/pdf",
        headers=headers,
    )
    assert pdf_res.status_code == 200
    assert pdf_res.headers["content-type"] == "application/pdf"
    assert pdf_res.content.startswith(b"%PDF-")


@pytest.mark.asyncio
async def test_session_isolation_and_authorization(client: AsyncClient):
    """Verifies that citizen A cannot access citizen B's documents or drafts."""
    sess1 = await _init_test_citizen(client)
    sess2 = await _init_test_citizen(client)

    # Upload document for Citizen 1
    img_bytes = _create_sample_image()
    up = await client.post(
        "/api/v1/documents/upload",
        data={"citizen_id": sess1["citizen_id"]},
        files={"file": ("doc.png", img_bytes, "image/png")},
        headers={"X-Session-ID": sess1["session_id"]},
    )
    doc_id = up.json()["id"]

    # Citizen 2 attempts to fetch Citizen 1's document using Citizen 2's session
    cross_res = await client.get(
        f"/api/v1/documents/{doc_id}",
        headers={"X-Session-ID": sess2["session_id"]},
    )
    assert cross_res.status_code == 403


@pytest.mark.asyncio
async def test_session_termination_kiosk_cleanup(client: AsyncClient, db_session: AsyncSession):
    """Verifies that ending a session physically purges uploaded documents and package PDFs from disk."""
    sess = await _init_test_citizen(client)
    headers = {"X-Session-ID": sess["session_id"]}

    # 1. Upload a document
    img_bytes = _create_sample_image()
    up = await client.post(
        "/api/v1/documents/upload",
        data={"citizen_id": sess["citizen_id"]},
        files={"file": ("temp.png", img_bytes, "image/png")},
        headers=headers,
    )
    doc_id = up.json()["id"]

    # 2. Generate a package PDF
    pkg = await client.post(
        "/api/v1/applications/package",
        json={"citizen_id": sess["citizen_id"], "scheme_id": "pm-kisan"},
        headers=headers,
    )
    draft_id = pkg.json()["draft_id"]

    # Check that file exists on disk
    d_res = await db_session.execute(select(DocumentRecord).where(DocumentRecord.id == doc_id))
    doc_rec = d_res.scalar_one_or_none()
    assert doc_rec is not None
    assert doc_rec.storage_path is not None
    assert os.path.exists(doc_rec.storage_path)

    # 3. Terminate session (Kiosk End Session action)
    term_res = await client.post(
        "/api/v1/sessions/terminate",
        json={"session_id": sess["session_id"]},
    )
    assert term_res.status_code == 200
    assert term_res.json()["data_purged"] is True

    # 4. Verify physical file is gone from disk
    assert not os.path.exists(doc_rec.storage_path)
