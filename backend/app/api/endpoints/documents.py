"""Document Intelligence endpoints: upload, OCR extraction, human review, and consistency audit."""
import io
import os
import uuid
from pathlib import Path
from typing import Any
from fastapi import APIRouter, Depends, File, Form, Header, HTTPException, UploadFile, status
from PIL import Image
import PyPDF2
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.endpoints.profile import verify_citizen_session
from app.core.config import settings
from app.database.session import get_db
from app.models.citizen import Citizen, CitizenProfile
from app.models.document import DocumentRecord
from app.schemas.document import (
    ConsistencyCheckItem,
    ConsistencyReportResponse,
    DocumentConfirmRequest,
    DocumentConfirmResponse,
    DocumentDetailDTO,
    DocumentUploadResponse,
)
from app.services.ocr import get_ocr_provider
from app.services.ocr.consistency import run_cross_document_consistency_checks

router = APIRouter(prefix="/documents", tags=["Document Intelligence"])


def _detect_magic_bytes(content: bytes) -> tuple[str, str]:
    """Inspects raw file bytes to safely detect MIME type and safe extension.
    
    Prevents file extension masquerading and executable uploads.
    """
    if content.startswith(b"%PDF-"):
        return ("application/pdf", ".pdf")
    elif content.startswith(b"\x89PNG\r\n\x1a\n"):
        return ("image/png", ".png")
    elif content.startswith(b"\xff\xd8\xff"):
        return ("image/jpeg", ".jpg")
    raise HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail="अमान्य फ़ाइल प्रकार: केवल वैध PDF, PNG, और JPEG दस्तावेज़ समर्थित हैं (Invalid file format: Only genuine PDF, PNG, and JPEG files are supported)",
    )


@router.post("/upload", response_model=DocumentUploadResponse)
async def upload_document(
    file: UploadFile = File(...),
    citizen_id: str = Form(...),
    document_type: str | None = Form(None),
    x_session_id: str | None = Header(default=None, alias="X-Session-ID"),
    db: AsyncSession = Depends(get_db),
) -> DocumentUploadResponse:
    """Uploads a citizen document, executes OCR, and returns unconfirmed draft extractions."""
    # 1. Verify citizen ownership
    await verify_citizen_session(citizen_id, x_session_id, db)

    # 2. Read content and validate size limit (10MB)
    content = await file.read()
    file_size = len(content)
    if file_size > settings.MAX_DOCUMENT_FILE_SIZE_BYTES:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"फ़ाइल का आकार सीमा (10 MB) से अधिक है: {file_size / (1024*1024):.1f} MB (File exceeds 10MB limit)",
        )

    if file_size == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="खाली फ़ाइल अपलोड नहीं की जा सकती (Empty file cannot be uploaded)",
        )

    # 3. Detect genuine MIME type via magic bytes
    mime_type, safe_ext = _detect_magic_bytes(content)

    # 4. Decompression bomb and page count security checks
    page_count = 1
    if mime_type == "application/pdf":
        try:
            reader = PyPDF2.PdfReader(io.BytesIO(content))
            page_count = len(reader.pages)
            if page_count > settings.MAX_DOCUMENT_PAGE_COUNT:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"पीडीएफ में पृष्ठ सीमा ({settings.MAX_DOCUMENT_PAGE_COUNT}) से अधिक पृष्ठ हैं: {page_count} (PDF exceeds max 10 pages)",
                )
        except Exception as e:
            if isinstance(e, HTTPException):
                raise
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"दूषित अथवा अवैध पीडीएफ फ़ाइल (Corrupt or invalid PDF): {str(e)}",
            )
    elif mime_type in ("image/png", "image/jpeg"):
        try:
            with Image.open(io.BytesIO(content)) as img:
                width, height = img.size
                if width > settings.MAX_IMAGE_DIMENSION or height > settings.MAX_IMAGE_DIMENSION:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=f"छवि का आकार अधिकतम सीमा ({settings.MAX_IMAGE_DIMENSION}px) से अधिक है: {width}x{height} (Image dimensions too large)",
                    )
        except Exception as e:
            if isinstance(e, HTTPException):
                raise
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"दूषित अथवा अवैध छवि फ़ाइल (Corrupt image file): {str(e)}",
            )

    # 5. Persist securely using UUID filename (never user-supplied filename)
    settings.DOCUMENTS_TEMP_DIR.mkdir(parents=True, exist_ok=True)
    safe_filename = f"{uuid.uuid4().hex}{safe_ext}"
    saved_path = settings.DOCUMENTS_TEMP_DIR / safe_filename
    with open(saved_path, "wb") as f:
        f.write(content)

    # 6. Execute OCR Processor
    try:
        ocr_provider = get_ocr_provider(mime_type=mime_type)
        ocr_res = await ocr_provider.process_document(
            file_path=saved_path,
            mime_type=mime_type,
            hint_document_type=document_type,
        )

        # 7. Persist Document Record (gated: review_status=UNREVIEWED, citizen_confirmed=False)
        doc_record = DocumentRecord(
            id=str(uuid.uuid4()),
            citizen_id=citizen_id,
            document_type=ocr_res.document_type,
            file_name=Path(file.filename or "uploaded_doc").name,
            mime_type=mime_type,
            file_size_bytes=file_size,
            page_count=len(ocr_res.pages) if ocr_res.pages else 1,
            ocr_provider=ocr_res.provider_name,
            is_mock=ocr_res.is_mock,
            ocr_status="COMPLETED",
            review_status="UNREVIEWED",
            citizen_confirmed=False,
            masked_identifier=ocr_res.masked_identifier,
            extracted_fields=ocr_res.extracted_fields,
            ocr_confidence=ocr_res.overall_confidence,
            page_extractions=[
                {"page_number": p.page_number, "raw_text": p.raw_text, "fields": p.fields}
                for p in ocr_res.pages
            ],
            user_corrections={},
            storage_path=str(saved_path),
        )
        db.add(doc_record)
        await db.commit()
        await db.refresh(doc_record)
    except Exception as e:
        if saved_path.exists():
            try:
                saved_path.unlink()
            except OSError:
                pass
        if isinstance(e, HTTPException):
            raise
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"दस्तावेज़ ओसीआर प्रसंस्करण विफल (Document OCR processing failed): {str(e)}",
        )


    return DocumentUploadResponse(
        id=doc_record.id,
        citizen_id=doc_record.citizen_id,
        document_type=doc_record.document_type,
        file_name=doc_record.file_name,
        mime_type=doc_record.mime_type,
        file_size_bytes=doc_record.file_size_bytes,
        page_count=doc_record.page_count,
        ocr_provider=doc_record.ocr_provider,
        is_mock=doc_record.is_mock,
        ocr_status=doc_record.ocr_status,
        review_status=doc_record.review_status,
        citizen_confirmed=doc_record.citizen_confirmed,
        masked_identifier=doc_record.masked_identifier,
        extracted_fields=doc_record.extracted_fields,
        ocr_confidence=doc_record.ocr_confidence,
        page_extractions=doc_record.page_extractions,
        uploaded_at=doc_record.uploaded_at,
    )


@router.get("", response_model=list[DocumentDetailDTO])
async def list_documents(
    citizen_id: str,
    x_session_id: str | None = Header(default=None, alias="X-Session-ID"),
    db: AsyncSession = Depends(get_db),
) -> list[DocumentDetailDTO]:
    """Lists all uploaded documents for a citizen."""
    await verify_citizen_session(citizen_id, x_session_id, db)

    result = await db.execute(
        select(DocumentRecord).where(DocumentRecord.citizen_id == citizen_id).order_by(DocumentRecord.uploaded_at.desc())
    )
    docs = result.scalars().all()

    return [
        DocumentDetailDTO(
            id=d.id,
            citizen_id=d.citizen_id,
            document_type=d.document_type,
            file_name=d.file_name,
            mime_type=d.mime_type,
            file_size_bytes=d.file_size_bytes,
            page_count=d.page_count or 1,
            ocr_provider=d.ocr_provider or "mock",
            is_mock=bool(d.is_mock),
            ocr_status=d.ocr_status or "COMPLETED",
            review_status=d.review_status or "UNREVIEWED",
            citizen_confirmed=bool(d.citizen_confirmed),
            masked_identifier=d.masked_identifier,
            extracted_fields=d.extracted_fields or {},
            ocr_confidence=d.ocr_confidence or 0.0,
            page_extractions=d.page_extractions or [],
            user_corrections=d.user_corrections or {},
            uploaded_at=d.uploaded_at,
        )
        for d in docs
    ]


@router.get("/{document_id}", response_model=DocumentDetailDTO)
async def get_document(
    document_id: str,
    x_session_id: str | None = Header(default=None, alias="X-Session-ID"),
    db: AsyncSession = Depends(get_db),
) -> DocumentDetailDTO:
    """Fetches details for a specific document with multi-page extractions."""
    result = await db.execute(select(DocumentRecord).where(DocumentRecord.id == document_id))
    doc = result.scalar_one_or_none()
    if not doc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="दस्तावेज़ नहीं मिला (Document not found)")

    await verify_citizen_session(doc.citizen_id, x_session_id, db)

    return DocumentDetailDTO(
        id=doc.id,
        citizen_id=doc.citizen_id,
        document_type=doc.document_type,
        file_name=doc.file_name,
        mime_type=doc.mime_type,
        file_size_bytes=doc.file_size_bytes,
        page_count=doc.page_count or 1,
        ocr_provider=doc.ocr_provider or "mock",
        is_mock=bool(doc.is_mock),
        ocr_status=doc.ocr_status or "COMPLETED",
        review_status=doc.review_status or "UNREVIEWED",
        citizen_confirmed=bool(doc.citizen_confirmed),
        masked_identifier=doc.masked_identifier,
        extracted_fields=doc.extracted_fields or {},
        ocr_confidence=doc.ocr_confidence or 0.0,
        page_extractions=doc.page_extractions or [],
        user_corrections=doc.user_corrections or {},
        uploaded_at=doc.uploaded_at,
    )


@router.put("/{document_id}/confirm", response_model=DocumentConfirmResponse)
async def confirm_document(
    document_id: str,
    payload: DocumentConfirmRequest,
    x_session_id: str | None = Header(default=None, alias="X-Session-ID"),
    db: AsyncSession = Depends(get_db),
) -> DocumentConfirmResponse:
    """Citizen confirms or corrects OCR extractions, with optional profile synchronization."""
    result = await db.execute(select(DocumentRecord).where(DocumentRecord.id == document_id))
    doc = result.scalar_one_or_none()
    if not doc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="दस्तावेज़ नहीं मिला (Document not found)")

    await verify_citizen_session(doc.citizen_id, x_session_id, db)

    # 1. Update review status
    doc.citizen_confirmed = payload.confirmed
    doc.review_status = "CONFIRMED" if payload.confirmed else "REJECTED"
    if payload.corrections:
        doc.user_corrections = {**(doc.user_corrections or {}), **payload.corrections}

    # Merged active fields
    final_fields = {**(doc.extracted_fields or {}), **(doc.user_corrections or {})}

    # 2. Gated profile sync (only if explicitly requested and confirmed)
    profile_updated = False
    updated_fields: list[str] = []

    if payload.apply_to_profile and payload.confirmed:
        prof_res = await db.execute(select(CitizenProfile).where(CitizenProfile.citizen_id == doc.citizen_id))
        profile = prof_res.scalar_one_or_none()

        if profile:
            # Sync Land Record
            if doc.document_type == "land_khatauni":
                area = final_fields.get("land_area_hectares")
                if area is not None:
                    profile.owns_agricultural_land = True
                    profile.land_acres = float(area) * 2.47105  # Convert Ha to Acres
                    updated_fields.extend(["owns_agricultural_land", "land_acres"])


            # Sync Income
            if doc.document_type == "income_certificate":
                inc = final_fields.get("annual_income")
                if inc is not None:
                    profile.annual_income = float(inc)
                    updated_fields.append("annual_income")

            # Sync Ration Card
            if doc.document_type == "ration_card":
                profile.residence_type = profile.residence_type or "RURAL"
                updated_fields.append("residence_type")

            # Sync Identity / Gender
            if doc.document_type == "aadhaar_card_masked":
                g = final_fields.get("gender")
                if g and g.upper() in ("MALE", "FEMALE", "TRANSGENDER", "OTHER"):
                    profile.gender = g.upper()
                    updated_fields.append("gender")

            if updated_fields:
                profile_updated = True

    await db.commit()

    return DocumentConfirmResponse(
        document_id=doc.id,
        review_status=doc.review_status,
        citizen_confirmed=doc.citizen_confirmed,
        final_fields=final_fields,
        profile_updated=profile_updated,
        updated_profile_fields=updated_fields,
        message="दस्तावेज़ सत्यापन सफलतापूर्वक सहेजा गया (Document confirmation saved)",
    )


@router.delete("/{document_id}")
async def delete_document(
    document_id: str,
    x_session_id: str | None = Header(default=None, alias="X-Session-ID"),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Deletes a document record and removes the physical file from disk."""
    result = await db.execute(select(DocumentRecord).where(DocumentRecord.id == document_id))
    doc = result.scalar_one_or_none()
    if not doc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="दस्तावेज़ नहीं मिला (Document not found)")

    await verify_citizen_session(doc.citizen_id, x_session_id, db)

    # Remove physical file
    if doc.storage_path and os.path.exists(doc.storage_path):
        try:
            os.remove(doc.storage_path)
        except OSError:
            pass

    await db.delete(doc)
    await db.commit()

    return {"message": "दस्तावेज़ सफलतापूर्वक हटाया गया (Document deleted successfully)", "document_id": document_id}


@router.get("/consistency/{citizen_id}", response_model=ConsistencyReportResponse)
async def check_document_consistency(
    citizen_id: str,
    x_session_id: str | None = Header(default=None, alias="X-Session-ID"),
    db: AsyncSession = Depends(get_db),
) -> ConsistencyReportResponse:
    """Runs cross-document and profile consistency audit for a citizen."""
    await verify_citizen_session(citizen_id, x_session_id, db)

    docs_res = await db.execute(
        select(DocumentRecord).where(DocumentRecord.citizen_id == citizen_id)
    )
    docs = docs_res.scalars().all()

    prof_res = await db.execute(
        select(CitizenProfile).where(CitizenProfile.citizen_id == citizen_id)
    )
    prof = prof_res.scalar_one_or_none()

    doc_dicts = [
        {
            "id": d.id,
            "document_type": d.document_type,
            "extracted_fields": d.extracted_fields or {},
            "user_corrections": d.user_corrections or {},
            "citizen_confirmed": d.citizen_confirmed,
        }
        for d in docs
    ]

    prof_dict = {}
    if prof:
        prof_dict = {
            "owns_agricultural_land": prof.owns_agricultural_land,
            "annual_income": prof.annual_income,
            "gender": prof.gender,
            "residence_type": prof.residence_type,
        }

    raw_checks = run_cross_document_consistency_checks(doc_dicts, prof_dict)
    has_vars = any(c.get("status") in ("VARIATION", "REVIEW_RECOMMENDED") for c in raw_checks)

    summary_hi = (
        "दस्तावेज़ों में भिन्नताएँ पाई गईं। कृपया सीएससी ऑपरेटर द्वारा समीक्षा करवाएं।"
        if has_vars else "सभी संलग्न दस्तावेज़ परस्पर सुसंगत हैं।"
    )
    summary_en = (
        "Variations detected across documents. CSC operator review recommended."
        if has_vars else "All attached documents are mutually consistent."
    )

    items = [
        ConsistencyCheckItem(
            check_id=c["check_id"],
            field_name=c["field_name"],
            document_type=c["document_type"],
            document_value=c["document_value"],
            profile_value=c["profile_value"],
            status=c["status"],
            message_hi=c["message_hi"],
            message_en=c["message_en"],
        )
        for c in raw_checks
    ]

    return ConsistencyReportResponse(
        citizen_id=citizen_id,
        total_documents=len(docs),
        checks=items,
        has_variations=has_vars,
        summary_hi=summary_hi,
        summary_en=summary_en,
    )
