import type {
  HealthStatus,
  Scheme,
  SchemeDetail,
  CitizenProfile,
  EligibilityAssessment,
  VoiceTurnResponse,
  VoiceTranscribeResponse,
  VoiceProvidersInfo,
} from '../types/index.ts';


const API_BASE = '/api/v1';

export async function fetchHealth(): Promise<HealthStatus> {
  const res = await fetch(`${API_BASE}/health`);
  if (!res.ok) {
    throw new Error(`Health check failed with status: ${res.status}`);
  }
  return res.json();
}

export async function initSession(
  preferredLanguage: string = 'hi',
  consentGiven: boolean = false
): Promise<{
  session_id: string;
  citizen_id: string;
  preferred_language: string;
  consent_granted_at: string | null;
  status: string;
  message: string;
}> {
  const res = await fetch(`${API_BASE}/sessions/init`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      preferred_language: preferredLanguage,
      consent_given: consentGiven,
    }),
  });
  if (!res.ok) {
    throw new Error(`Failed to initialize session: ${res.statusText}`);
  }
  return res.json();
}

export async function terminateSession(sessionId: string): Promise<{
  session_id: string;
  status: string;
  message: string;
  data_purged: boolean;
}> {
  const res = await fetch(`${API_BASE}/sessions/terminate`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ session_id: sessionId }),
  });
  if (!res.ok) {
    throw new Error(`Failed to terminate session: ${res.statusText}`);
  }
  return res.json();
}

export async function fetchSchemes(filters?: {
  category?: string;
  jurisdiction?: string;
  verification_status?: string;
}): Promise<{
  total: number;
  schemes: Scheme[];
}> {
  const params = new URLSearchParams();
  if (filters?.category) params.append('category', filters.category);
  if (filters?.jurisdiction) params.append('jurisdiction', filters.jurisdiction);
  if (filters?.verification_status) params.append('verification_status', filters.verification_status);

  const url = `${API_BASE}/schemes${params.toString() ? `?${params.toString()}` : ''}`;
  const res = await fetch(url);
  if (!res.ok) {
    throw new Error(`Failed to fetch schemes: ${res.statusText}`);
  }
  return res.json();
}

export async function fetchSchemeDetail(schemeId: string): Promise<SchemeDetail> {
  const res = await fetch(`${API_BASE}/schemes/${schemeId}`);
  if (!res.ok) {
    throw new Error(`Failed to fetch scheme details: ${res.statusText}`);
  }
  return res.json();
}

export async function assessEligibility(
  schemeId: string,
  profileOverride?: Record<string, any>,
  sessionId?: string | null
): Promise<EligibilityAssessment> {
  const headers: Record<string, string> = { 'Content-Type': 'application/json' };
  if (sessionId) {
    headers['X-Session-ID'] = sessionId;
  }

  const res = await fetch(`${API_BASE}/eligibility/assess`, {
    method: 'POST',
    headers,
    body: JSON.stringify({
      scheme_id: schemeId,
      profile_override: profileOverride || null,
    }),
  });

  if (!res.ok) {
    const errBody = await res.json().catch(() => null);
    const detail = errBody?.detail || res.statusText;
    throw new Error(`Eligibility assessment failed: ${detail}`);
  }
  return res.json();
}

export async function fetchProfile(
  citizenId: string,
  sessionId?: string | null
): Promise<CitizenProfile> {
  const headers: Record<string, string> = {};
  if (sessionId) {
    headers['X-Session-ID'] = sessionId;
  }

  const res = await fetch(`${API_BASE}/profile/${citizenId}`, { headers });
  if (!res.ok) {
    throw new Error(`Failed to fetch profile: ${res.statusText}`);
  }
  const data = await res.json();
  return {
    age: data.age,
    state: data.state,
    district: data.district,
    landAcres: data.land_acres,
    landType: data.land_type,
    annualIncome: data.annual_income,
    rationCardType: data.ration_card_type,
    occupation: data.occupation,
    socialCategory: data.social_category,
    gender: data.gender,
    isIncomeTaxPayer: data.is_income_tax_payer,
    hasPuccaHouse: data.has_pucca_house,
    ownsAgriculturalLand: data.owns_agricultural_land,
    hasGirlChildUnder10: data.has_girl_child_under_10,
    hasExistingLpg: data.has_existing_lpg,
    enrolledInCropInsurance: data.enrolled_in_crop_insurance,
    residenceType: data.residence_type,
    bisVerified: data.bis_verified,
    awaasPlusVerified: data.awaas_plus_verified,
    isConfirmed: data.is_confirmed,
    updatedAt: data.updated_at,
  };
}

export async function updateProfile(
  citizenId: string,
  profile: Partial<CitizenProfile>,
  sessionId?: string | null
): Promise<CitizenProfile> {
  const payload = {
    age: profile.age,
    state: profile.state,
    district: profile.district,
    land_acres: profile.landAcres,
    land_type: profile.landType,
    annual_income: profile.annualIncome,
    ration_card_type: profile.rationCardType,
    occupation: profile.occupation,
    social_category: profile.socialCategory,
    gender: profile.gender,
    is_income_tax_payer: profile.isIncomeTaxPayer,
    has_pucca_house: profile.hasPuccaHouse,
    owns_agricultural_land: profile.ownsAgriculturalLand,
    has_girl_child_under_10: profile.hasGirlChildUnder10,
    has_existing_lpg: profile.hasExistingLpg,
    enrolled_in_crop_insurance: profile.enrolledInCropInsurance,
    residence_type: profile.residenceType,
    bis_verified: profile.bisVerified,
    awaas_plus_verified: profile.awaasPlusVerified,
    is_confirmed: profile.isConfirmed,
  };

  const headers: Record<string, string> = { 'Content-Type': 'application/json' };
  if (sessionId) {
    headers['X-Session-ID'] = sessionId;
  }

  const res = await fetch(`${API_BASE}/profile/${citizenId}`, {
    method: 'PUT',
    headers,
    body: JSON.stringify(payload),
  });
  if (!res.ok) {
    throw new Error(`Failed to update profile: ${res.statusText}`);
  }
  const data = await res.json();
  const updated = data.profile;
  return {
    age: updated.age,
    state: updated.state,
    district: updated.district,
    landAcres: updated.land_acres,
    landType: updated.land_type,
    annualIncome: updated.annual_income,
    rationCardType: updated.ration_card_type,
    occupation: updated.occupation,
    socialCategory: updated.social_category,
    gender: updated.gender,
    isIncomeTaxPayer: updated.is_income_tax_payer,
    hasPuccaHouse: updated.has_pucca_house,
    ownsAgriculturalLand: updated.owns_agricultural_land,
    hasGirlChildUnder10: updated.has_girl_child_under_10,
    hasExistingLpg: updated.has_existing_lpg,
    enrolledInCropInsurance: updated.enrolled_in_crop_insurance,
    residenceType: updated.residence_type,
    bisVerified: updated.bis_verified,
    awaasPlusVerified: updated.awaas_plus_verified,
    isConfirmed: updated.is_confirmed,
    updatedAt: updated.updated_at,
  };
}

export async function fetchVoiceProviders(): Promise<VoiceProvidersInfo> {
  const res = await fetch(`${API_BASE}/voice/providers`);
  if (!res.ok) {
    throw new Error(`Failed to fetch voice providers info: ${res.statusText}`);
  }
  return res.json();
}

export async function transcribeAudio(
  audioBase64: string,
  audioMimeType: string = 'audio/webm',
  language: string = 'hi'
): Promise<VoiceTranscribeResponse> {
  const res = await fetch(`${API_BASE}/voice/transcribe`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      audio_base64: audioBase64,
      audio_mime_type: audioMimeType,
      language,
    }),
  });
  if (!res.ok) {
    const errBody = await res.json().catch(() => null);
    throw new Error(errBody?.detail || `Transcription failed: ${res.statusText}`);
  }
  return res.json();
}

export async function synthesizeSpeech(
  text: string,
  language: string = 'hi'
): Promise<{
  audio_base64: string | null;
  audio_format: string;
  spoken_text: string;
  browser_tts_recommended: boolean;
}> {
  const res = await fetch(`${API_BASE}/voice/speak`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ text, language }),
  });
  if (!res.ok) {
    const errBody = await res.json().catch(() => null);
    throw new Error(errBody?.detail || `Speech synthesis failed: ${res.statusText}`);
  }
  return res.json();
}

export async function sendVoiceTurn(
  payload: {
    text?: string | null;
    audio_base64?: string | null;
    audio_mime_type?: string;
    confirmed_by_user?: boolean | null;
    request_tts?: boolean;
    preferred_language?: string;
  },
  sessionId?: string | null
): Promise<VoiceTurnResponse> {
  const headers: Record<string, string> = { 'Content-Type': 'application/json' };
  if (sessionId) {
    headers['X-Session-ID'] = sessionId;
  }

  const res = await fetch(`${API_BASE}/voice/turn`, {
    method: 'POST',
    headers,
    body: JSON.stringify({
      text: payload.text || null,
      audio_base64: payload.audio_base64 || null,
      audio_mime_type: payload.audio_mime_type || 'audio/webm',
      confirmed_by_user: payload.confirmed_by_user ?? null,
      request_tts: payload.request_tts ?? true,
      preferred_language: payload.preferred_language || 'hi',
    }),
  });

  if (!res.ok) {
    const errBody = await res.json().catch(() => null);
    throw new Error(errBody?.detail || `Voice turn failed: ${res.statusText}`);
  }
  return res.json();
}

// Phase 4: Document Intelligence & CSC Packaging APIs

export async function uploadDocument(
  citizenId: string,
  file: File,
  documentType?: string,
  sessionId?: string | null
): Promise<any> {
  const headers: Record<string, string> = {};
  if (sessionId) {
    headers['X-Session-ID'] = sessionId;
  }

  const formData = new FormData();
  formData.append('file', file);
  formData.append('citizen_id', citizenId);
  if (documentType) {
    formData.append('document_type', documentType);
  }

  const res = await fetch(`${API_BASE}/documents/upload`, {
    method: 'POST',
    headers,
    body: formData,
  });

  if (!res.ok) {
    const err = await res.json().catch(() => null);
    throw new Error(err?.detail || `Upload failed: ${res.statusText}`);
  }
  return res.json();
}

export async function fetchDocuments(
  citizenId: string,
  sessionId?: string | null
): Promise<any[]> {
  const headers: Record<string, string> = {};
  if (sessionId) {
    headers['X-Session-ID'] = sessionId;
  }

  const res = await fetch(`${API_BASE}/documents?citizen_id=${encodeURIComponent(citizenId)}`, {
    headers,
  });

  if (!res.ok) {
    const err = await res.json().catch(() => null);
    throw new Error(err?.detail || `Failed to fetch documents: ${res.statusText}`);
  }
  return res.json();
}

export async function fetchDocumentDetail(
  documentId: string,
  sessionId?: string | null
): Promise<any> {
  const headers: Record<string, string> = {};
  if (sessionId) {
    headers['X-Session-ID'] = sessionId;
  }

  const res = await fetch(`${API_BASE}/documents/${documentId}`, {
    headers,
  });

  if (!res.ok) {
    const err = await res.json().catch(() => null);
    throw new Error(err?.detail || `Failed to fetch document: ${res.statusText}`);
  }
  return res.json();
}

export async function confirmDocument(
  documentId: string,
  payload: {
    confirmed: boolean;
    corrections?: Record<string, any>;
    apply_to_profile?: boolean;
  },
  sessionId?: string | null
): Promise<any> {
  const headers: Record<string, string> = { 'Content-Type': 'application/json' };
  if (sessionId) {
    headers['X-Session-ID'] = sessionId;
  }

  const res = await fetch(`${API_BASE}/documents/${documentId}/confirm`, {
    method: 'PUT',
    headers,
    body: JSON.stringify(payload),
  });

  if (!res.ok) {
    const err = await res.json().catch(() => null);
    throw new Error(err?.detail || `Confirmation failed: ${res.statusText}`);
  }
  return res.json();
}

export async function deleteDocument(
  documentId: string,
  sessionId?: string | null
): Promise<any> {
  const headers: Record<string, string> = {};
  if (sessionId) {
    headers['X-Session-ID'] = sessionId;
  }

  const res = await fetch(`${API_BASE}/documents/${documentId}`, {
    method: 'DELETE',
    headers,
  });

  if (!res.ok) {
    const err = await res.json().catch(() => null);
    throw new Error(err?.detail || `Failed to delete document: ${res.statusText}`);
  }
  return res.json();
}

export async function fetchConsistencyReport(
  citizenId: string,
  sessionId?: string | null
): Promise<any> {
  const headers: Record<string, string> = {};
  if (sessionId) {
    headers['X-Session-ID'] = sessionId;
  }

  const res = await fetch(`${API_BASE}/documents/consistency/${citizenId}`, {
    headers,
  });

  if (!res.ok) {
    const err = await res.json().catch(() => null);
    throw new Error(err?.detail || `Failed to fetch consistency report: ${res.statusText}`);
  }
  return res.json();
}

export async function fetchSchemeChecklist(
  schemeId: string,
  citizenId?: string | null,
  sessionId?: string | null
): Promise<any> {
  const headers: Record<string, string> = {};
  if (sessionId) {
    headers['X-Session-ID'] = sessionId;
  }

  const url = `${API_BASE}/applications/checklist/${schemeId}${citizenId ? `?citizen_id=${encodeURIComponent(citizenId)}` : ''}`;
  const res = await fetch(url, { headers });

  if (!res.ok) {
    const err = await res.json().catch(() => null);
    throw new Error(err?.detail || `Failed to fetch checklist: ${res.statusText}`);
  }
  return res.json();
}

export async function generateCSCPackage(
  payload: {
    citizen_id: string;
    scheme_id: string;
    operator_notes?: string;
    disclaimer_acknowledged?: boolean;
  },
  sessionId?: string | null
): Promise<any> {
  const headers: Record<string, string> = { 'Content-Type': 'application/json' };
  if (sessionId) {
    headers['X-Session-ID'] = sessionId;
  }

  const res = await fetch(`${API_BASE}/applications/package`, {
    method: 'POST',
    headers,
    body: JSON.stringify(payload),
  });

  if (!res.ok) {
    const err = await res.json().catch(() => null);
    throw new Error(err?.detail || `Package generation failed: ${res.statusText}`);
  }
  return res.json();
}

export async function fetchCitizenDrafts(
  citizenId: string,
  sessionId?: string | null
): Promise<any[]> {
  const headers: Record<string, string> = {};
  if (sessionId) {
    headers['X-Session-ID'] = sessionId;
  }

  const res = await fetch(`${API_BASE}/applications/drafts/${citizenId}`, {
    headers,
  });

  if (!res.ok) {
    const err = await res.json().catch(() => null);
    throw new Error(err?.detail || `Failed to fetch drafts: ${res.statusText}`);
  }
  return res.json();
}

export function getCSCPackagePdfUrl(draftId: string, sessionId?: string | null): string {
  const query = sessionId ? `?session_id=${encodeURIComponent(sessionId)}` : '';
  return `${API_BASE}/applications/package/${draftId}/pdf${query}`;
}



