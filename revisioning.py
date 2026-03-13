from models import DocumentMetadata


def build_filename(metadata: DocumentMetadata) -> str:
    # Match the original naming convention so stored files stay predictable.
    parts = [
        metadata.project_code.strip(),
        metadata.module.strip(),
        metadata.document_title.strip(),
        metadata.revision.strip(),
    ]
    base = " - ".join(part for part in parts if part) or "unknown_document"
    for bad in r'\/:*?"<>|':
        base = base.replace(bad, "_")
    return base


def make_doc_key(metadata: DocumentMetadata) -> str:
    # Project + document number is the local identity used for revision checks.
    project = metadata.project_code.strip().lower()
    doc_no = metadata.document_number.strip().lower()
    return f"{project}|{doc_no}"


def parse_rev(revision: str) -> int:
    # Revisions are expected to look like R0, R1, R2, etc.
    if not revision:
        return -1
    normalized = revision.strip().upper()
    if normalized.startswith("R"):
        normalized = normalized[1:]
    try:
        return int(normalized)
    except ValueError:
        return -1
