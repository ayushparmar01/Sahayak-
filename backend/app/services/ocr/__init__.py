"""OCR Service package initializing OCR providers and factory."""
from pathlib import Path
from app.core.config import settings
from app.services.ocr.base import BaseOCRProvider
from app.services.ocr.mock_provider import MockOCRProvider
from app.services.ocr.pdf_extractor import LocalPDFTextOCRProvider


def get_ocr_provider(mime_type: str | None = None, force_mock: bool = False) -> BaseOCRProvider:
    """Returns the appropriate OCR provider based on configuration and MIME type.
    
    - For digital PDF files when force_mock is False: uses LocalPDFTextOCRProvider (is_mock=False).
    - For image files or when force_mock is True: uses MockOCRProvider (is_mock=True).
    """
    if force_mock:
        return MockOCRProvider()

    if mime_type == "application/pdf":
        return LocalPDFTextOCRProvider()

    # For image files when no live cloud vision credentials exist
    return MockOCRProvider()


__all__ = [
    "BaseOCRProvider",
    "MockOCRProvider",
    "LocalPDFTextOCRProvider",
    "get_ocr_provider",
]
