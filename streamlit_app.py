from __future__ import annotations

import json

import streamlit as st
from PIL import Image

from pipeline import DocumentPipeline


MAX_FILES = 10


def run() -> None:
    # The UI stays thin: it collects user input and hands work to the pipeline.
    try:
        pipeline = DocumentPipeline()
    except RuntimeError as exc:
        st.error(str(exc))
        st.info("Set OPENAI_API_KEY and optionally OPENAI_MODEL / LLM_PROVIDER before running.")
        st.stop()

    _render_logo()
    st.title("MWS DocPilot")
    st.caption(f"Base storage folder: {pipeline.base_dir}")

    project_name = st.selectbox("Select Project", list(pipeline.project_folders.keys()))
    uploaded_files = st.file_uploader("Upload PDF(s)", type=["pdf"], accept_multiple_files=True)
    st.caption(f"Max {MAX_FILES} files per batch.")

    if not st.button("Process Document(s)"):
        return

    if not uploaded_files:
        st.warning("Please upload at least one PDF.")
        st.stop()

    if len(uploaded_files) > MAX_FILES:
        st.error(f"Too many files. Please upload {MAX_FILES} or fewer at a time.")
        st.stop()

    index = pipeline.load_project_index(project_name)
    progress = st.progress(0)
    status_box = st.empty()
    results = []

    for idx, uploaded_file in enumerate(uploaded_files, start=1):
        status_box.info(f"Processing {idx}/{len(uploaded_files)}: {uploaded_file.name}")
        try:
            result = pipeline.process_one_pdf(uploaded_file, project_name, index)
        except Exception as exc:
            result = {
                "file": uploaded_file.name,
                "status": "error",
                "reason": str(exc),
                "original_pdf": "",
                "summary_pdf": "",
                "problem_file": "",
            }
        else:
            result = result.to_dict()

        results.append(result)
        progress.progress(idx / len(uploaded_files))

    pipeline.save_project_index(project_name, index)
    project_folder = pipeline.project_folders[project_name]
    status_box.success("Batch complete.")
    st.subheader("Batch results")
    st.dataframe(results, width="stretch")
    st.download_button(
        "Download results (JSON)",
        data=json.dumps(results, indent=2),
        file_name="docpilot_batch_results.json",
        mime="application/json",
    )
    # Show the real output paths so it is obvious where files were written.
    st.write("**Project folder:**", str(project_folder))
    st.write("**Originals folder:**", str(project_folder / "originals"))
    st.write("**Summaries folder:**", str(project_folder / "summaries"))
    st.write("**Problem files folder:**", str(project_folder / "problem_files"))
    st.write("**Archive folder:**", str(project_folder / "archive"))


def _render_logo() -> None:
    try:
        logo = Image.open("gmlogo.png")
    except Exception:
        return
    st.image(logo, width=200)
