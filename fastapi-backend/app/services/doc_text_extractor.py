"""Pull plain text out of an uploaded .txt/.md or .pdf document."""

from __future__ import annotations


class UnsupportedDocumentError(ValueError):
    """Raised when the upload is neither text nor PDF, or has no extractable text."""


def _extract_pdf_text(data: bytes) -> str:
    from pypdf import PdfReader
    from io import BytesIO

    reader = PdfReader(BytesIO(data))
    pages = [page.extract_text() or "" for page in reader.pages]
    return "\n".join(pages)


def extract_text(filename: str, content_type: str, data: bytes) -> str:
    name = (filename or "").lower()
    is_pdf = name.endswith(".pdf") or (content_type or "") == "application/pdf"

    if is_pdf:
        text = _extract_pdf_text(data)
    else:
        try:
            text = data.decode("utf-8")
        except UnicodeDecodeError as exc:
            raise UnsupportedDocumentError(
                "Could not decode the upload as UTF-8 text or PDF"
            ) from exc

    text = text.strip()
    if not text:
        raise UnsupportedDocumentError("No extractable text found in the uploaded document")
    return text
