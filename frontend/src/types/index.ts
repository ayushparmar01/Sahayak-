export type Language = 'hi' | 'en';

export interface HealthStatus {
  status: string;
  app_name: string;
  version: string;
  environment: string;
  database_connected: boolean;
  timestamp: string;
}

export interface SessionState {
  sessionId: string | null;
  citizenId: string | null;
  preferredLanguage: Language;
  consentGrantedAt: string | null;
  isActive: boolean;
  isLoading: boolean;
  error: string | null;
}

export interface CitizenProfile {
  age?: number | null;
  state?: string | null;
  district?: string | null;
  landAcres?: number | null;
  landType?: string | null;
  annualIncome?: number | null;
  rationCardType?: string | null;
  occupation?: string | null;
  socialCategory?: string | null;
  gender?: string | null;
  isIncomeTaxPayer?: boolean | null;
  hasPuccaHouse?: boolean | null;
  ownsAgriculturalLand?: boolean | null;
  hasGirlChildUnder10?: boolean | null;
  hasExistingLpg?: boolean | null;
  enrolledInCropInsurance?: boolean | null;
  residenceType?: 'RURAL' | 'URBAN' | string | null;
  bisVerified?: boolean | null;
  awaasPlusVerified?: boolean | null;
  isConfirmed: boolean;
  updatedAt?: string | null;
}

export interface SchemeRule {
  id: string;
  rule_code: string;
  rule_type: 'MANDATORY_CRITERION' | 'EXCLUSION' | 'DOCUMENT_REQ' | 'EXTERNAL_VERIFICATION';
  description_hi: string;
  description_en: string;
  source_citation: string;
  failure_message_hi: string;
  failure_message_en: string;
}

export interface Scheme {
  id: string;
  code: string;
  name_hi: string;
  name_en: string;
  ministry: string;
  category: string;
  target_group_hi: string;
  target_group_en: string;
  official_portal_url: string;
  benefit_summary_hi: string;
  benefit_summary_en: string;
  max_annual_benefit_inr: number;
  benefit_type?: string;
  benefit_metric_label_hi?: string;
  benefit_metric_label_en?: string;
  benefit_amount_display_hi?: string;
  benefit_amount_display_en?: string;
  jurisdiction: string;
  last_verified_date: string;
  verification_source: string;
  verification_status: 'VERIFIED' | 'REVISION_PENDING' | 'OUTDATED' | 'UNKNOWN';
  is_active: boolean;
  rule_version: number;
}

export interface SchemeDetail extends Scheme {
  application_process_hi: string;
  application_process_en: string;
  documents_required: string[];
  caveats_hi: string;
  caveats_en: string;
  rules: SchemeRule[];
}

export type AssessmentStatus = 'ELIGIBLE' | 'POTENTIALLY_ELIGIBLE' | 'INELIGIBLE' | 'NEEDS_MORE_INFO';
export type ConditionOutcome = 'PASS' | 'FAIL' | 'UNKNOWN' | 'NOT_APPLICABLE' | 'PENDING_VERIFICATION';

export interface ConditionEvaluation {
  id: string;
  title_hi: string;
  title_en: string;
  outcome: ConditionOutcome;
  outcome_detail_hi: string;
  outcome_detail_en: string;
  source_citation: string;
}

export interface MissingFieldRequirement {
  field_name: string;
  label_hi: string;
  label_en: string;
  reason_hi: string;
  reason_en: string;
}

export interface BenefitAssessmentSummary {
  amount_inr: number;
  benefit_type?: string;
  benefit_metric_label_hi?: string;
  benefit_metric_label_en?: string;
  benefit_amount_display_hi?: string;
  benefit_amount_display_en?: string;
  description_hi: string;
  description_en: string;
  caveats_hi: string;
  caveats_en: string;
}

export interface OfficialSourceReference {
  title: string;
  url: string;
  section?: string | null;
}

export interface EligibilityAssessment {
  scheme_id: string;
  scheme_name_hi: string;
  scheme_name_en: string;
  rule_version: number;
  evaluated_at: string;
  status: AssessmentStatus;
  status_label_hi: string;
  status_label_en: string;
  summary_explanation_hi: string;
  summary_explanation_en: string;
  conditions_satisfied: ConditionEvaluation[];
  conditions_failed: ConditionEvaluation[];
  missing_information: MissingFieldRequirement[];
  applicable_exclusions: ConditionEvaluation[];
  pending_verifications: ConditionEvaluation[];
  benefit_summary: BenefitAssessmentSummary;
  required_documents: string[];
  official_sources: OfficialSourceReference[];
  next_recommended_action_hi: string;
  next_recommended_action_en: string;
  disclaimer_hi: string;
  disclaimer_en: string;
}

export interface VoiceTurnResponse {
  session_id: string;
  citizen_id: string;
  turn_count: number;
  status: 'ready' | 'awaiting_consent' | 'needs_confirmation' | 'needs_follow_up' | 'completed' | 'error';
  transcript?: string | null;
  transcript_confidence: number;
  intent?: string | null;
  proposed_profile_updates: Record<string, any>;
  persisted_profile_updates: Record<string, any>;
  is_profile_confirmed: boolean;
  follow_up_field?: string | null;
  follow_up_question_hi?: string | null;
  follow_up_question_en?: string | null;
  evaluated_schemes: EligibilityAssessment[];
  response_text_hi: string;
  response_text_en: string;
  audio_base64?: string | null;
  audio_format?: string;
  browser_tts_recommended: boolean;
  provider_info: Record<string, string>;
  error_message?: string | null;
}

export interface VoiceTranscribeResponse {
  transcript: string;
  confidence: number;
  language: string;
  is_mock: boolean;
  duration_seconds: number;
}

export interface VoiceProvidersInfo {
  stt_provider: string;
  tts_provider: string;
  llm_provider: string;
  is_mock: boolean;
  supported_languages: string[];
  audio_limits: {
    max_file_size_bytes: number;
    max_duration_seconds: number;
    max_conversation_turns: number;
    supported_mime_types: string[];
  };
}

// Phase 4: Document Intelligence & CSC Packaging Types
export interface PageExtraction {
  page_number: number;
  raw_text: string;
  fields: Record<string, any>;
}

export interface DocumentRecordDTO {
  id: string;
  citizen_id: string;
  document_type: string;
  file_name?: string | null;
  mime_type?: string | null;
  file_size_bytes?: number | null;
  page_count: number;
  ocr_provider: string;
  is_mock: boolean;
  ocr_status: string;
  review_status: 'UNREVIEWED' | 'CONFIRMED' | 'REJECTED' | string;
  citizen_confirmed: boolean;
  masked_identifier?: string | null;
  extracted_fields: Record<string, any>;
  ocr_confidence: number;
  page_extractions: PageExtraction[];
  user_corrections?: Record<string, any>;
  uploaded_at: string;
}

export interface ConsistencyCheckItem {
  check_id: string;
  field_name: string;
  document_type: string;
  document_value: any;
  profile_value: any;
  status: 'MATCH' | 'VARIATION' | 'REVIEW_RECOMMENDED';
  message_hi: string;
  message_en: string;
}

export interface ConsistencyReport {
  citizen_id: string;
  total_documents: number;
  checks: ConsistencyCheckItem[];
  has_variations: boolean;
  summary_hi: string;
  summary_en: string;
}

export interface SchemeChecklistItem {
  document_code: string;
  document_title_hi: string;
  document_title_en: string;
  is_mandatory: boolean;
  status: 'PRESENT' | 'MISSING' | 'PENDING_CONFIRMATION';
  matching_document_id?: string | null;
  statutory_citation: string;
}

export interface SchemeChecklistResponse {
  scheme_id: string;
  scheme_name_hi: string;
  scheme_name_en: string;
  total_required: number;
  total_present: number;
  readiness_percentage: number;
  checklist: SchemeChecklistItem[];
  is_ready_for_packaging: boolean;
  guideline_notes_hi: string;
  guideline_notes_en: string;
}

export interface CSCPackageResponse {
  draft_id: string;
  citizen_id: string;
  scheme_id: string;
  scheme_name_hi: string;
  scheme_name_en: string;
  status: string;
  completeness_percentage: number;
  pdf_download_url: string;
  package_summary: Record<string, any>;
  cross_document_checks: any[];
  checklist_status: any;
  disclaimer: string;
  created_at: string;
  message?: string;
}

export interface ApplicationDraftListItem {
  id: string;
  citizen_id: string;
  scheme_id: string;
  scheme_name_hi: string;
  scheme_name_en: string;
  status: string;
  completeness_percentage: number;
  has_pdf: boolean;
  created_at: string;
  updated_at: string;
}


