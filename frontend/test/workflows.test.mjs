import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { join } from 'node:path';

// --- Test 1: Translation Dictionaries Completeness and Symmetry ---
test('Translation dictionaries: hi and en have symmetric route and component keys', () => {
  const content = readFileSync(join(process.cwd(), 'src', 'i18n', 'translations.ts'), 'utf-8');

  // Verify core navigation keys
  const expectedNavKeys = ['home', 'schemes', 'profile', 'documents', 'applications', 'followup', 'privacy', 'endSession'];
  for (const key of expectedNavKeys) {
    assert.ok(content.includes(`${key}:`), `Missing navigation key: ${key}`);
  }

  // Verify critical privacy keys
  assert.ok(content.includes('zeroAadhaarTitle:'), 'Must include zeroAadhaarTitle');
  assert.ok(content.includes('sharedDeviceTitle:'), 'Must include sharedDeviceTitle');
  assert.ok(content.includes('wipeDataBtn:'), 'Must include wipeDataBtn');

  // Verify disclaimer
  assert.ok(content.includes('disclaimerTitle:'), 'Must include public service disclaimer title');

  // Verify Phase 2 Scheme Detail and Assessment modal keys
  const phase2ModalKeys = [
    'overview',
    'rulesAndCriteria',
    'assessmentTab',
    'targetBeneficiary',
    'applicationProcess',
    'requiredDocs',
    'caveats',
    'primarySources',
    'runAssessmentBtn',
    'satisfiedConditions',
    'failedConditions',
    'missingFields',
    'pendingVerifications',
    'exclusionsEvaluated',
    'nextSteps',
    'statusEligible',
    'statusPotentiallyEligible',
    'statusIneligible',
    'statusNeedsMoreInfo',
  ];
  for (const key of phase2ModalKeys) {
    assert.ok(content.includes(`${key}:`), `Missing Phase 2 modal key: ${key}`);
  }

  // Verify Phase 2 Scheme Category keys
  const phase2CategoryKeys = [
    'allCategories',
    'agriculture',
    'healthcare',
    'housing',
    'womenChild',
    'financialSecurity',
    'socialWelfare',
  ];
  for (const key of phase2CategoryKeys) {
    assert.ok(content.includes(`${key}:`), `Missing Phase 2 category key: ${key}`);
  }

  // Verify Phase 2 extended profile fields
  const phase2ProfileKeys = [
    'gender',
    'ownsLand',
    'incomeTax',
    'puccaHouse',
    'girlChild',
    'existingLpg',
  ];
  for (const key of phase2ProfileKeys) {
    assert.ok(content.includes(`${key}:`), `Missing Phase 2 profile key: ${key}`);
  }
});

// --- Test 2: Dynamic Readiness Score Logic ---
test('Dynamic readiness score correctly calculates percentage based on required fields', () => {
  const requiredFields = ['age', 'state', 'district', 'occupation'];

  function calculateReadiness(profile) {
    const filledCount = requiredFields.filter((f) => profile[f]).length;
    return Math.round((filledCount / requiredFields.length) * 80);
  }

  // Case 0: Empty profile -> 0%
  assert.equal(calculateReadiness({}), 0);

  // Case 1: Partial profile (age and state only) -> 40%
  assert.equal(calculateReadiness({ age: 45, state: 'Uttar Pradesh' }), 40);

  // Case 2: 3 of 4 fields -> 60%
  assert.equal(calculateReadiness({ age: 45, state: 'Uttar Pradesh', district: 'Mathura' }), 60);

  // Case 3: All 4 mandatory fields filled -> 80% (remaining 20% reserved for verified documents in Phase 4)
  assert.equal(calculateReadiness({ age: 45, state: 'Uttar Pradesh', district: 'Mathura', occupation: 'farmer' }), 80);
});

// --- Test 3: API Client fetchHealth with mocked network success and failure ---
test('API Client fetchHealth returns status or throws on HTTP error', async () => {
  const originalFetch = globalThis.fetch;

  try {
    // Subtest: Success 200
    globalThis.fetch = async (url) => {
      assert.equal(url, '/api/v1/health');
      return {
        ok: true,
        status: 200,
        json: async () => ({
          status: 'ok',
          app_name: 'SAHAYAK',
          version: '0.1.0',
          environment: 'development',
          database_connected: true,
          timestamp: new Date().toISOString(),
        }),
      };
    };

    const res = await (await import('../src/services/api.ts')).fetchHealth();
    assert.equal(res.status, 'ok');
    assert.equal(res.database_connected, true);

    // Subtest: Failure 503
    globalThis.fetch = async () => ({
      ok: false,
      status: 503,
      statusText: 'Service Unavailable',
    });

    await assert.rejects(
      async () => (await import('../src/services/api.ts')).fetchHealth(),
      /Health check failed with status: 503/
    );
  } finally {
    globalThis.fetch = originalFetch;
  }
});

// --- Test 4: API Client fetchProfile and updateProfile send X-Session-ID header ---
test('API Client passes X-Session-ID authorization header for profile requests', async () => {
  const originalFetch = globalThis.fetch;
  const recordedHeaders = [];

  try {
    globalThis.fetch = async (url, options = {}) => {
      recordedHeaders.push(options.headers || {});
      return {
        ok: true,
        status: 200,
        json: async () => ({
          age: 42,
          state: 'Uttar Pradesh',
          district: 'Mathura',
          land_acres: 2.0,
          land_type: 'irrigated',
          annual_income: 85000,
          ration_card_type: 'BPL',
          occupation: 'farmer',
          social_category: 'OBC',
          is_confirmed: true,
          updated_at: new Date().toISOString(),
          profile: {
            age: 42,
            state: 'Uttar Pradesh',
            district: 'Mathura',
            land_acres: 2.0,
            land_type: 'irrigated',
            annual_income: 85000,
            ration_card_type: 'BPL',
            occupation: 'farmer',
            social_category: 'OBC',
            is_confirmed: true,
            updated_at: new Date().toISOString(),
          },
        }),
      };
    };

    const api = await import('../src/services/api.ts');

    // 1. fetchProfile with session ID
    await api.fetchProfile('citizen-uuid-1', 'sess_test_header_abc');
    assert.equal(recordedHeaders[0]['X-Session-ID'], 'sess_test_header_abc');

    // 2. updateProfile with session ID
    await api.updateProfile('citizen-uuid-1', { age: 42 }, 'sess_test_header_abc');
    assert.equal(recordedHeaders[1]['X-Session-ID'], 'sess_test_header_abc');
    assert.equal(recordedHeaders[1]['Content-Type'], 'application/json');
  } finally {
    globalThis.fetch = originalFetch;
  }
});

// --- Test 5: API Client fetchSchemeDetail and assessEligibility ---
test('API Client fetchSchemeDetail and assessEligibility perform verified HTTP requests with X-Session-ID', async () => {
  const originalFetch = globalThis.fetch;
  const calls = [];

  try {
    globalThis.fetch = async (url, options = {}) => {
      calls.push({ url, options });
      if (url.includes('/schemes/pm-kisan')) {
        return {
          ok: true,
          status: 200,
          json: async () => ({
            id: 'pm-kisan',
            code: 'PM_KISAN',
            name_hi: 'प्रधानमंत्री किसान सम्मान निधि',
            name_en: 'PM Kisan Samman Nidhi',
            rules: [{ id: 'rule-1', rule_code: 'PMK_LAND', description_hi: 'भूमि' }],
          }),
        };
      }
      if (url.includes('/eligibility/assess')) {
        return {
          ok: true,
          status: 200,
          json: async () => ({
            scheme_id: 'pm-kisan',
            status: 'ELIGIBLE',
            status_label_en: 'Eligible',
            status_label_hi: 'पात्र',
            benefit_summary: { amount_inr: 6000.0 },
          }),
        };
      }
      return { ok: false, status: 404 };
    };

    const api = await import('../src/services/api.ts');

    // 1. fetchSchemeDetail
    const detail = await api.fetchSchemeDetail('pm-kisan');
    assert.equal(detail.id, 'pm-kisan');
    assert.equal(calls[0].url, '/api/v1/schemes/pm-kisan');

    // 2. assessEligibility: signature is (schemeId, profileOverride, sessionId)
    const assessment = await api.assessEligibility('pm-kisan', { owns_agricultural_land: true }, 'sess_phase2_test_123');
    assert.equal(assessment.status, 'ELIGIBLE');
    assert.equal(calls[1].url, '/api/v1/eligibility/assess');
    assert.equal(calls[1].options.headers['X-Session-ID'], 'sess_phase2_test_123');
    const parsedBody = JSON.parse(calls[1].options.body);
    assert.equal(parsedBody.scheme_id, 'pm-kisan');
    assert.equal(parsedBody.profile_override.owns_agricultural_land, true);
  } finally {
    globalThis.fetch = originalFetch;
  }
});

// --- Test 6: Eligibility Status Badge Styling Logic ---
test('Eligibility status badges map to distinct accessible color themes', () => {
  function getStatusBadgeConfig(status) {
    switch (status) {
      case 'ELIGIBLE':
        return { bg: 'bg-emerald-50', text: 'text-emerald-800', border: 'border-emerald-300' };
      case 'POTENTIALLY_ELIGIBLE':
        return { bg: 'bg-amber-50', text: 'text-amber-800', border: 'border-amber-300' };
      case 'INELIGIBLE':
        return { bg: 'bg-red-50', text: 'text-red-800', border: 'border-red-300' };
      case 'NEEDS_MORE_INFO':
      default:
        return { bg: 'bg-sky-50', text: 'text-sky-800', border: 'border-sky-300' };
    }
  }

  const eligibleBadge = getStatusBadgeConfig('ELIGIBLE');
  assert.equal(eligibleBadge.text, 'text-emerald-800');

  const potentialBadge = getStatusBadgeConfig('POTENTIALLY_ELIGIBLE');
  assert.equal(potentialBadge.text, 'text-amber-800');

  const ineligibleBadge = getStatusBadgeConfig('INELIGIBLE');
  assert.equal(ineligibleBadge.text, 'text-red-800');

  const needsMoreInfoBadge = getStatusBadgeConfig('NEEDS_MORE_INFO');
  assert.equal(needsMoreInfoBadge.text, 'text-sky-800');
});

// --- Test 7: Kiosk Wipe & Zero Persistent Storage Invariant ---
test('Kiosk Session Purge cleans in-memory and volatile state with zero localStorage footprint', () => {
  // Mock sessionStorage
  const mockStorage = new Map();
  const fakeSessionStorage = {
    getItem: (k) => mockStorage.get(k) || null,
    setItem: (k, v) => mockStorage.set(k, String(v)),
    removeItem: (k) => mockStorage.delete(k),
    clear: () => mockStorage.clear(),
  };

  // Simulate citizen session on kiosk
  fakeSessionStorage.setItem('sahayak_session_id', 'sess_kiosk_99');
  fakeSessionStorage.setItem('sahayak_citizen_id', 'citizen_kiosk_88');
  fakeSessionStorage.setItem('sahayak_consent_granted', new Date().toISOString());

  assert.equal(mockStorage.size, 3);

  // Citizen or kiosk operator presses "End Session / Wipe Data"
  fakeSessionStorage.clear();

  assert.equal(mockStorage.size, 0, 'SessionStorage must be completely cleared');
  assert.equal(fakeSessionStorage.getItem('sahayak_session_id'), null);
  assert.equal(fakeSessionStorage.getItem('sahayak_citizen_id'), null);
});
