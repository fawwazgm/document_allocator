from __future__ import annotations

import json

import google.generativeai as genai

from models import DocumentMetadata


class GeminiMetadataExtractor:
    provider_name = "gemini"

    def __init__(self, *, api_key: str, model: str) -> None:
        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel(model)

    def extract_metadata(self, text: str, source_filename: str) -> DocumentMetadata:
        # This prompt mirrors the canonical schema used by the OpenAI extractor.
        truncated_text = text[:12000]
        prompt = f"""
You extract structured document metadata for a Marine Warranty Survey workflow.
Respond ONLY with a valid JSON object. No explanation. No markdown fences.

Rules:
- Prefer exact values from the document.
- Use empty strings for unknown string fields.
- Use the broadest valid document_category.
- Use document_subtype for specific labels like procedure, drawing, report, calculation, email.
- confidence must be a number between 0 and 1.

Allowed document_category values:
- incoming_document
- project_document
- comment_sheet
- comment
- checklist
- certificate
- correspondence
- other

Return a JSON object with exactly these keys:
- customer
- project_code
- project_title
- module
- document_title
- document_number
- revision
- document_category
- document_subtype
- originating_company
- submitted_date
- summary
- confidence
- mfiles_class_candidate
- mfiles_notes

Source filename: {source_filename}

Document text:
{truncated_text}
"""
        response = self.model.generate_content(prompt)
        raw = (response.text or "").strip()
        try:
            payload = json.loads(raw)
        except json.JSONDecodeError:
            # Gemini sometimes wraps JSON in markdown fences or prefixes it with `json`.
            trimmed = raw.strip("` \n")
            if trimmed.lower().startswith("json"):
                trimmed = trimmed[4:].strip()
            payload = json.loads(trimmed)

        return DocumentMetadata.from_provider_payload(
            payload,
            source_filename=source_filename,
            provider_name=self.provider_name,
        )
