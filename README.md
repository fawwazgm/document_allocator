# document_allocator

`document_allocator` is a small Streamlit app for processing Marine Warranty Survey (MWS) PDFs.

It can:

- upload PDF documents in batches
- extract text from each PDF
- use Gemini to generate structured metadata and a short summary
- save the original PDF, metadata JSON, and a generated summary PDF
- track revisions and archive replaced document versions

## Requirements

- Python 3.13
- A `GEMINI_API_KEY` environment variable
- Optional: an `MWS_BASE_DIR` environment variable to control where project files are stored

## Install

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

## Run

```powershell
$env:GEMINI_API_KEY="your_api_key_here"
$env:MWS_BASE_DIR="C:\path\to\MWS"
streamlit run app.py
```

If `MWS_BASE_DIR` is not set, the app will create and use an `MWS` folder inside the project directory.

## Output Structure

- The app creates these folders for each project:
  - `originals`
  - `summaries`
  - `problem_files`
  - `archive`
- Each project also keeps an `index.json` file for revision tracking.
- The logo file is loaded from `gmlogo.png` if present.
