"""Eligibility assessment schemas for SAHAYAK Deterministic Rules Engine."""
from datetime import datetime
from enum import Enum
from pydantic import BaseModel, Field


class AssessmentStatus(str, Enum):
    ELIGIBLE = "ELIGIBLE"
    POTENTIALLY_ELIGIBLE = "POTENTIALLY_ELIGIBLE"
    INELIGIBLE = "INELIGIBLE"
    NEEDS_MORE_INFO = "NEEDS_MORE_INFO"


class ConditionOutcome(str, Enum):
    PASS = "PASS"
    FAIL = "FAIL"
    UNKNOWN = "UNKNOWN"
    NOT_APPLICABLE = "NOT_APPLICABLE"
    PENDING_VERIFICATION = "PENDING_VERIFICATION"


class ConditionEvaluation(BaseModel):
    id: str
    title_hi: str
    title_en: str
    outcome: ConditionOutcome
    outcome_detail_hi: str
    outcome_detail_en: str
    source_citation: str


class MissingFieldRequirement(BaseModel):
    field_name: str
    label_hi: str
    label_en: str
    reason_hi: str
    reason_en: str


class BenefitAssessmentSummary(BaseModel):
    amount_inr: float
    benefit_type: str = "DIRECT_CASH_TRANSFER"
    benefit_metric_label_hi: str = "अधिकतम वार्षिक लाभ"
    benefit_metric_label_en: str = "Max Annual Benefit"
    benefit_amount_display_hi: str = "₹6,000"
    benefit_amount_display_en: str = "₹6,000"
    description_hi: str
    description_en: str
    caveats_hi: str
    caveats_en: str


class OfficialSourceReference(BaseModel):
    title: str
    url: str
    section: str | None = None


class EligibilityAssessRequest(BaseModel):
    scheme_id: str
    profile_override: dict | None = None


class EligibilityAssessResponse(BaseModel):
    scheme_id: str
    scheme_name_hi: str
    scheme_name_en: str
    rule_version: int
    evaluated_at: datetime
    status: AssessmentStatus
    status_label_hi: str
    status_label_en: str
    summary_explanation_hi: str
    summary_explanation_en: str
    conditions_satisfied: list[ConditionEvaluation]
    conditions_failed: list[ConditionEvaluation]
    missing_information: list[MissingFieldRequirement]
    applicable_exclusions: list[ConditionEvaluation]
    pending_verifications: list[ConditionEvaluation]
    benefit_summary: BenefitAssessmentSummary
    required_documents: list[str]
    official_sources: list[OfficialSourceReference]
    next_recommended_action_hi: str
    next_recommended_action_en: str
    disclaimer_hi: str = (
        "सार्वजनिक सेवा सूचना: यह एक प्रारंभिक और सूचनात्मक आकलन है, कोई अंतिम सरकारी स्वीकृति नहीं। "
        "योजना का अंतिम लाभ संबंधित विभाग/बैंक द्वारा भौतिक दस्तावेज़ सत्यापन के बाद ही मान्य होता है।"
    )
    disclaimer_en: str = (
        "Public Service Notice: This is an informational preliminary assessment, not an official government approval. "
        "Final scheme benefits are subject to physical document verification and sanction by the competent authority/bank."
    )
