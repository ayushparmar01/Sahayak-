import test from 'node:test';
import assert from 'node:assert';
import { translations } from '../src/i18n/translations.ts';
import {
  uploadDocument,
  confirmDocument,
  generateCSCPackage,
  getCSCPackagePdfUrl,
  fetchSchemeChecklist,
} from '../src/services/api.ts';

test('Document Intelligence translations: Hindi and English key symmetry', () => {
  assert.ok(translations.hi.documentsPage, 'Hindi documentsPage exists');
  assert.ok(translations.en.documentsPage, 'English documentsPage exists');

  const hiKeys = Object.keys(translations.hi.documentsPage).sort();
  const enKeys = Object.keys(translations.en.documentsPage).sort();

  assert.deepStrictEqual(
    hiKeys,
    enKeys,
    'Hindi and English documentsPage translations must have exact identical keys'
  );

  assert.ok(translations.hi.documentsPage.securityBanner.includes('12-अंकों का आधार'));
  assert.ok(translations.en.documentsPage.securityBanner.includes('never store 12-digit raw Aadhaar'));
});

test('CSC Applications translations: Hindi and English key symmetry and statutory disclaimer', () => {
  assert.ok(translations.hi.applicationsPage, 'Hindi applicationsPage exists');
  assert.ok(translations.en.applicationsPage, 'English applicationsPage exists');

  const hiKeys = Object.keys(translations.hi.applicationsPage).sort();
  const enKeys = Object.keys(translations.en.applicationsPage).sort();

  assert.deepStrictEqual(
    hiKeys,
    enKeys,
    'Hindi and English applicationsPage translations must have exact identical keys'
  );

  assert.ok(translations.hi.applicationsPage.disclaimerBanner.includes('वैधानिक अस्वीकरण'));
  assert.ok(translations.en.applicationsPage.disclaimerBanner.includes('STATUTORY DISCLAIMER'));
});

test('Document API: confirmDocument sends PUT with review corrections and X-Session-ID', async () => {
  const originalFetch = globalThis.fetch;
  let capturedUrl = '';
  let capturedMethod = '';
  let capturedHeaders = {};
  let capturedBody = null;

  globalThis.fetch = async (url, opts) => {
    capturedUrl = url;
    capturedMethod = opts.method;
    capturedHeaders = opts.headers;
    capturedBody = JSON.parse(opts.body);
    return {
      ok: true,
      json: async () => ({
        document_id: 'doc-123',
        review_status: 'CONFIRMED',
        citizen_confirmed: true,
        final_fields: { land_area_hectares: 1.8 },
        profile_updated: true,
        updated_profile_fields: ['owns_agricultural_land', 'land_acres'],
        message: 'Saved',
      }),
    };
  };

  try {
    const res = await confirmDocument(
      'doc-123',
      {
        confirmed: true,
        corrections: { land_area_hectares: 1.8 },
        apply_to_profile: true,
      },
      'sess-xyz'
    );

    assert.strictEqual(capturedUrl, '/api/v1/documents/doc-123/confirm');
    assert.strictEqual(capturedMethod, 'PUT');
    assert.strictEqual(capturedHeaders['X-Session-ID'], 'sess-xyz');
    assert.strictEqual(capturedBody.confirmed, true);
    assert.strictEqual(capturedBody.apply_to_profile, true);
    assert.strictEqual(res.profile_updated, true);
  } finally {
    globalThis.fetch = originalFetch;
  }
});

test('CSC Packaging API: generateCSCPackage sends POST with disclaimer acknowledgement', async () => {
  const originalFetch = globalThis.fetch;
  let capturedUrl = '';
  let capturedBody = null;

  globalThis.fetch = async (url, opts) => {
    capturedUrl = url;
    capturedBody = JSON.parse(opts.body);
    return {
      ok: true,
      json: async () => ({
        draft_id: 'draft-999',
        citizen_id: 'citizen-1',
        scheme_id: 'pm-kisan',
        status: 'DRAFT_READY',
        completeness_percentage: 95.0,
        pdf_download_url: '/api/v1/applications/package/draft-999/pdf',
        package_summary: {},
        cross_document_checks: [],
        checklist_status: {},
        disclaimer: 'Preparation aid only',
        created_at: new Date().toISOString(),
      }),
    };
  };

  try {
    const pkg = await generateCSCPackage(
      {
        citizen_id: 'citizen-1',
        scheme_id: 'pm-kisan',
        operator_notes: 'Verified land record',
        disclaimer_acknowledged: true,
      },
      'sess-xyz'
    );

    assert.strictEqual(capturedUrl, '/api/v1/applications/package');
    assert.strictEqual(capturedBody.scheme_id, 'pm-kisan');
    assert.strictEqual(capturedBody.disclaimer_acknowledged, true);
    assert.strictEqual(pkg.completeness_percentage, 95.0);
    assert.strictEqual(getCSCPackagePdfUrl(pkg.draft_id), '/api/v1/applications/package/draft-999/pdf');
  } finally {
    globalThis.fetch = originalFetch;
  }
});
