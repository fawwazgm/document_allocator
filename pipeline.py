from __future__ import annotations

import io
import json
from datetime import datetime
from pathlib import Path

from llm_provider import get_metadata_extractor
from models import DocumentMetadata, ProcessingResult
from pdf_extraction import extract_text_from_pdf
from revisioning import build_filename, make_doc_key, parse_rev
from storage import (
    build_project_folders,
    create_summary_pdf,
    load_index,
    move_if_exists,
    save_index,
)


class DocumentPipeline:
    """Coordinates extraction, revision checks, and file storage for one batch item."""

    def __init__(self) -> None:
        self.extractor = get_metadata_extractor()
        self.project_folders = build_project_folders()
        self.base_dir = next(iter(self.project_folders.values())).parent

    def load_project_index(self, project_name: str) -> dict:
        return load_index(self.project_folders[project_name])

    def save_project_index(self, project_name: str, index: dict) -> None:
        save_index(self.project_folders[project_name], index)

    def process_one_pdf(self, uploaded_file, project_name: str, index: dict) -> ProcessingResult:
        project_folder = self.project_folders[project_name]
        problem_dir = project_folder / "problem_files"
        file_bytes = uploaded_file.getvalue()
        try:
            # Extract text first, then hand only text + filename to the AI provider.
            text = extract_text_from_pdf(io.BytesIO(file_bytes))
            metadata = self.extractor.extract_metadata(text, uploaded_file.name)
            metadata = self._finalize_metadata_defaults(metadata, uploaded_file.name)
        except Exception as exc:
            # Any extraction/provider failure is treated as a problem file, not a crash.
            fallback_metadata = DocumentMetadata(
                source_filename=uploaded_file.name,
                document_title=Path(uploaded_file.name).stem,
            )
            return self._write_problem(
                metadata=fallback_metadata,
                file_bytes=file_bytes,
                problem_dir=problem_dir,
                suffix="EXTRACTION_ERROR",
                reason=str(exc),
            )

        originals_dir = project_folder / "originals"
        summaries_dir = project_folder / "summaries"
        archive_dir = project_folder / "archive"
        doc_key = make_doc_key(metadata)
        in_system = doc_key in index
        if in_system:
            # Existing records are checked before we write any new files.
            revision_problem = self._validate_existing_revision(
                metadata, index[doc_key], archive_dir, file_bytes, problem_dir
            )
            if revision_problem:
                return revision_problem

        base_name = build_filename(metadata)
        original_path = originals_dir / f"{base_name}.pdf"
        original_path.write_bytes(file_bytes)

        summary_path = summaries_dir / f"{base_name}_summary.pdf"
        create_summary_pdf(metadata, summary_path)

        meta_path = originals_dir / f"{base_name}_metadata.json"
        meta_path.write_text(json.dumps(metadata.to_dict(), indent=2, ensure_ascii=False), encoding="utf-8")

        index[doc_key] = {
            "metadata": metadata.to_dict(),
            "original_path": str(original_path),
            "summary_path": str(summary_path),
            "meta_path": str(meta_path),
        }

        return ProcessingResult(
            file=uploaded_file.name,
            status="updated" if in_system else "ok",
            reason="newer revision replaced + archived old" if in_system else "new doc",
            original_pdf=str(original_path),
            summary_pdf=str(summary_path),
        )

    def _finalize_metadata_defaults(
        self, metadata: DocumentMetadata, source_filename: str
    ) -> DocumentMetadata:
        # Fill the minimum fields the storage layer expects, even if the model missed them.
        metadata.source_filename = source_filename
        if not metadata.document_title:
            metadata.document_title = Path(source_filename).stem
        if not metadata.document_category:
            metadata.document_category = "incoming_document"
        if not metadata.mfiles_class_candidate:
            metadata.mfiles_class_candidate = "IncomingDocument"
        return metadata

    def _validate_existing_revision(
        self,
        metadata: DocumentMetadata,
        existing_record: dict,
        archive_dir: Path,
        file_bytes: bytes,
        problem_dir: Path,
    ) -> ProcessingResult | None:
        # Revision logic stays intentionally close to the original single-file app.
        existing_meta = existing_record.get("metadata", {})
        old_project = str(existing_meta.get("project") or existing_meta.get("project_code") or "").strip()
        new_project = metadata.project_code.strip()
        if old_project and new_project and old_project != new_project:
            return self._write_problem(
                metadata=metadata,
                file_bytes=file_bytes,
                problem_dir=problem_dir,
                suffix="JOB_MISMATCH",
                reason=f"Job mismatch (index:{old_project} vs upload:{new_project})",
            )

        existing_rev = str(existing_meta.get("revision", ""))
        old_rev = parse_rev(existing_rev)
        new_rev = parse_rev(metadata.revision)

        if new_rev == -1:
            return self._write_problem(
                metadata=metadata,
                file_bytes=file_bytes,
                problem_dir=problem_dir,
                suffix="BAD_REV",
                reason="Bad / unparsable revision",
            )

        if old_rev != -1 and new_rev <= old_rev:
            return self._write_problem(
                metadata=metadata,
                file_bytes=file_bytes,
                problem_dir=problem_dir,
                suffix="OLD_OR_DUPLICATE_REV",
                reason=f"Old/duplicate revision (existing:{existing_rev}, upload:{metadata.revision})",
            )

        move_if_exists(existing_record.get("original_path", ""), archive_dir)
        move_if_exists(existing_record.get("summary_path", ""), archive_dir)
        move_if_exists(existing_record.get("meta_path", ""), archive_dir)
        return None

    def _write_problem(
        self,
        *,
        metadata: DocumentMetadata,
        file_bytes: bytes,
        problem_dir: Path,
        suffix: str,
        reason: str,
    ) -> ProcessingResult:
        # Problem files are kept with a timestamp so failed uploads are still traceable.
        stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        base_name = build_filename(metadata)
        problem_path = problem_dir / f"{base_name}_{suffix}_{stamp}.pdf"
        problem_path.write_bytes(file_bytes)
        return ProcessingResult(
            file=metadata.source_filename,
            status="problem",
            reason=reason,
            problem_file=str(problem_path),
        )
