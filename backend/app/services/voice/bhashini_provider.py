"""Bhashini (National Language Translation Mission) Provider Adapter."""
import base64
import httpx
from app.core.config import settings
from app.services.voice.base import BaseSTTProvider, BaseTTSProvider, STTResult, TTSResult
from app.services.voice.mock_providers import MockSTTProvider, MockTTSProvider


class BhashiniSTTProvider(BaseSTTProvider):
    """Bhashini ULCA ASR pipeline adapter."""

    def __init__(self):
        self.user_id = settings.BHASHINI_USER_ID
        self.api_key = settings.BHASHINI_API_KEY
        self.pipeline_id = settings.BHASHINI_PIPELINE_ID
        self._fallback = MockSTTProvider()

    async def transcribe(
        self,
        audio_bytes: bytes,
        mime_type: str = "audio/webm",
        language: str = "hi",
    ) -> STTResult:
        if not self.api_key or not self.user_id:
            return await self._fallback.transcribe(audio_bytes, mime_type, language)

        try:
            audio_b64 = base64.b64encode(audio_bytes).decode("ascii")
            headers = {
                "userID": self.user_id,
                "ulcaApiKey": self.api_key,
                "Content-Type": "application/json",
            }
            body = {
                "pipelineTasks": [
                    {
                        "taskType": "asr",
                        "config": {
                            "language": {"sourceLanguage": language},
                            "audioFormat": mime_type.split("/")[-1],
                        },
                    }
                ],
                "inputData": {"audio": [{"audioContent": audio_b64}]},
            }
            async with httpx.AsyncClient(timeout=15.0) as client:
                res = await client.post(
                    "https://dhruva-api.bhashini.gov.in/services/inference/pipeline",
                    json=body,
                    headers=headers,
                )
                if res.status_code == 200:
                    data = res.json()
                    transcript = data["pipelineResponse"][0]["output"][0]["source"]
                    return STTResult(
                        transcript=transcript,
                        confidence=0.92,
                        language=language,
                        is_mock=False,
                    )
        except Exception:
            pass

        return await self._fallback.transcribe(audio_bytes, mime_type, language)


class BhashiniTTSProvider(BaseTTSProvider):
    """Bhashini ULCA TTS pipeline adapter."""

    def __init__(self):
        self.user_id = settings.BHASHINI_USER_ID
        self.api_key = settings.BHASHINI_API_KEY
        self.pipeline_id = settings.BHASHINI_PIPELINE_ID
        self._fallback = MockTTSProvider()

    async def synthesize(self, text: str, language: str = "hi") -> TTSResult:
        if not self.api_key or not self.user_id or not text.strip():
            return await self._fallback.synthesize(text, language)

        try:
            headers = {
                "userID": self.user_id,
                "ulcaApiKey": self.api_key,
                "Content-Type": "application/json",
            }
            body = {
                "pipelineTasks": [
                    {
                        "taskType": "tts",
                        "config": {
                            "language": {"sourceLanguage": language},
                            "gender": "female",
                        },
                    }
                ],
                "inputData": {"input": [{"source": text}]},
            }
            async with httpx.AsyncClient(timeout=15.0) as client:
                res = await client.post(
                    "https://dhruva-api.bhashini.gov.in/services/inference/pipeline",
                    json=body,
                    headers=headers,
                )
                if res.status_code == 200:
                    data = res.json()
                    audio_b64 = data["pipelineResponse"][0]["audio"][0]["audioContent"]
                    return TTSResult(
                        spoken_text=text,
                        audio_base64=audio_b64,
                        audio_format="audio/wav",
                        is_mock=False,
                        browser_fallback_recommended=False,
                    )
        except Exception:
            pass

        return await self._fallback.synthesize(text, language)
