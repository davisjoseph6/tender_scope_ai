"""Lecture PDF, sans dépendance à Streamlit."""
import io

from pypdf import PdfReader


def extract_pages(content: bytes, document: str) -> list[dict]:
    reader = PdfReader(io.BytesIO(content))
    if reader.is_encrypted and not reader.decrypt(""):
        raise ValueError("Ce PDF est protégé par un mot de passe.")
    return [
        {"document": document, "page": number, "text": page.extract_text() or ""}
        for number, page in enumerate(reader.pages, start=1)
    ]
