"""Compatibility wrapper for the refactored Streamlit app.

The original monolithic implementation is preserved below in `LEGACY_APP`
so it remains in the repository for reference without being deleted.

Only `run()` is active. `LEGACY_APP` is stored as a string on purpose so it
stays easy to recover without affecting the current app behavior.
"""

from streamlit_app import run


# Legacy copy of the original single-file app kept for reference during the refactor.
LEGACY_APP = r'''
import os
import io
import json
import shutil
from datetime import datetime
from pathlib import Path

import streamlit as st
from PIL import Image
import google.generativeai as genai
from pypdf import PdfReader
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.pagesizes import letter




# Configuration


GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
if not GEMINI_API_KEY:
    st.error("GEMINI_API_KEY environment variable not set.")
    st.stop()

genai.configure(api_key=GEMINI_API_KEY)

def resolve_base_dir() -> Path:
    configured = os.getenv("MWS_BASE_DIR", "").strip()
    if configured:
        return Path(configured).expanduser()
    return Path.cwd() / "MWS"


# Map dropdown options to real folders on disk
BASE_DIR = resolve_base_dir()
PROJECT_FOLDERS = {
    "Project 1": BASE_DIR / "project_1",
    "Project 2": BASE_DIR / "project_2",
    "Project 3": BASE_DIR / "project_3",
}

for p in PROJECT_FOLDERS.values():
    (p / "originals").mkdir(parents=True, exist_ok=True)
    (p / "summaries").mkdir(parents=True, exist_ok=True)
    (p / "problem_files").mkdir(parents=True, exist_ok=True)
    (p / "archive").mkdir(parents=True, exist_ok=True)



# Helpers


def extract_text_from_pdf(file_obj) -> str:
    """
    file_obj should be a file-like object (e.g., io.BytesIO).
    """
    reader = PdfReader(file_obj)
    chunks = []
    for page in reader.pages:
        text = page.extract_text() or ""
        chunks.append(text)
    return "\n".join(chunks)


def call_gemini_for_metadata(text: str) -> dict:
    model = genai.GenerativeModel("gemini-2.5-flash")

    prompt = f"""
You are an assistant for a Marine Warranty Survey (MWS) team called Global Maritime.

From the following document text, extract structured metadata.
Respond ONLY with a valid JSON object. NO explanation, no backticks.

The JSON must have these keys:
- "customer": string
- "project": string          // job number, if present (e.g. "A46.01-8B-00453")
- "module": string           // e.g. "Module M04", if present
- "document_title": string
- "document_number": string
- "revision": string         // e.g. "R0", "R1"
- "document_type": string    // e.g. "procedure", "calculation", "drawing", "certificate", "report", "email", "other"
- "submitted_date": string   // ISO date if possible, else ""
- "summary": string          // 3-5 sentence summary of the document

If some fields are unknown, use an empty string "".

Document text (may be truncated):
{text[:7000]}
"""

    resp = model.generate_content(prompt)
    raw = (resp.text or "").strip()

    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        trimmed = raw.strip("` \n")
        trimmed = trimmed.replace("json", "", 1).strip()
        try:
            data = json.loads(trimmed)
        except json.JSONDecodeError:
            data = {
                "error": "Failed to parse JSON from Gemini response",
                "raw_response": raw,
            }

    return data


def create_summary_pdf(metadata: dict, output_path: Path):
    styles = getSampleStyleSheet()
    doc = SimpleDocTemplate(str(output_path), pagesize=letter)
    story = []

    title = metadata.get("document_title", "Document Summary")
    customer = metadata.get("customer", "")
    project = metadata.get("project", "")
    doc_no = metadata.get("document_number", "")
    rev = metadata.get("revision", "")
    doc_type = metadata.get("document_type", "")
    submitted_date = metadata.get("submitted_date", "")
    summary = metadata.get("summary", "")

    header = f"<b>{title}</b><br/>"
    header += f"Customer: {customer}<br/>"
    header += f"Project: {project}<br/>"
    header += f"Document Number: {doc_no}<br/>"
    header += f"Revision: {rev}<br/>"
    header += f"Type: {doc_type}<br/>"
    header += f"Submitted Date: {submitted_date}<br/><br/>"
    story.append(Paragraph(header, styles["Normal"]))
    story.append(Spacer(1, 12))

    story.append(Paragraph("<b>AI-Generated Summary</b><br/><br/>", styles["Normal"]))
    story.append(Paragraph(summary.replace("\n", "<br/>"), styles["Normal"]))

    doc.build(story)


def build_filename(metadata: dict) -> str:
    """
    Build a standard file name:
    Job# - Module - Doc_Title - Rev
    """
    job = (metadata.get("project") or "").strip()
    module = (metadata.get("module") or "").strip()
    title = (metadata.get("document_title") or "").strip()
    rev = (metadata.get("revision") or "").strip()

    parts = [p for p in [job, module, title, rev] if p]
    base = " - ".join(parts) if parts else "unknown_document"

    # Clean illegal characters for Windows filenames
    for bad in r'\/:*?"<>|':
        base = base.replace(bad, "_")

    return base or "unknown_document"



# Index management


INDEX_FILENAME = "index.json"

def load_index(project_folder: Path) -> dict:
    index_path = project_folder / INDEX_FILENAME
    if index_path.exists():
        try:
            with open(index_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}
    return {}


def save_index(project_folder: Path, index: dict) -> None:
    index_path = project_folder / INDEX_FILENAME
    with open(index_path, "w", encoding="utf-8") as f:
        json.dump(index, f, indent=2, ensure_ascii=False)


def make_doc_key(metadata: dict) -> str:
    project = (metadata.get("project") or "").strip().lower()
    doc_no = (metadata.get("document_number") or "").strip().lower()
    return f"{project}|{doc_no}"


def parse_rev(rev: str) -> int:
    if not rev:
        return -1
    r = rev.strip().upper()
    if r.startswith("R"):
        r = r[1:]
    try:
        return int(r)
    except ValueError:
        return -1



# Batch processing core


def move_if_exists(path_str: str, dest_dir: Path):
    if not path_str:
        return
    p = Path(path_str)
    if p.exists():
        shutil.move(str(p), str(dest_dir / p.name))


def process_one_pdf(uploaded_file, project_folder: Path, index: dict) -> dict:
    """
    Process one UploadedFile.
    Returns a result dict for table output.
    Mutates `index` in-place when a doc is successfully stored/updated.
    """
    originals_dir = project_folder / "originals"
    summaries_dir = project_folder / "summaries"
    problem_dir = project_folder / "problem_files"
    archive_dir = project_folder / "archive"

    # Grab bytes once (avoids stream pointer problems)
    file_bytes = uploaded_file.getvalue()

    # STEP 1: Extract text
    text = extract_text_from_pdf(io.BytesIO(file_bytes))

    # STEP 2: Gemini
    metadata = call_gemini_for_metadata(text)
    if "error" in metadata:
        stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        problem_path = problem_dir / f"{Path(uploaded_file.name).stem}_{stamp}_GEMINI_JSON_ERROR.pdf"
        problem_path.write_bytes(file_bytes)
        return {
            "file": uploaded_file.name,
            "status": "problem",
            "reason": "Gemini JSON parse failed",
            "original_pdf": "",
            "summary_pdf": "",
            "problem_file": str(problem_path),
        }

    # STEP 3: In-system check (local index)
    doc_key = make_doc_key(metadata)
    in_system = doc_key in index

    if in_system:
        existing = index[doc_key]
        existing_meta = existing.get("metadata", {})

        # Job mismatch check
        old_project = (existing_meta.get("project") or "").strip()
        new_project = (metadata.get("project") or "").strip()
        if old_project and new_project and old_project != new_project:
            base_name = build_filename(metadata)
            problem_path = problem_dir / f"{base_name}_JOB_MISMATCH.pdf"
            problem_path.write_bytes(file_bytes)
            return {
                "file": uploaded_file.name,
                "status": "problem",
                "reason": f"Job mismatch (index:{old_project} vs upload:{new_project})",
                "original_pdf": "",
                "summary_pdf": "",
                "problem_file": str(problem_path),
            }

        # Revision check
        existing_rev_str = existing_meta.get("revision", "")
        new_rev_str = metadata.get("revision", "")

        old_rev = parse_rev(existing_rev_str)
        new_rev = parse_rev(new_rev_str)

        if new_rev == -1:
            base_name = build_filename(metadata)
            problem_path = problem_dir / f"{base_name}_BAD_REV.pdf"
            problem_path.write_bytes(file_bytes)
            return {
                "file": uploaded_file.name,
                "status": "problem",
                "reason": "Bad / unparsable revision",
                "original_pdf": "",
                "summary_pdf": "",
                "problem_file": str(problem_path),
            }

        if old_rev != -1 and new_rev <= old_rev:
            base_name = build_filename(metadata)
            problem_path = problem_dir / f"{base_name}_OLD_OR_DUPLICATE_REV.pdf"
            problem_path.write_bytes(file_bytes)
            return {
                "file": uploaded_file.name,
                "status": "problem",
                "reason": f"Old/duplicate revision (existing:{existing_rev_str}, upload:{new_rev_str})",
                "original_pdf": "",
                "summary_pdf": "",
                "problem_file": str(problem_path),
            }

        # Newer revision -> archive old outputs (pdf/summary/meta if tracked)
        move_if_exists(existing.get("original_path", ""), archive_dir)
        move_if_exists(existing.get("summary_path", ""), archive_dir)
        move_if_exists(existing.get("meta_path", ""), archive_dir)

    # STEP 4: Save outputs
    base_name = build_filename(metadata)

    original_path = originals_dir / f"{base_name}.pdf"
    original_path.write_bytes(file_bytes)

    summary_path = summaries_dir / f"{base_name}_summary.pdf"
    create_summary_pdf(metadata, summary_path)

    meta_path = originals_dir / f"{base_name}_metadata.json"
    meta_path.write_text(json.dumps(metadata, indent=2, ensure_ascii=False), encoding="utf-8")

    # Update index
    index[doc_key] = {
        "metadata": metadata,
        "original_path": str(original_path),
        "summary_path": str(summary_path),
        "meta_path": str(meta_path),
    }

    return {
        "file": uploaded_file.name,
        "status": "updated" if in_system else "ok",
        "reason": "newer revision replaced + archived old" if in_system else "new doc",
        "original_pdf": str(original_path),
        "summary_pdf": str(summary_path),
        "problem_file": "",
    }



# UI


# Logo is optional (doesn't crash if missing)
try:
    logo = Image.open("gmlogo.png")
    st.image(logo, width=200)
except Exception:
    pass

st.title("MWS DocPilot")
st.caption(f"Base storage folder: {BASE_DIR}")

project_name = st.selectbox("Select Project", list(PROJECT_FOLDERS.keys()))
uploaded_files = st.file_uploader("Upload PDF(s)", type=["pdf"], accept_multiple_files=True)

MAX_FILES = 10
st.caption(f"Max {MAX_FILES} files per batch.")

if st.button("Process Document(s)"):
    if not uploaded_files:
        st.warning("Please upload at least one PDF.")
        st.stop()

    if len(uploaded_files) > int(MAX_FILES):
        st.error(f"Too many files. Please upload {int(MAX_FILES)} or fewer at a time.")
        st.stop()

    project_folder = PROJECT_FOLDERS[project_name]
    index = load_index(project_folder)

    progress = st.progress(0)
    status_box = st.empty()
    results = []

    for i, f in enumerate(uploaded_files, start=1):
        status_box.info(f"Processing {i}/{len(uploaded_files)}: {f.name}")

        try:
            res = process_one_pdf(f, project_folder, index)
        except Exception as e:
            res = {
                "file": f.name,
                "status": "error",
                "reason": str(e),
                "original_pdf": "",
                "summary_pdf": "",
                "problem_file": "",
            }

        results.append(res)
        progress.progress(i / len(uploaded_files))

    # Save index once at the end (faster + cleaner)
    save_index(project_folder, index)

    status_box.success("Batch complete âœ…")
    st.subheader("Batch results")
    st.dataframe(results, width="stretch")

    # Optional: download results as JSON (easy to keep with your batch logs)
    st.download_button(
        "Download results (JSON)",
        data=json.dumps(results, indent=2),
        file_name="docpilot_batch_results.json",
        mime="application/json",
    )

    st.write("**Project folder:**", str(project_folder))
'''


run()
