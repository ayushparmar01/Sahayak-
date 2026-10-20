"""CSC Application Packaging endpoints: checklists, draft package compilation, and PDF export."""
import os
import uuid
from typing import Any
from fastapi import APIRouter, Depends, Header, HTTPException, Query, status
from fastapi.responses import FileResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.endpoints.profile import verify_citizen_session
from app.database.session import get_db
from app.models.application import ApplicationDraft, DraftDocumentLink
from app.models.citizen import Citizen, CitizenProfile
from app.models.document import DocumentRecord
from app.schemas.application import (
    ApplicationDraftListItem,
    CSCPackageGenerateRequest,
    CSCPackageResponse,
    SchemeChecklistItem,
    SchemeChecklistResponse,
)
from app.services.ocr.checklist import get_scheme_document_checklist
from app.services.ocr.packaging import generate_csc_application_package

router = APIRouter(prefix="/applications", tags=["CSC Application Packaging"])


@router.get("/checklist/{scheme_id}", response_model=SchemeChecklistResponse)
async def get_checklist(
    scheme_id: str,
    citizen_id: str | None = Query(default=None),
    x_session_id: str | None = Header(default=None, alias="X-Session-ID"),
    db: AsyncSession = Depends(get_db),
) -> SchemeChecklistResponse:
    """Evaluates scheme-specific document requirements against a citizen's uploaded documents."""
    docs: list[dict[str, Any]] = []

    if citizen_id:
        await verify_citizen_session(citizen_id, x_session_id, db)
        docs_res = await db.execute(
            select(DocumentRecord).where(DocumentRecord.citizen_id == citizen_id)
        )
        for d in docs_res.scalars().all():
            docs.append({
                "id": d.id,
                "document_type": d.document_type,
                "citizen_confirmed": d.citizen_confirmed,
                "extracted_fields": d.extracted_fields or {},
                "is_mock": d.is_mock,
                "ocr_provider": d.ocr_provider,
            })

    try:
        raw_res = get_scheme_document_checklist(scheme_id, docs)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))

    items = [
        SchemeChecklistItem(
            document_code=c["document_code"],
            document_title_hi=c["document_title_hi"],
            document_title_en=c["document_title_en"],
            is_mandatory=c["is_mandatory"],
            status=c["status"],
            matching_document_id=c["matching_document_id"],
            statutory_citation=c["statutory_citation"],
        )
        for c in raw_res["checklist"]
    ]

    return SchemeChecklistResponse(
        scheme_id=raw_res["scheme_id"],
        scheme_name_hi=raw_res["scheme_name_hi"],
        scheme_name_en=raw_res["scheme_name_en"],
        total_required=raw_res["total_required"],
        total_present=raw_res["total_present"],
        readiness_percentage=raw_res["readiness_percentage"],
        checklist=items,
        is_ready_for_packaging=raw_res["is_ready_for_packaging"],
        guideline_notes_hi=raw_res["guideline_notes_hi"],
        guideline_notes_en=raw_res["guideline_notes_en"],
    )


@router.post("/package", response_model=CSCPackageResponse)
async def generate_package(
    payload: CSCPackageGenerateRequest,
    x_session_id: str | None = Header(default=None, alias="X-Session-ID"),
    db: AsyncSession = Depends(get_db),
) -> CSCPackageResponse:
    """Generates a complete CSC Application Package Draft with ReportLab PDF."""
    citizen = await verify_citizen_session(payload.citizen_id, x_session_id, db)

    prof_res = await db.execute(
        select(CitizenProfile).where(CitizenProfile.citizen_id == payload.citizen_id)
    )
    profile = prof_res.scalar_one_or_none()

    docs_res = await db.execute(
        select(DocumentRecord).where(DocumentRecord.citizen_id == payload.citizen_id)
    )
    doc_records = docs_res.scalars().all()

    docs_list = [
        {
            "id": d.id,
            "document_type": d.document_type,
            "citizen_confirmed": d.citizen_confirmed,
            "extracted_fields": d.extracted_fields or {},
            "user_corrections": d.user_corrections or {},
            "masked_identifier": d.masked_identifier,
            "is_mock": d.is_mock,
            "ocr_provider": d.ocr_provider,
        }
        for d in doc_records
    ]

    citizen_dict = {
        "id": citizen.id,
        "preferred_language": citizen.preferred_language,
    }
    profile_dict = {}
    if profile:
        profile_dict = {
            "age": profile.age,
            "gender": profile.gender,
            "residence_type": profile.residence_type,
            "category": profile.social_category,
            "owns_agricultural_land": profile.owns_agricultural_land,
            "land_area_hectares": round((profile.land_acres or 0.0) / 2.47105, 2) if profile.land_acres else None,
            "annual_income": profile.annual_income,
        }


    draft_id = str(uuid.uuid4())
    try:
        package_data = generate_csc_application_package(
            draft_id=draft_id,
            scheme_id=payload.scheme_id,
            citizen_data=citizen_dict,
            profile_data=profile_dict,
            documents=docs_list,
            operator_notes=payload.operator_notes,
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))

    # Persist Application Draft
    draft = ApplicationDraft(
        id=draft_id,
        citizen_id=payload.citizen_id,
        scheme_id=payload.scheme_id,
        status="DRAFT_READY",
        completeness_percentage=package_data["completeness_percentage"],
        package_summary=package_data["package_summary"],
        checklist_status=package_data["checklist_status"],
        cross_document_checks=package_data["cross_document_checks"],
        pdf_export_path=package_data["pdf_path"],
        disclaimer_ack=payload.disclaimer_acknowledged,
    )
    db.add(draft)

    # Attach document links
    for d in doc_records:
        link = DraftDocumentLink(
            id=str(uuid.uuid4()),
            application_draft_id=draft.id,
            document_record_id=d.id,
        )
        db.add(link)

    await db.commit()
    await db.refresh(draft)

    disclaimer_text = (
        "महत्वपूर्ण अस्वीकरण (Disclaimer): यह दस्तावेज़ केवल नागरिक सुविधा और कॉमन सर्विस सेंटर (CSC) "
        "पर आवेदन भरने हेतु सहायता प्रारूप (Preparation Aid) है। यह कोई आधिकारिक सरकारी स्वीकृति, "
        "पंजीकरण रसीद या लाभ गारंटी नहीं है।"
    )

    return CSCPackageResponse(
        draft_id=draft.id,
        citizen_id=draft.citizen_id,
        scheme_id=draft.scheme_id,
        scheme_name_hi=package_data["package_summary"].get("scheme_name_hi", ""),
        scheme_name_en=package_data["package_summary"].get("scheme_name_en", ""),
        status=draft.status,
        completeness_percentage=draft.completeness_percentage,
        pdf_download_url=f"/api/v1/applications/package/{draft.id}/pdf",
        package_summary=draft.package_summary,
        cross_document_checks=draft.cross_document_checks,
        checklist_status=draft.checklist_status,
        disclaimer=disclaimer_text,
        created_at=draft.created_at,
    )


@router.get("/package/{draft_id}/pdf")
async def download_package_pdf(
    draft_id: str,
    x_session_id: str | None = Header(default=None, alias="X-Session-ID"),
    session_id: str | None = Query(default=None, alias="session_id"),
    db: AsyncSession = Depends(get_db),
):
    """Streams the generated CSC Application Preparation Aid PDF for printing/download."""
    result = await db.execute(select(ApplicationDraft).where(ApplicationDraft.id == draft_id))
    draft = result.scalar_one_or_none()
    if not draft:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="ड्राफ्ट नहीं मिला (Draft not found)")

    effective_session_id = x_session_id or session_id
    await verify_citizen_session(draft.citizen_id, effective_session_id, db)


    pdf_path = draft.pdf_export_path
    if not pdf_path or not os.path.exists(pdf_path):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="पीडीएफ फ़ाइल उपलब्ध नहीं है (PDF file not found)",
        )

    return FileResponse(
        path=pdf_path,
        filename=f"csc_preparation_aid_{draft.scheme_id}_{draft_id[:8]}.pdf",
        media_type="application/pdf",
    )


@router.get("/drafts/{citizen_id}", response_model=list[ApplicationDraftListItem])
async def list_citizen_drafts(
    citizen_id: str,
    x_session_id: str | None = Header(default=None, alias="X-Session-ID"),
    db: AsyncSession = Depends(get_db),
) -> list[ApplicationDraftListItem]:
    """Lists all prepared application drafts for a citizen."""
    await verify_citizen_session(citizen_id, x_session_id, db)

    result = await db.execute(
        select(ApplicationDraft)
        .where(ApplicationDraft.citizen_id == citizen_id)
        .order_by(ApplicationDraft.created_at.desc())
    )
    drafts = result.scalars().all()

    items = []
    for d in drafts:
        summary = d.package_summary or {}
        items.append(
            ApplicationDraftListItem(
                id=d.id,
                citizen_id=d.citizen_id,
                scheme_id=d.scheme_id,
                scheme_name_hi=summary.get("scheme_name_hi", d.scheme_id),
                scheme_name_en=summary.get("scheme_name_en", d.scheme_id),
                status=d.status,
                completeness_percentage=d.completeness_percentage or 0.0,
                has_pdf=bool(d.pdf_export_path and os.path.exists(d.pdf_export_path)),
                created_at=d.created_at,
                updated_at=d.updated_at,
            )
        )
    return items
