"""Base interfaces and data structures for Document OCR."""
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class FieldExtractionResult:
    field_name: str
    value: Any
    confidence: float = 1.0
    source_page: int = 1
    is_masked: bool = False
    bbox: list[float] | None = None


@dataclass
class PageExtractionResult:
    page_number: int
    raw_text: str
    fields: dict[str, Any] = field(default_factory=dict)


@dataclass
class OCRExtractionResult:
    provider_name: str
    is_mock: bool
    document_type: str
    overall_confidence: float
    pages: list[PageExtractionResult] = field(default_factory=list)
    extracted_fields: dict[str, Any] = field(default_factory=dict)
    masked_identifier: str | None = None
    raw_text_summary: str = ""
    warnings: list[str] = field(default_factory=list)


class BaseOCRProvider(ABC):
    """Abstract base class for OCR document processors."""

    @abstractmethod
    async def process_document(
        self,
        file_path: Path,
        mime_type: str,
        hint_document_type: str | None = None,
    ) -> OCRExtractionResult:
        """Process a physical document file and extract structured fields."""
        raise NotImplementedError
