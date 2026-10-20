"""Read the text of a PDF CV.

The PDF is read from bytes held in memory (what Streamlit's file uploader
gives us). Nothing is written to disk, which keeps the privacy promise of the
app simple: once the session ends, the CV is gone.
"""

from __future__ import annotations

from io import BytesIO

try:  # pdfplumber is the best reader for multi-column CVs...
    import pdfplumber
except ImportError:  # ...but it needs a compiled library that the in-browser version lacks
    pdfplumber = None


class PdfReadError(Exception):
    """Raised when the uploaded file cannot be read as a PDF."""


def extract_text_from_pdf(file_bytes: bytes) -> str:
    """Return all the text of a PDF, page by page, separated by newlines.

    pdfplumber is used because it handles multi-column CV layouts better than
    simpler readers. Scanned PDFs (images without a text layer) return an
    empty string: the caller should warn the user, since OCR is out of scope.

    Raises:
        PdfReadError: if the bytes are not a valid or readable PDF.
    """
    if not file_bytes:
        raise PdfReadError("The uploaded file is empty.")

    try:
        pages_text = []
        if pdfplumber is not None:
            with pdfplumber.open(BytesIO(file_bytes)) as pdf:
                for page in pdf.pages:
                    # extract_text() returns None for pages without a text layer.
                    pages_text.append(page.extract_text() or "")
        else:
            from pypdf import PdfReader  # pure Python, works in the browser

            pages_text = [page.extract_text() or "" for page in PdfReader(BytesIO(file_bytes)).pages]
    except Exception as exc:  # PDF libraries raise several low-level error types
        raise PdfReadError(f"Could not read the PDF: {exc}") from exc

    return "\n".join(pages_text).strip()
