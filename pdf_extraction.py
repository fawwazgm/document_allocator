from pypdf import PdfReader


def extract_text_from_pdf(file_obj) -> str:
    reader = PdfReader(file_obj)
    chunks: list[str] = []
    for page in reader.pages:
        chunks.append(page.extract_text() or "")
    return "\n".join(chunks).strip()
