"""OCR engine using Tesseract (pytesseract) — zero paid dependencies."""
import re
from pathlib import Path

try:
    import pytesseract
    from PIL import Image
    import fitz  # PyMuPDF
    TESSERACT_AVAILABLE = True
except ImportError:
    TESSERACT_AVAILABLE = False


def extract_text_from_report(file_path: str) -> str:
    """
    Extract raw text from an image or PDF report file.

    Returns plain-text string. Raises RuntimeError if Tesseract is not installed.
    """
    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(f"File not found: {file_path}")

    suffix = path.suffix.lower()

    if suffix == ".txt":
        return path.read_text(encoding="utf-8", errors="replace")

    if not TESSERACT_AVAILABLE:
        raise RuntimeError(
            "pytesseract / Pillow / PyMuPDF not installed. "
            "Run: pip install pytesseract pillow pymupdf"
        )

    if suffix == ".pdf":
        return _extract_from_pdf(path)

    if suffix in (".png", ".jpg", ".jpeg", ".tiff", ".bmp", ".gif"):
        return _extract_from_image(path)

    raise ValueError(f"Unsupported file type: {suffix}")


def _extract_from_image(path: Path) -> str:
    """Run Tesseract OCR on a single image file and return raw text."""
    img = Image.open(path)
    text = pytesseract.image_to_string(img, lang="eng")
    return text


def _extract_from_pdf(path: Path) -> str:
    """Extract text from each PDF page, falling back to OCR for image-only pages."""
    doc = fitz.open(str(path))
    pages_text = []
    for page in doc:
        text = page.get_text()
        if text.strip():
            pages_text.append(text)
        else:
            pix = page.get_pixmap(dpi=200)
            img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
            pages_text.append(pytesseract.image_to_string(img, lang="eng"))
    doc.close()
    return "\n".join(pages_text)
