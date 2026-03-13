from __future__ import annotations

import os
from typing import Protocol

from models import DocumentMetadata
from gemini_extractor import GeminiMetadataExtractor
from openai_extractor import OpenAIMetadataExtractor


class MetadataExtractor(Protocol):
    """Minimal contract every metadata provider must follow."""

    provider_name: str

    def extract_metadata(self, text: str, source_filename: str) -> DocumentMetadata:
        ...


def get_metadata_extractor() -> MetadataExtractor:
    # Provider choice is entirely env-driven so the pipeline code stays unchanged.
    provider = os.getenv("LLM_PROVIDER", "openai").strip().lower()
    if provider == "openai":
        api_key = os.getenv("OPENAI_API_KEY", "").strip()
        if not api_key:
            raise RuntimeError("OPENAI_API_KEY environment variable not set.")
        model = os.getenv("OPENAI_MODEL", "gpt-5-mini").strip() or "gpt-5-mini"
        return OpenAIMetadataExtractor(api_key=api_key, model=model)
    if provider == "gemini":
        api_key = os.getenv("GEMINI_API_KEY", "").strip()
        if not api_key:
            raise RuntimeError("GEMINI_API_KEY environment variable not set.")
        model = os.getenv("GEMINI_MODEL", "gemini-2.5-flash").strip() or "gemini-2.5-flash"
        return GeminiMetadataExtractor(api_key=api_key, model=model)
    raise RuntimeError(f"Unsupported LLM_PROVIDER: {provider}")
