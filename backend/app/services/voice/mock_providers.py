"""Mock STT and TTS Providers for Local Development and Deterministic Testing.

Guarantees full end-to-end functionality without requiring live external paid API keys.
Returns valid audio payloads and realistic Hindi speech-to-text transcripts.
"""
import base64
import struct
from app.services.voice.base import BaseSTTProvider, BaseTTSProvider, STTResult, TTSResult


def _generate_minimal_wav_base64(duration_seconds: float = 0.5, sample_rate: int = 16000) -> str:
    """Generates a minimal valid PCM 16-bit Mono WAV byte structure encoded as base64."""
    num_samples = int(duration_seconds * sample_rate)
    data_size = num_samples * 2  # 16-bit = 2 bytes per sample
    file_size = 36 + data_size

    # WAV RIFF header
    header = struct.pack(
        "<4sI4s4sIHHIIHH4sI",
        b"RIFF",
        file_size,
        b"WAVE",
        b"fmt ",
        16,  # Subchunk1Size (16 for PCM)
        1,   # AudioFormat (1 for PCM)
        1,   # NumChannels (1 mono)
        sample_rate,
        sample_rate * 2,  # ByteRate
        2,   # BlockAlign
        16,  # BitsPerSample
        b"data",
        data_size,
    )
    # Silent PCM audio data
    audio_data = b"\x00" * data_size
    return base64.b64encode(header + audio_data).decode("ascii")


class MockSTTProvider(BaseSTTProvider):
    """Deterministic Speech-to-Text provider for tests and offline development."""

    def __init__(self, default_transcript: str | None = None):
        self.default_transcript = (
            default_transcript
            or "मैं उत्तर प्रदेश के मथुरा जिले का किसान हूँ, मेरे पास 2 एकड़ जमीन है और पक्का मकान नहीं है।"
        )

    async def transcribe(
        self,
        audio_bytes: bytes,
        mime_type: str = "audio/webm",
        language: str = "hi",
    ) -> STTResult:
        if not audio_bytes:
            return STTResult(
                transcript="",
                confidence=0.0,
                language=language,
                is_mock=True,
                duration_seconds=0.0,
                detected_noise_or_ambiguity=True,
            )

        # Check for simulated test commands encoded in audio bytes
        try:
            raw_text = audio_bytes.decode("utf-8", errors="ignore")
            if "SIMULATE_STT:" in raw_text:
                simulated = raw_text.split("SIMULATE_STT:")[1].split("\n")[0].strip()
                return STTResult(
                    transcript=simulated,
                    confidence=0.98,
                    language=language,
                    is_mock=True,
                    duration_seconds=2.0,
                )
            if "SIMULATE_LOW_CONFIDENCE" in raw_text:
                return STTResult(
                    transcript="मेरी... जमीन... शायद...",
                    confidence=0.35,
                    language=language,
                    is_mock=True,
                    duration_seconds=1.5,
                    detected_noise_or_ambiguity=True,
                )
            if "SIMULATE_ERROR" in raw_text:
                raise RuntimeError("Simulated speech recognition error")
        except UnicodeDecodeError:
            pass

        duration = min(60.0, max(0.5, len(audio_bytes) / 32000.0))
        return STTResult(
            transcript=self.default_transcript,
            confidence=0.95,
            language=language,
            is_mock=True,
            duration_seconds=round(duration, 1),
        )


class MockTTSProvider(BaseTTSProvider):
    """Deterministic Text-to-Speech provider for tests and offline development."""

    async def synthesize(
        self,
        text: str,
        language: str = "hi",
    ) -> TTSResult:
        clean_text = (text or "").strip()
        if not clean_text:
            return TTSResult(
                spoken_text="",
                audio_base64=None,
                is_mock=True,
                browser_fallback_recommended=True,
            )

        # Produce a valid playable minimal WAV base64 string
        audio_b64 = _generate_minimal_wav_base64(duration_seconds=0.5)
        return TTSResult(
            spoken_text=clean_text,
            audio_base64=audio_b64,
            audio_format="audio/wav",
            is_mock=True,
            browser_fallback_recommended=True,
        )
