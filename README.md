# document_allocator

`document_allocator` is a small Streamlit app for processing Marine Warranty Survey (MWS) PDFs.

It can:

- upload PDF documents in batches
- extract text from each PDF
- use OpenAI Structured Outputs to generate structured metadata and a short summary
- save the original PDF, metadata JSON, and a generated summary PDF
- track revisions and archive replaced document versions
- prepare metadata that can later map more cleanly into M-Files concepts

## Requirements

- Python 3.13
- An `OPENAI_API_KEY` environment variable
- Optional: `OPENAI_MODEL` to override the default model
- Optional: `LLM_PROVIDER` to select the metadata provider
- Optional: `GEMINI_API_KEY` and `GEMINI_MODEL` when testing with Gemini
- Optional: an `MWS_BASE_DIR` environment variable to control where project files are stored

## Install

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

## Run

```powershell
$env:OPENAI_API_KEY="your_api_key_here"
$env:OPENAI_MODEL="gpt-5-mini"
$env:LLM_PROVIDER="openai"
$env:MWS_BASE_DIR="C:\path\to\MWS"
streamlit run app.py
```

For Gemini testing:

```powershell
$env:GEMINI_API_KEY="your_api_key_here"
$env:GEMINI_MODEL="gemini-2.5-flash"
$env:LLM_PROVIDER="gemini"
$env:MWS_BASE_DIR="C:\path\to\MWS"
streamlit run app.py
```

Replace `C:\path\to\MWS` with a real folder path on your machine, for example
`C:\Users\fawwaz.ibrahim\Desktop\MWS`.

If `MWS_BASE_DIR` is not set, the app will create and use an `MWS` folder inside the project directory.

## Architecture

- [`app.py`](C:\Users\fawwaz.ibrahim\Desktop\Mini Projects\document_allocator\app.py) is now a thin wrapper that preserves the old monolithic Streamlit app as a legacy commented block.
- Only the wrapper import and `run()` call are active in `app.py`; the legacy code is stored for reference only.
- The active app uses modular components for PDF extraction, metadata modeling, revision handling, storage, and LLM provider selection.
- The metadata extractor is swappable through `LLM_PROVIDER`, so you can test with Gemini and later switch to OpenAI without changing the pipeline code.
- The canonical metadata model now includes future-facing M-Files mapping hints such as `mfiles_class_candidate` and `mfiles_property_candidates`.

## Output Structure

- The app creates these folders for each project:
  - `originals`
  - `summaries`
  - `problem_files`
  - `archive`
- Each project also keeps an `index.json` file for revision tracking.
- The logo file is loaded from `gmlogo.png` if present.
