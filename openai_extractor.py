from __future__ import annotations

import json

from openai import OpenAI

from models import DocumentMetadata


class OpenAIMetadataExtractor:
    provider_name = "openai"

    def __init__(self, *, api_key: str, model: str) -> None:
        self.client = OpenAI(api_key=api_key)
        self.model = model

    def extract_metadata(self, text: str, source_filename: str) -> DocumentMetadata:
        # We cap the text sent to the model to keep requests fast and predictable.
        truncated_text = text[:12000]
        response = self.client.responses.create(
            model=self.model,
            store=False,
            input=[
                {
                    "role": "system",
                    "content": (
                        "You extract structured document metadata for a Marine Warranty Survey "
                        "workflow. Return only schema-compliant data. Prefer exact values from "
                        "the document. Use empty strings when unknown. Choose the broadest valid "
                        "document_category, and use document_subtype for specific labels."
                    ),
                },
                {
                    "role": "user",
                    "content": (
                        f"Source filename: {source_filename}\n\n"
                        "Extract document metadata from the following PDF text.\n\n"
                        f"{truncated_text}"
                    ),
                },
            ],
            text={
                "format": {
                    "type": "json_schema",
                    "name": "document_metadata",
                    "strict": True,
                    "schema": {
                        "type": "object",
                        "additionalProperties": False,
                        "properties": {
                            "customer": {"type": "string"},
                            "project_code": {"type": "string"},
                            "project_title": {"type": "string"},
                            "module": {"type": "string"},
                            "document_title": {"type": "string"},
                            "document_number": {"type": "string"},
                            "revision": {"type": "string"},
                            "document_category": {
                                "type": "string",
                                "enum": [
                                    "incoming_document",
                                    "project_document",
                                    "comment_sheet",
                                    "comment",
                                    "checklist",
                                    "certificate",
                                    "correspondence",
                                    "other",
                                ],
                            },
                            "document_subtype": {"type": "string"},
                            "originating_company": {"type": "string"},
                            "submitted_date": {"type": "string"},
                            "summary": {"type": "string"},
                            "confidence": {"type": "number"},
                            "mfiles_class_candidate": {"type": "string"},
                            "mfiles_notes": {"type": "string"},
                        },
                        "required": [
                            "customer",
                            "project_code",
                            "project_title",
                            "module",
                            "document_title",
                            "document_number",
                            "revision",
                            "document_category",
                            "document_subtype",
                            "originating_company",
                            "submitted_date",
                            "summary",
                            "confidence",
                            "mfiles_class_candidate",
                            "mfiles_notes",
                        ],
                    },
                }
            },
        )
        output_text = getattr(response, "output_text", "")
        if not output_text:
            raise RuntimeError("OpenAI response did not contain structured output text.")
        # Convert the model output into the app's single canonical metadata shape.
        payload = json.loads(output_text)
        return DocumentMetadata.from_provider_payload(
            payload,
            source_filename=source_filename,
            provider_name=self.provider_name,
        )
