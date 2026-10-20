"""Local offline TTS Provider using pyttsx3."""
import base64
import tempfile
import os
from pathlib import Path
from app.services.voice.base import BaseTTSProvider, TTSResult
from app.services.voice.mock_providers import _generate_minimal_wav_base64


class Pyttsx3TTSProvider(BaseTTSProvider):
    """Local offline TTS synthesis via pyttsx3."""

    def __init__(self):
        self._available = False
        try:
            import pyttsx3  # noqa: F401
            self._available = True
        except ImportError:
            self._available = False

    async def synthesize(self, text: str, language: str = "hi") -> TTSResult:
        clean = (text or "").strip()
        if not clean or not self._available:
            return TTSResult(
                spoken_text=clean,
                audio_base64=_generate_minimal_wav_base64(),
                is_mock=True,
                browser_fallback_recommended=True,
            )

        temp_wav = None
        try:
            import pyttsx3
            engine = pyttsx3.init()
            engine.setProperty("rate", 150)
            
            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
                temp_wav = f.name
            
            engine.save_to_file(clean, temp_wav)
            engine.runAndWait()

            if os.path.exists(temp_wav) and os.path.getsize(temp_wav) > 0:
                with open(temp_wav, "rb") as rf:
                    wav_bytes = rf.read()
                audio_b64 = base64.b64encode(wav_bytes).decode("ascii")
                return TTSResult(
                    spoken_text=clean,
                    audio_base64=audio_b64,
                    audio_format="audio/wav",
                    is_mock=False,
                    browser_fallback_recommended=False,
                )
        except Exception:
            # Fallback on any engine/driver errors
            pass
        finally:
            if temp_wav and os.path.exists(temp_wav):
                try:
                    os.unlink(temp_wav)
                except OSError:
                    pass

        return TTSResult(
            spoken_text=clean,
            audio_base64=_generate_minimal_wav_base64(),
            is_mock=True,
            browser_fallback_recommended=True,
        )
