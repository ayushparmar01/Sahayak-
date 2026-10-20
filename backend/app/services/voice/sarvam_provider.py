"""Sarvam AI Provider Adapter for Indic Speech Recognition and Synthesis."""
import httpx
from app.core.config import settings
from app.services.voice.base import BaseSTTProvider, BaseTTSProvider, STTResult, TTSResult
from app.services.voice.mock_providers import MockSTTProvider, MockTTSProvider


class SarvamSTTProvider(BaseSTTProvider):
    """Sarvam AI Speech-to-Text (Saaras) adapter."""

    def __init__(self, api_key: str | None = None):
        self.api_key = api_key or settings.SARVAM_API_KEY
        self._fallback = MockSTTProvider()

    async def transcribe(
        self,
        audio_bytes: bytes,
        mime_type: str = "audio/webm",
        language: str = "hi",
    ) -> STTResult:
        if not self.api_key:
            res = await self._fallback.transcribe(audio_bytes, mime_type, language)
            return res

        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                files = {"file": ("audio.webm", audio_bytes, mime_type)}
                data = {
                    "model": "saaras:v1",
                    "language_code": "hi-IN" if language == "hi" else "en-IN",
                }
                headers = {"api-subscription-key": self.api_key}
                response = await client.post(
                    "https://api.sarvam.ai/speech-to-text",
                    files=files,
                    data=data,
                    headers=headers,
                )
                if response.status_code == 200:
                    payload = response.json()
                    transcript = payload.get("transcript", "")
                    return STTResult(
                        transcript=transcript,
                        confidence=0.95,
                        language=language,
                        is_mock=False,
                    )
        except Exception:
            pass

        return await self._fallback.transcribe(audio_bytes, mime_type, language)


class SarvamTTSProvider(BaseTTSProvider):
    """Sarvam AI Text-to-Speech (Bulbul) adapter."""

    def __init__(self, api_key: str | None = None):
        self.api_key = api_key or settings.SARVAM_API_KEY
        self._fallback = MockTTSProvider()

    async def synthesize(self, text: str, language: str = "hi") -> TTSResult:
        if not self.api_key or not text.strip():
            return await self._fallback.synthesize(text, language)

        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                payload = {
                    "inputs": [text],
                    "target_language_code": "hi-IN" if language == "hi" else "en-IN",
                    "speaker": "meera",
                    "model": "bulbul:v1",
                }
                headers = {
                    "api-subscription-key": self.api_key,
                    "Content-Type": "application/json",
                }
                response = await client.post(
                    "https://api.sarvam.ai/text-to-speech",
                    json=payload,
                    headers=headers,
                )
                if response.status_code == 200:
                    res_json = response.json()
                    audios = res_json.get("audios", [])
                    if audios:
                        return TTSResult(
                            spoken_text=text,
                            audio_base64=audios[0],
                            audio_format="audio/wav",
                            is_mock=False,
                            browser_fallback_recommended=False,
                        )
        except Exception:
            pass

        return await self._fallback.synthesize(text, language)
