"""Independent Security & Data Integrity Gate Regression Tests for Phase 4.

Verifies:
1. Cross-Session IDOR prevention across all document and application packaging endpoints.
2. Zero Aadhaar persistence across raw text, page extractions, and SQLite columns.
3. Failed upload / OCR physical file cleanup.
4. Truthful Mock OCR disclosures in checklist and generated ReportLab PDF.
"""
import io
import os
import uuid
from unittest.mock import patch
import pytest
from httpx import AsyncClient
from PIL import Image
from PyPDF2 import PdfReader
from reportlab.pdfgen import canvas
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.citizen import Citizen, CitizenProfile
from app.models.document import DocumentRecord


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


def _create_sample_image(width: int = 150, height: int = 150) -> bytes:
    """Creates a valid test image in memory."""
    buffer = io.BytesIO()
    img = Image.new("RGB", (width, height), color=(245, 245, 245))
    img.save(buffer, format="PNG")
    buffer.seek(0)
    return buffer.getvalue()


async def _init_test_citizen(client: AsyncClient) -> dict[str, str]:
    """Helper to initialize a fresh citizen session."""
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
async def test_idor_document_cross_session_forbidden(client: AsyncClient):
    """Verifies that Citizen B cannot view, confirm, or delete Citizen A's documents."""
    sess_a = await _init_test_citizen(client)
    sess_b = await _init_test_citizen(client)

    # 1. Citizen A uploads document
    img_bytes = _create_sample_image()
    up = await client.post(
        "/api/v1/documents/upload",
        data={"citizen_id": sess_a["citizen_id"], "document_type": "land_khatauni"},
        files={"file": ("land.png", img_bytes, "image/png")},
        headers={"X-Session-ID": sess_a["session_id"]},
    )
    assert up.status_code == 200
    doc_id = up.json()["id"]

    # 2. Citizen B attempts GET document detail -> 403
    res_get = await client.get(
        f"/api/v1/documents/{doc_id}",
        headers={"X-Session-ID": sess_b["session_id"]},
    )
    assert res_get.status_code == 403

    # 3. Citizen B attempts PUT confirmation -> 403
    res_confirm = await client.put(
        f"/api/v1/documents/{doc_id}/confirm",
        json={"confirmed": True, "apply_to_profile": True},
        headers={"X-Session-ID": sess_b["session_id"]},
    )
    assert res_confirm.status_code == 403

    # 4. Citizen B attempts DELETE document -> 403
    res_del = await client.delete(
        f"/api/v1/documents/{doc_id}",
        headers={"X-Session-ID": sess_b["session_id"]},
    )
    assert res_del.status_code == 403

    # 5. Missing session header -> 403
    res_no_sess = await client.get(f"/api/v1/documents/{doc_id}")
    assert res_no_sess.status_code == 403

    # 6. Random/non-existent doc_id with Citizen A's session -> 404
    res_404 = await client.get(
        f"/api/v1/documents/{uuid.uuid4()}",
        headers={"X-Session-ID": sess_a["session_id"]},
    )
    assert res_404.status_code == 404


@pytest.mark.asyncio
async def test_idor_pdf_download_cross_session_forbidden(client: AsyncClient):
    """Verifies that Citizen B cannot download Citizen A's CSC package PDF."""
    sess_a = await _init_test_citizen(client)
    sess_b = await _init_test_citizen(client)

    # Citizen A packages draft
    pkg_res = await client.post(
        "/api/v1/applications/package",
        json={"citizen_id": sess_a["citizen_id"], "scheme_id": "pm-kisan"},
        headers={"X-Session-ID": sess_a["session_id"]},
    )
    assert pkg_res.status_code == 200
    draft_id = pkg_res.json()["draft_id"]

    # 1. Citizen B attempts download with header -> 403
    res_hdr = await client.get(
        f"/api/v1/applications/package/{draft_id}/pdf",
        headers={"X-Session-ID": sess_b["session_id"]},
    )
    assert res_hdr.status_code == 403

    # 2. Citizen B attempts download with query param -> 403
    res_param = await client.get(
        f"/api/v1/applications/package/{draft_id}/pdf?session_id={sess_b['session_id']}",
    )
    assert res_param.status_code == 403

    # 3. Download attempt without any session -> 403
    res_no_auth = await client.get(
        f"/api/v1/applications/package/{draft_id}/pdf",
    )
    assert res_no_auth.status_code == 403

    # 4. Non-existent draft ID with Citizen A's session -> 404
    res_404 = await client.get(
        f"/api/v1/applications/package/{uuid.uuid4()}/pdf",
        headers={"X-Session-ID": sess_a["session_id"]},
    )
    assert res_404.status_code == 404

    # 5. Citizen A downloads with header -> 200 OK
    res_ok_hdr = await client.get(
        f"/api/v1/applications/package/{draft_id}/pdf",
        headers={"X-Session-ID": sess_a["session_id"]},
    )
    assert res_ok_hdr.status_code == 200
    assert res_ok_hdr.headers["content-type"] == "application/pdf"
    assert res_ok_hdr.content.startswith(b"%PDF-")

    # 6. Citizen A downloads with query param -> 200 OK
    res_ok_param = await client.get(
        f"/api/v1/applications/package/{draft_id}/pdf?session_id={sess_a['session_id']}",
    )
    assert res_ok_param.status_code == 200
    assert res_ok_param.content.startswith(b"%PDF-")


@pytest.mark.asyncio
async def test_idor_checklist_and_drafts_cross_session(client: AsyncClient):
    """Verifies that Citizen B cannot read or create drafts/checklists for Citizen A."""
    sess_a = await _init_test_citizen(client)
    sess_b = await _init_test_citizen(client)

    # 1. Citizen B queries Citizen A's drafts -> 403
    drafts_res = await client.get(
        f"/api/v1/applications/drafts/{sess_a['citizen_id']}",
        headers={"X-Session-ID": sess_b["session_id"]},
    )
    assert drafts_res.status_code == 403

    # 2. Citizen B queries Citizen A's consistency report -> 403
    consist_res = await client.get(
        f"/api/v1/documents/consistency/{sess_a['citizen_id']}",
        headers={"X-Session-ID": sess_b["session_id"]},
    )
    assert consist_res.status_code == 403

    # 3. Citizen B queries Citizen A's checklist -> 403
    chk_res = await client.get(
        f"/api/v1/applications/checklist/pm-kisan?citizen_id={sess_a['citizen_id']}",
        headers={"X-Session-ID": sess_b["session_id"]},
    )
    assert chk_res.status_code == 403

    # 4. Citizen B attempts to package Citizen A's application -> 403
    pkg_cross = await client.post(
        "/api/v1/applications/package",
        json={"citizen_id": sess_a["citizen_id"], "scheme_id": "pm-kisan"},
        headers={"X-Session-ID": sess_b["session_id"]},
    )
    assert pkg_cross.status_code == 403


@pytest.mark.asyncio
async def test_zero_aadhaar_persisted_in_database(client: AsyncClient, db_session: AsyncSession):
    """Verifies that full 12-digit Aadhaar numbers are NEVER saved in SQLite columns."""
    sess = await _init_test_citizen(client)
    raw_aadhaar = "4819 1234 9999"
    raw_aadhaar_clean = "481912349999"

    # Create digital PDF containing raw 12-digit Aadhaar
    pdf_content = (
        "State Bank of India Passbook\n"
        "Account: 987654321012\n"
        "IFSC: SBIN0001234\n"
        f"Aadhaar Number: {raw_aadhaar}\n"
    )
    pdf_bytes = _create_sample_pdf([pdf_content])

    # Upload document
    res = await client.post(
        "/api/v1/documents/upload",
        data={"citizen_id": sess["citizen_id"], "document_type": "bank_passbook"},
        files={"file": ("passbook.pdf", pdf_bytes, "application/pdf")},
        headers={"X-Session-ID": sess["session_id"]},
    )
    assert res.status_code == 200
    doc_id = res.json()["id"]

    # Direct database inspection
    stmt = select(DocumentRecord).where(DocumentRecord.id == doc_id)
    result = await db_session.execute(stmt)
    doc_record = result.scalar_one_or_none()
    assert doc_record is not None

    # Verify zero persistence of raw 12-digit Aadhaar in DocumentRecord
    page_extractions_str = str(doc_record.page_extractions)
    assert raw_aadhaar not in page_extractions_str
    assert raw_aadhaar_clean not in page_extractions_str

    fields_str = str(doc_record.extracted_fields)
    assert raw_aadhaar not in fields_str
    assert raw_aadhaar_clean not in fields_str
    assert "aadhaar_number_masked" in doc_record.extracted_fields
    assert doc_record.extracted_fields["aadhaar_number_masked"] == "XXXX-XXXX-9999"

    # Confirm and verify CitizenProfile does not leak raw Aadhaar
    await client.put(
        f"/api/v1/documents/{doc_id}/confirm",
        json={"confirmed": True, "apply_to_profile": True},
        headers={"X-Session-ID": sess["session_id"]},
    )

    prof_stmt = select(CitizenProfile).where(CitizenProfile.citizen_id == sess["citizen_id"])
    prof_res = await db_session.execute(prof_stmt)
    prof_rec = prof_res.scalar_one_or_none()
    assert prof_rec is not None
    # No column in profile should contain raw Aadhaar
    assert raw_aadhaar not in str(vars(prof_rec))
    assert raw_aadhaar_clean not in str(vars(prof_rec))


@pytest.mark.asyncio
async def test_failed_ocr_unlinks_temp_file(client: AsyncClient):
    """Verifies that an OCR runtime failure immediately unlinks the temporary file from disk."""
    sess = await _init_test_citizen(client)
    img_bytes = _create_sample_image()
    initial_files = set(settings.DOCUMENTS_TEMP_DIR.glob("*"))

    with patch("app.services.ocr.mock_provider.MockOCRProvider.process_document", side_effect=RuntimeError("Simulated OCR engine failure")):
        res = await client.post(
            "/api/v1/documents/upload",
            data={"citizen_id": sess["citizen_id"], "document_type": "land_khatauni"},
            files={"file": ("fail_doc.png", img_bytes, "image/png")},
            headers={"X-Session-ID": sess["session_id"]},
        )
        assert res.status_code == 422

    # Ensure no file named fail_doc or orphaned file remains in DOCUMENTS_TEMP_DIR
    final_files = set(settings.DOCUMENTS_TEMP_DIR.glob("*"))
    assert final_files == initial_files


@pytest.mark.asyncio
async def test_mock_ocr_prominent_disclosures_in_pdf(client: AsyncClient):
    """Verifies that mock OCR results generate prominent warnings in both API response and generated PDF."""
    sess = await _init_test_citizen(client)
    headers = {"X-Session-ID": sess["session_id"]}

    # Upload mock image document
    img_bytes = _create_sample_image()
    up = await client.post(
        "/api/v1/documents/upload",
        data={"citizen_id": sess["citizen_id"], "document_type": "land_khatauni"},
        files={"file": ("demo_khatauni.png", img_bytes, "image/png")},
        headers=headers,
    )
    assert up.status_code == 200
    doc_id = up.json()["id"]

    # Confirm document
    await client.put(
        f"/api/v1/documents/{doc_id}/confirm",
        json={"confirmed": True, "apply_to_profile": True},
        headers=headers,
    )

    # Package draft
    pkg_res = await client.post(
        "/api/v1/applications/package",
        json={"citizen_id": sess["citizen_id"], "scheme_id": "pm-kisan"},
        headers=headers,
    )
    assert pkg_res.status_code == 200
    pkg_data = pkg_res.json()

    # Verify mock indicator in summary
    assert pkg_data["package_summary"]["has_mock_documents"] is True

    # Download generated PDF and inspect contents
    draft_id = pkg_data["draft_id"]
    pdf_res = await client.get(
        f"/api/v1/applications/package/{draft_id}/pdf",
        headers=headers,
    )
    assert pdf_res.status_code == 200
    pdf_reader = PdfReader(io.BytesIO(pdf_res.content))
    pdf_text = "".join(page.extract_text() or "" for page in pdf_reader.pages)

    # Verify prominent mock notice appears in the PDF text
    assert "MOCK OCR NOTICE" in pdf_text or "सिम्युलेटेड ओसीआर" in pdf_text
    assert "simulated mock OCR" in pdf_text
    assert "ATTACHED - MOCK DEMO" in pdf_text
