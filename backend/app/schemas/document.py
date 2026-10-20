"""Pydantic schemas for Document Intelligence and Multi-Page OCR."""
from datetime import datetime
from typing import Any
from pydantic import BaseModel, Field


class FieldExtractionDTO(BaseModel):
    field_name: str
    value: Any
    confidence: float = 1.0
    source_page: int = 1
    is_masked: bool = False
    bbox: list[float] | None = None


class PageExtractionDTO(BaseModel):
    page_number: int
    raw_text: str
    fields: dict[str, Any] = Field(default_factory=dict)


class DocumentUploadResponse(BaseModel):
    id: str
    citizen_id: str
    document_type: str
    file_name: str | None = None
    mime_type: str | None = None
    file_size_bytes: int | None = None
    page_count: int = 1
    ocr_provider: str
    is_mock: bool
    ocr_status: str
    review_status: str
    citizen_confirmed: bool
    masked_identifier: str | None = None
    extracted_fields: dict[str, Any] = Field(default_factory=dict)
    ocr_confidence: float = 0.0
    page_extractions: list[dict[str, Any]] = Field(default_factory=list)
    uploaded_at: datetime
    message: str = "दस्तावेज़ सफलतापूर्वक अपलोड और संसाधित हुआ (Document uploaded and processed)"


class DocumentDetailDTO(BaseModel):
    id: str
    citizen_id: str
    document_type: str
    file_name: str | None = None
    mime_type: str | None = None
    file_size_bytes: int | None = None
    page_count: int = 1
    ocr_provider: str
    is_mock: bool
    ocr_status: str
    review_status: str
    citizen_confirmed: bool
    masked_identifier: str | None = None
    extracted_fields: dict[str, Any] = Field(default_factory=dict)
    ocr_confidence: float = 0.0
    page_extractions: list[dict[str, Any]] = Field(default_factory=list)
    user_corrections: dict[str, Any] = Field(default_factory=dict)
    uploaded_at: datetime


class DocumentConfirmRequest(BaseModel):
    confirmed: bool = True
    corrections: dict[str, Any] = Field(default_factory=dict)
    apply_to_profile: bool = False


class DocumentConfirmResponse(BaseModel):
    document_id: str
    review_status: str
    citizen_confirmed: bool
    final_fields: dict[str, Any]
    profile_updated: bool
    updated_profile_fields: list[str] = Field(default_factory=list)
    message: str


class ConsistencyCheckItem(BaseModel):
    check_id: str
    field_name: str
    document_type: str
    document_value: Any
    profile_value: Any
    status: str  # MATCH, VARIATION, REVIEW_RECOMMENDED
    message_hi: str
    message_en: str


class ConsistencyReportResponse(BaseModel):
    citizen_id: str
    total_documents: int
    checks: list[ConsistencyCheckItem] = Field(default_factory=list)
    has_variations: bool = False
    summary_hi: str
    summary_en: str
