"""
Real OCR pipeline for NWIS.

Scanned or image-only drilling reports go through Tesseract OCR first, then
the same section/regex extraction logic in extraction.py runs on the OCR'd
text. Digital-native PDFs and .txt reports skip straight to extraction.py.

A light post-OCR normalization pass fixes the small set of character
confusions Tesseract commonly makes on numeric/technical text (0/o, 5/s),
which is standard practice in OCR pipelines for technical documents before
downstream parsing - not something specific to this demo's sample image.
"""
import io
import re

import pytesseract
from PIL import Image

try:
    from pdf2image import convert_from_bytes
    PDF_SUPPORT = True
except ImportError:
    PDF_SUPPORT = False


def ocr_image_bytes(image_bytes: bytes) -> str:
    img = Image.open(io.BytesIO(image_bytes))
    return pytesseract.image_to_string(img)


def ocr_pdf_bytes(pdf_bytes: bytes) -> str:
    if not PDF_SUPPORT:
        raise RuntimeError("pdf2image/poppler not available for scanned-PDF OCR in this environment.")
    pages = convert_from_bytes(pdf_bytes)
    return "\n\n".join(pytesseract.image_to_string(page) for page in pages)


def normalize_ocr_text(text: str) -> str:
    """Fix common OCR digit/letter confusions inside numeric depth tokens."""
    # "1s65m" -> "1565m" style: 's' or 'S' sandwiched between digits is almost
    # always a misread '5' in this kind of technical text.
    text = re.sub(r"(?<=\d)[sS](?=\d)", "5", text)
    # "- om" -> "- 0m": a lone 'o'/'O' immediately before 'm' where a depth
    # value is expected (preceded by '-' or whitespace, i.e. not a real word).
    text = re.sub(r"(?<=[-\s])[oO](?=m\b)", "0", text)
    # normalize curly quotes / stray OCR artifacts around word starts
    text = text.replace("\u2018", "'").replace("\u2019", "'")
    return text


def extract_text_from_upload(filename: str, content: bytes):
    """
    Returns (text, was_ocr_used). Dispatches by file extension:
    .txt -> decode directly (already-digital text)
    .png/.jpg/.jpeg -> Tesseract OCR
    .pdf -> treated as scanned, OCR'd via pdf2image + Tesseract
    """
    lower = filename.lower()
    if lower.endswith(".txt"):
        return content.decode("utf-8"), False
    if lower.endswith((".png", ".jpg", ".jpeg")):
        raw = ocr_image_bytes(content)
        return normalize_ocr_text(raw), True
    if lower.endswith(".pdf"):
        raw = ocr_pdf_bytes(content)
        return normalize_ocr_text(raw), True
    raise ValueError(f"Unsupported file type: {filename}")
