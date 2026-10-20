"""Scheme schemas."""
from datetime import date
from pydantic import BaseModel


class SchemeRuleDTO(BaseModel):
    id: str
    rule_code: str
    rule_type: str
    description_hi: str
    description_en: str
    source_citation: str
    failure_message_hi: str
    failure_message_en: str


class SchemeSummaryDTO(BaseModel):
    id: str
    code: str
    name_hi: str
    name_en: str
    ministry: str
    category: str
    target_group_hi: str
    target_group_en: str
    official_portal_url: str
    benefit_summary_hi: str
    benefit_summary_en: str
    max_annual_benefit_inr: float
    benefit_type: str = "DIRECT_CASH_TRANSFER"
    benefit_metric_label_hi: str = "अधिकतम वार्षिक लाभ"
    benefit_metric_label_en: str = "Max Annual Benefit"
    benefit_amount_display_hi: str = "₹6,000"
    benefit_amount_display_en: str = "₹6,000"
    jurisdiction: str
    last_verified_date: date
    verification_source: str
    verification_status: str
    is_active: bool
    rule_version: int


class SchemeDetailDTO(BaseModel):
    id: str
    code: str
    name_hi: str
    name_en: str
    ministry: str
    category: str
    target_group_hi: str
    target_group_en: str
    official_portal_url: str
    benefit_summary_hi: str
    benefit_summary_en: str
    max_annual_benefit_inr: float
    benefit_type: str = "DIRECT_CASH_TRANSFER"
    benefit_metric_label_hi: str = "अधिकतम वार्षिक लाभ"
    benefit_metric_label_en: str = "Max Annual Benefit"
    benefit_amount_display_hi: str = "₹6,000"
    benefit_amount_display_en: str = "₹6,000"
    jurisdiction: str
    application_process_hi: str
    application_process_en: str
    documents_required: list[str]
    caveats_hi: str
    caveats_en: str
    last_verified_date: date
    verification_source: str
    verification_status: str
    is_active: bool
    rule_version: int
    rules: list[SchemeRuleDTO] = []


class SchemeListResponse(BaseModel):
    total: int
    schemes: list[SchemeSummaryDTO]
