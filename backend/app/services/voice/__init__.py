"""Voice & Indic NLP provider registry and factories."""
from app.core.config import settings
from app.services.voice.base import BaseSTTProvider, BaseTTSProvider, BaseExtractionProvider
from app.services.voice.mock_providers import MockSTTProvider, MockTTSProvider
from app.services.voice.extractor import DeterministicIndicExtractor
from app.services.voice.pyttsx3_provider import Pyttsx3TTSProvider
from app.services.voice.sarvam_provider import SarvamSTTProvider, SarvamTTSProvider
from app.services.voice.bhashini_provider import BhashiniSTTProvider, BhashiniTTSProvider


def get_stt_provider() -> BaseSTTProvider:
    """Returns configured Speech-to-Text provider."""
    provider_name = (settings.STT_PROVIDER or "mock").lower()
    if provider_name == "sarvam" and settings.SARVAM_API_KEY:
        return SarvamSTTProvider()
    if provider_name == "bhashini" and settings.BHASHINI_API_KEY:
        return BhashiniSTTProvider()
    return MockSTTProvider()


def get_tts_provider() -> BaseTTSProvider:
    """Returns configured Text-to-Speech provider."""
    provider_name = (settings.TTS_PROVIDER or "mock").lower()
    if provider_name == "sarvam" and settings.SARVAM_API_KEY:
        return SarvamTTSProvider()
    if provider_name == "bhashini" and settings.BHASHINI_API_KEY:
        return BhashiniTTSProvider()
    if provider_name == "pyttsx3":
        return Pyttsx3TTSProvider()
    return MockTTSProvider()


def get_extraction_provider() -> BaseExtractionProvider:
    """Returns intent and profile attribute extraction provider."""
    return DeterministicIndicExtractor()
