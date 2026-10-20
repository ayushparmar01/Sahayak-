import test from 'node:test';
import assert from 'node:assert';
import { translations } from '../src/i18n/translations.ts';
import {
  fetchVoiceProviders,
  sendVoiceTurn,
  transcribeAudio,
  synthesizeSpeech,
} from '../src/services/api.ts';

test('Voice Assistant translations: complete Hindi and English symmetry', () => {
  assert.ok(translations.hi.voiceAssistant, 'Hindi voiceAssistant section exists');
  assert.ok(translations.en.voiceAssistant, 'English voiceAssistant section exists');

  const hiKeys = Object.keys(translations.hi.voiceAssistant).sort();
  const enKeys = Object.keys(translations.en.voiceAssistant).sort();

  assert.deepStrictEqual(
    hiKeys,
    enKeys,
    'Hindi and English voiceAssistant translations must have exact identical keys'
  );

  // Check critical keys
  assert.ok(translations.hi.voiceAssistant.grantVoiceConsent.includes('सहमति'));
  assert.ok(translations.hi.voiceAssistant.confirmBtn.includes('पुष्टि'));
  assert.ok(translations.hi.voiceAssistant.rulesEngine.includes('Zero LLM'));
});

test('Voice API Client: fetchVoiceProviders executes GET /api/v1/voice/providers', async () => {
  const originalFetch = globalThis.fetch;
  let requestedUrl = '';

  globalThis.fetch = async (url) => {
    requestedUrl = url;
    return {
      ok: true,
      json: async () => ({
        stt_provider: 'mock',
        tts_provider: 'mock',
        llm_provider: 'mock',
        is_mock: true,
        supported_languages: ['hi', 'en'],
        audio_limits: {
          max_file_size_bytes: 10485760,
          max_duration_seconds: 60,
          max_conversation_turns: 15,
          supported_mime_types: ['audio/webm', 'audio/wav'],
        },
      }),
    };
  };

  try {
    const providers = await fetchVoiceProviders();
    assert.strictEqual(requestedUrl, '/api/v1/voice/providers');
    assert.strictEqual(providers.stt_provider, 'mock');
    assert.strictEqual(providers.audio_limits.max_conversation_turns, 15);
  } finally {
    globalThis.fetch = originalFetch;
  }
});

test('Voice API Client: sendVoiceTurn attaches X-Session-ID header and handles confirmation', async () => {
  const originalFetch = globalThis.fetch;
  let passedHeaders = {};
  let passedBody = {};

  globalThis.fetch = async (url, options) => {
    passedHeaders = options.headers;
    passedBody = JSON.parse(options.body);
    return {
      ok: true,
      json: async () => ({
        session_id: 'sess_123',
        citizen_id: 'cit_456',
        turn_count: 2,
        status: 'completed',
        transcript: 'हाँ यह सही है',
        transcript_confidence: 1.0,
        is_profile_confirmed: true,
        proposed_profile_updates: {},
        persisted_profile_updates: { occupation: 'farmer' },
        evaluated_schemes: [],
        response_text_hi: 'प्रोफ़ाइल सुरक्षित कर ली गई है।',
        response_text_en: 'Profile has been saved.',
        provider_info: { stt: 'direct_text_input' },
      }),
    };
  };

  try {
    const response = await sendVoiceTurn(
      {
        text: 'हाँ यह सही है',
        confirmed_by_user: true,
        preferred_language: 'hi',
      },
      'sess_test_xyz'
    );

    assert.strictEqual(passedHeaders['X-Session-ID'], 'sess_test_xyz');
    assert.strictEqual(passedBody.text, 'हाँ यह सही है');
    assert.strictEqual(passedBody.confirmed_by_user, true);
    assert.strictEqual(response.is_profile_confirmed, true);
    assert.strictEqual(response.persisted_profile_updates.occupation, 'farmer');
  } finally {
    globalThis.fetch = originalFetch;
  }
});

test('Voice API Client: transcribeAudio sends base64 payload to /api/v1/voice/transcribe', async () => {
  const originalFetch = globalThis.fetch;
  let requestedUrl = '';
  let payloadSent = {};

  globalThis.fetch = async (url, options) => {
    requestedUrl = url;
    payloadSent = JSON.parse(options.body);
    return {
      ok: true,
      json: async () => ({
        transcript: 'मैं किसान हूँ',
        confidence: 0.95,
        language: 'hi',
        is_mock: true,
        duration_seconds: 3.5,
      }),
    };
  };

  try {
    const result = await transcribeAudio('dummy_base64_data', 'audio/webm', 'hi');
    assert.strictEqual(requestedUrl, '/api/v1/voice/transcribe');
    assert.strictEqual(payloadSent.audio_base64, 'dummy_base64_data');
    assert.strictEqual(result.transcript, 'मैं किसान हूँ');
    assert.strictEqual(result.confidence, 0.95);
  } finally {
    globalThis.fetch = originalFetch;
  }
});

test('Voice API Client: synthesizeSpeech sends text to /api/v1/voice/speak', async () => {
  const originalFetch = globalThis.fetch;
  let requestedUrl = '';
  let payloadSent = {};

  globalThis.fetch = async (url, options) => {
    requestedUrl = url;
    payloadSent = JSON.parse(options.body);
    return {
      ok: true,
      json: async () => ({
        audio_base64: 'dummy_wav_base64',
        audio_format: 'audio/wav',
        spoken_text: 'नमस्ते',
        browser_tts_recommended: true,
      }),
    };
  };

  try {
    const res = await synthesizeSpeech('नमस्ते', 'hi');
    assert.strictEqual(requestedUrl, '/api/v1/voice/speak');
    assert.strictEqual(payloadSent.text, 'नमस्ते');
    assert.strictEqual(res.spoken_text, 'नमस्ते');
  } finally {
    globalThis.fetch = originalFetch;
  }
});
