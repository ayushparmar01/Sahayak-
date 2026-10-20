"""Base provider interfaces and contracts for SAHAYAK Voice & Indic NLP."""
from abc import ABC, abstractmethod
from typing import Any
from pydantic import BaseModel, Field


class STTResult(BaseModel):
    """Result of Speech-to-Text transcription."""
    transcript: str
    confidence: float = Field(ge=0.0, le=1.0, default=1.0)
    language: str = "hi"
    is_mock: bool = False
    duration_seconds: float = 0.0
    detected_noise_or_ambiguity: bool = False


class TTSResult(BaseModel):
    """Result of Text-to-Speech synthesis."""
    spoken_text: str
    audio_base64: str | None = None
    audio_format: str = "audio/wav"
    is_mock: bool = False
    browser_fallback_recommended: bool = False
    sample_rate: int = 16000

    @property
    def browser_tts_recommended(self) -> bool:
        return self.browser_fallback_recommended



class ExtractionResult(BaseModel):
    """Result of NLP intent and profile field extraction."""
    intent: str = "general_query"  # update_profile, check_eligibility, confirm_changes, cancel, general_query
    extracted_fields: dict[str, Any] = Field(default_factory=dict)
    confidence: float = Field(ge=0.0, le=1.0, default=1.0)
    is_confirmed: bool = False
    is_cancelled: bool = False
    is_mock: bool = False


class BaseSTTProvider(ABC):
    """Abstract interface for Speech-to-Text providers."""

    @abstractmethod
    async def transcribe(
        self,
        audio_bytes: bytes,
        mime_type: str = "audio/webm",
        language: str = "hi",
    ) -> STTResult:
        """Transcribe speech audio to text."""
        pass


class BaseTTSProvider(ABC):
    """Abstract interface for Text-to-Speech providers."""

    @abstractmethod
    async def synthesize(
        self,
        text: str,
        language: str = "hi",
    ) -> TTSResult:
        """Synthesize text into speech audio."""
        pass


class BaseExtractionProvider(ABC):
    """Abstract interface for intent and demographic profile field extraction."""

    @abstractmethod
    async def extract_intent_and_fields(
        self,
        text: str,
        current_profile: dict[str, Any] | None = None,
        language: str = "hi",
    ) -> ExtractionResult:
        """Extract user intent and supported demographic attributes."""
        pass
