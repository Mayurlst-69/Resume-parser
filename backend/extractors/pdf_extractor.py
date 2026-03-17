import pdfplumber
from pathlib import Path


def extract_text_from_pdf(file_path: str) -> tuple[str, bool]:
    """
    Try to extract text directly from PDF text layer.
    Returns (text, is_text_based).
    If text is empty or very short → is_text_based=False (needs OCR).
    """
    try:
        with pdfplumber.open(file_path) as pdf:
            pages_text = []
            for page in pdf.pages:
                text = page.extract_text()
                if text:
                    pages_text.append(text.strip())

            full_text = "\n".join(pages_text).strip()

            # Heuristic: fewer than 50 chars means no real text layer
            is_text_based = len(full_text) >= 50
            return full_text, is_text_based

    except Exception as e:
        return "", False
