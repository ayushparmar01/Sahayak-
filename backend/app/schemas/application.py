"""Pydantic schemas for CSC Application Packaging and Checklists."""
from datetime import datetime
from typing import Any
from pydantic import BaseModel, Field


class SchemeChecklistItem(BaseModel):
    document_code: str
    document_title_hi: str
    document_title_en: str
    is_mandatory: bool = True
    status: str  # PRESENT, MISSING, PENDING_CONFIRMATION
    matching_document_id: str | None = None
    statutory_citation: str


class SchemeChecklistResponse(BaseModel):
    scheme_id: str
    scheme_name_hi: str
    scheme_name_en: str
    total_required: int
    total_present: int
    readiness_percentage: float
    checklist: list[SchemeChecklistItem] = Field(default_factory=list)
    is_ready_for_packaging: bool
    guideline_notes_hi: str
    guideline_notes_en: str


class CSCPackageGenerateRequest(BaseModel):
    citizen_id: str
    scheme_id: str
    operator_notes: str | None = None
    disclaimer_acknowledged: bool = True


class CSCPackageResponse(BaseModel):
    draft_id: str
    citizen_id: str
    scheme_id: str
    scheme_name_hi: str
    scheme_name_en: str
    status: str
    completeness_percentage: float
    pdf_download_url: str
    package_summary: dict[str, Any] = Field(default_factory=dict)
    cross_document_checks: list[dict[str, Any]] = Field(default_factory=list)
    checklist_status: dict[str, Any] = Field(default_factory=dict)
    disclaimer: str
    created_at: datetime
    message: str = "सीएससी आवेदन ड्राफ्ट पैकेज तैयार किया गया (CSC Application Package Draft generated)"


class ApplicationDraftListItem(BaseModel):
    id: str
    citizen_id: str
    scheme_id: str
    scheme_name_hi: str
    scheme_name_en: str
    status: str
    completeness_percentage: float
    has_pdf: bool
    created_at: datetime
    updated_at: datetime
