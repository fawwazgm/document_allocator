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

## Install

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

## Run

```powershell
$env:GEMINI_API_KEY="your_api_key_here"
streamlit run app.py
```

## Notes

- The app currently writes to project folders under `C:\Users\fawwaz.ibrahim\Desktop\MWS`.
- The logo file is loaded from `gmlogo.png` if present.
