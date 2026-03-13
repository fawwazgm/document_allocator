from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from typing import Any


# Shared metadata shape used by the UI, storage layer, and AI providers.
DOCUMENT_CATEGORIES = (
    "incoming_document",
    "project_document",
    "comment_sheet",
    "comment",
    "checklist",
    "certificate",
    "correspondence",
    "other",
)

SUBTYPE_CATEGORY_HINTS = {
    "certificate": "certificate",
    "comment sheet": "comment_sheet",
    "commentsheet": "comment_sheet",
    "comment": "comment",
    "checklist": "checklist",
    "correspondence": "correspondence",
    "email": "correspondence",
}


def normalize_text(value: Any) -> str:
    return str(value or "").strip()


def normalize_document_category(raw_category: Any, raw_subtype: Any) -> str:
    category = normalize_text(raw_category).lower().replace(" ", "_")
    if category in DOCUMENT_CATEGORIES:
        return category

    subtype = normalize_text(raw_subtype).lower()
    for hint, mapped in SUBTYPE_CATEGORY_HINTS.items():
        if hint in subtype:
            return mapped

    return "incoming_document"


def default_mfiles_property_candidates() -> dict[str, str]:
    return {
        "project_code": "PD.Project",
        "document_number": "PD.DocumentNumber or PD.ClientDocumentNumber",
        "revision": "PD.Revision or PD.ClientRevisionNumber",
    }


@dataclass
class DocumentMetadata:
    """Normalized document record used throughout the app."""

    source_filename: str = ""
    customer: str = ""
    project_code: str = ""
    project_title: str = ""
    module: str = ""
    document_title: str = ""
    document_number: str = ""
    revision: str = ""
    document_category: str = "incoming_document"
    document_subtype: str = ""
    originating_company: str = ""
    submitted_date: str = ""
    summary: str = ""
    source_system: str = "docpilot"
    confidence: float | None = None
    raw_provider_payload: str = ""
    mfiles_class_candidate: str = "IncomingDocument"
    mfiles_property_candidates: dict[str, str] = field(
        default_factory=default_mfiles_property_candidates
    )
    mfiles_notes: str = (
        "Current PDFs most likely map to IncomingDocument until a test vault confirms "
        "the final class and property mapping."
    )

    @classmethod
    def from_provider_payload(
        cls,
        payload: dict[str, Any],
        *,
        source_filename: str,
        provider_name: str,
    ) -> "DocumentMetadata":
        # Providers can return slightly different keys, so we normalize them here once.
        customer = normalize_text(payload.get("customer"))
        subtype = normalize_text(payload.get("document_subtype") or payload.get("document_type"))
        category = normalize_document_category(payload.get("document_category"), subtype)
        raw_payload = json.dumps(payload, indent=2, ensure_ascii=False)
        confidence_value = payload.get("confidence")
        try:
            confidence = float(confidence_value) if confidence_value not in (None, "") else None
        except (TypeError, ValueError):
            confidence = None

        return cls(
            source_filename=source_filename,
            customer=customer,
            project_code=normalize_text(payload.get("project_code") or payload.get("project")),
            project_title=normalize_text(payload.get("project_title")),
            module=normalize_text(payload.get("module")),
            document_title=normalize_text(payload.get("document_title")),
            document_number=normalize_text(payload.get("document_number")),
            revision=normalize_text(payload.get("revision")),
            document_category=category,
            document_subtype=subtype,
            originating_company=normalize_text(payload.get("originating_company") or customer),
            submitted_date=normalize_text(payload.get("submitted_date")),
            summary=normalize_text(payload.get("summary")),
            source_system="docpilot",
            confidence=confidence,
            raw_provider_payload=raw_payload,
            mfiles_class_candidate=normalize_text(
                payload.get("mfiles_class_candidate") or "IncomingDocument"
            ),
            mfiles_notes=normalize_text(payload.get("mfiles_notes")) or cls().mfiles_notes,
        )

    def resolved_document_type(self) -> str:
        return self.document_subtype or self.document_category

    def to_dict(self) -> dict[str, Any]:
        # Keep a couple of legacy keys so saved JSON stays familiar to earlier versions.
        data = asdict(self)
        data.update(
            {
                "project": self.project_code,
                "document_type": self.resolved_document_type(),
            }
        )
        return data


@dataclass
class ProcessingResult:
    """Small result object returned for each uploaded file."""

    file: str
    status: str
    reason: str
    original_pdf: str = ""
    summary_pdf: str = ""
    problem_file: str = ""

    def to_dict(self) -> dict[str, str]:
        return asdict(self)
