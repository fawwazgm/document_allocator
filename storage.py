from __future__ import annotations

import json
import os
import shutil
from pathlib import Path

from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer

from models import DocumentMetadata


INDEX_FILENAME = "index.json"
DEFAULT_PROJECT_NAMES = ("Project 1", "Project 2", "Project 3")


def resolve_base_dir() -> Path:
    # `MWS_BASE_DIR` lets the app write anywhere without changing code.
    raw = os.getenv("MWS_BASE_DIR", "").strip()
    if raw:
        return Path(raw).expanduser()
    return Path.cwd() / "MWS"


def build_project_folders(
    base_dir: Path | None = None,
    project_names: tuple[str, ...] = DEFAULT_PROJECT_NAMES,
) -> dict[str, Path]:
    # The UI shows friendly project names, but folders stay filesystem-safe.
    root = base_dir or resolve_base_dir()
    folders = {
        project_name: root / project_name.lower().replace(" ", "_")
        for project_name in project_names
    }
    for project_folder in folders.values():
        ensure_project_structure(project_folder)
    return folders


def ensure_project_structure(project_folder: Path) -> None:
    # These folders match the original app behavior.
    for name in ("originals", "summaries", "problem_files", "archive"):
        (project_folder / name).mkdir(parents=True, exist_ok=True)


def load_index(project_folder: Path) -> dict:
    # A broken index should not stop uploads, so we fall back to an empty one.
    index_path = project_folder / INDEX_FILENAME
    if not index_path.exists():
        return {}
    try:
        return json.loads(index_path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def save_index(project_folder: Path, index: dict) -> None:
    index_path = project_folder / INDEX_FILENAME
    index_path.write_text(json.dumps(index, indent=2, ensure_ascii=False), encoding="utf-8")


def move_if_exists(path_str: str, dest_dir: Path) -> None:
    if not path_str:
        return
    path = Path(path_str)
    if path.exists():
        shutil.move(str(path), str(dest_dir / path.name))


def create_summary_pdf(metadata: DocumentMetadata, output_path: Path) -> None:
    # Summary PDFs are meant for quick human review, not as a full export format.
    styles = getSampleStyleSheet()
    doc = SimpleDocTemplate(str(output_path), pagesize=letter)
    story = []

    header = f"<b>{metadata.document_title or 'Document Summary'}</b><br/>"
    header += f"Customer: {metadata.customer}<br/>"
    header += f"Project: {metadata.project_code}<br/>"
    header += f"Document Number: {metadata.document_number}<br/>"
    header += f"Revision: {metadata.revision}<br/>"
    header += f"Category: {metadata.document_category}<br/>"
    header += f"Subtype: {metadata.document_subtype}<br/>"
    header += f"Submitted Date: {metadata.submitted_date}<br/><br/>"
    story.append(Paragraph(header, styles["Normal"]))
    story.append(Spacer(1, 12))
    story.append(Paragraph("<b>AI-Generated Summary</b><br/><br/>", styles["Normal"]))
    story.append(Paragraph(metadata.summary.replace("\n", "<br/>"), styles["Normal"]))
    doc.build(story)
