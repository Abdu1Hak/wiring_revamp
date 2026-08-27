"""
rag/ingestor.py
─────────────────────────────────────────────────────────────────────────
PURPOSE: Raw content extraction ONLY.
- PDF bytes  → two-layer extraction:
    Layer 1: PyMuPDF digital text extraction (fast, lossless)
    Layer 2: Tesseract OCR on image-heavy pages (handles scanned/image PDFs)
- URL        → headless browser fetch via Playwright (JS-rendered pages)

Called exclusively by the Celery task (T4). Never called directly by agent.

OCR STRATEGY:
  For each page:
    1. Extract embedded digital text via page.get_text("text")
    2. If text is sparse (< OCR_TEXT_THRESHOLD chars) OR page has embedded
       raster images, render the page at 300 DPI and run Tesseract OCR.
    3. Merge: use whichever source is longer, or combine both if both have
       meaningful content. Deduplication applied via set-based line comparison.
"""
import logging
import os
import io
from typing import cast

import pymupdf as fitz  # PyMuPDF

logger = logging.getLogger(__name__)

# ── OCR Configuration ────────────────────────────────────────────────────────

# Pages with fewer than this many characters of embedded text trigger OCR.
OCR_TEXT_THRESHOLD = 80

# DPI to render pages for OCR — 300 is the minimum for reliable Tesseract accuracy.
OCR_DPI = 300

# Tesseract binary path on Windows. Falls back to PATH if not set.
TESSERACT_CMD = os.getenv(
    "TESSERACT_CMD",
    r"C:\Program Files\Tesseract-OCR\tesseract.exe"
)


def _get_tesseract_available() -> bool:
    """Check once at import time whether Tesseract is available."""
    try:
        import pytesseract
        pytesseract.pytesseract.tesseract_cmd = TESSERACT_CMD
        pytesseract.get_tesseract_version()
        return True
    except Exception:
        return False


_TESSERACT_AVAILABLE = _get_tesseract_available()
if not _TESSERACT_AVAILABLE:
    logger.warning(
        "[INGESTOR] Tesseract OCR not found — OCR layer disabled. "
        "Install from https://github.com/UB-Mannheim/tesseract/wiki "
        "and set TESSERACT_CMD in .env if not in PATH."
    )


def _ocr_page(page: fitz.Page) -> str:
    """
    Render a PDF page to a PIL image at OCR_DPI and run Tesseract OCR on it.
    Returns extracted text string, or '' if Tesseract unavailable or fails.
    """
    if not _TESSERACT_AVAILABLE:
        return ""
    try:
        import pytesseract
        from PIL import Image

        pytesseract.pytesseract.tesseract_cmd = TESSERACT_CMD

        # Render page to pixel map (RGB, 300 DPI)
        mat = fitz.Matrix(OCR_DPI / 72, OCR_DPI / 72)  # 72 DPI base
        pix = page.get_pixmap(matrix=mat, colorspace=fitz.csRGB)

        # Convert to PIL Image via raw bytes
        img = Image.open(io.BytesIO(pix.tobytes("png")))

        # Run Tesseract — lang=eng, PSM 3 (fully automatic page segmentation)
        # pyrefly: ignore [bad-assignment]
        ocr_text: str = pytesseract.image_to_string(img, lang="eng", config="--psm 3", output_type=pytesseract.Output.STRING)
        return ocr_text.strip()
    except Exception as e:
        logger.warning(f"[INGESTOR] OCR failed on page: {e}")
        return ""


def _merge_texts(digital_text: str, ocr_text: str) -> str:
    """
    Merge digital text extraction with OCR output.
    Strategy: combine both, deduplicate lines, prefer digital text ordering.
    """
    if not ocr_text:
        return digital_text
    if not digital_text:
        return ocr_text

    # Deduplicate: OCR often reproduces digital text imperfectly.
    # Keep all digital lines, then append OCR-unique lines.
    digital_lines = [l.strip() for l in digital_text.splitlines() if l.strip()]
    ocr_lines = [l.strip() for l in ocr_text.splitlines() if l.strip()]

    digital_set = {l.lower() for l in digital_lines}
    ocr_unique = [l for l in ocr_lines if l.lower() not in digital_set]

    if ocr_unique:
        combined = digital_text.rstrip() + "\n\n[OCR]\n" + "\n".join(ocr_unique)
        return combined
    return digital_text


def _page_has_raster_images(page: fitz.Page) -> bool:
    """Return True if the page contains any embedded raster images."""
    return len(page.get_images(full=False)) > 0


def _extract_page(page: fitz.Page, page_num: int) -> str:
    """
    Two-layer extraction for a single page.
    Layer 1: Digital text. Layer 2: OCR if needed.
    Returns combined page text with page header.
    """
    # Layer 1: digital text
    # pyrefly: ignore [missing-attribute]
    digital_text = (page.get_text("text") or "").strip()

    # Decide whether to run OCR
    needs_ocr = (
        _TESSERACT_AVAILABLE and (
            len(digital_text) < OCR_TEXT_THRESHOLD or   # sparse text page
            _page_has_raster_images(page)                # page contains images
        )
    )

    if needs_ocr:
        ocr_text = _ocr_page(page)
        logger.debug(
            f"[INGESTOR] Page {page_num + 1}: digital={len(digital_text)}ch, "
            f"ocr={len(ocr_text)}ch"
        )
        merged = _merge_texts(digital_text, ocr_text)
    else:
        merged = digital_text

    return merged


# ── Public API ────────────────────────────────────────────────────────────────

def extract_text_from_pdf_bytes(pdf_bytes: bytes) -> str:
    """
    Full two-layer extraction from all PDF pages.
    Layer 1: PyMuPDF digital text.
    Layer 2: Tesseract OCR on image-heavy or sparse pages.
    Returns concatenated text of all pages.
    """
    try:
        doc = fitz.open(stream=pdf_bytes, filetype="pdf")
        pages_text: list[str] = []

        for page_num, page in enumerate(doc):
            page_content = _extract_page(page, page_num)
            if page_content:
                pages_text.append(f"[Page {page_num + 1}]\n{page_content}")

        doc_len = len(doc)
        doc.close()

        full_text = "\n\n".join(pages_text)
        logger.info(
            f"[INGESTOR] Extracted {len(full_text)} chars from {doc_len} pages "
            f"(OCR {'enabled' if _TESSERACT_AVAILABLE else 'disabled'})"
        )
        return full_text
    except Exception as e:
        logger.error(f"[INGESTOR] PDF extraction failed: {e}")
        raise


def extract_first_pages_for_validation(pdf_bytes: bytes, num_pages: int = 2) -> str:
    """
    Extract only the first N pages — used by the LangGraph validate_datasheet_node
    before committing to a full ingest. Keeps the agent fast.
    Uses two-layer extraction so validation works on scanned PDFs too.
    """
    try:
        doc = fitz.open(stream=pdf_bytes, filetype="pdf")
        pages_text: list[str] = []
        for page_num in range(min(num_pages, len(doc))):
            page_content = _extract_page(doc[page_num], page_num)
            pages_text.append(page_content)
        doc.close()
        return "\n\n".join(pages_text)
    except Exception as e:
        logger.error(f"[INGESTOR] Validation extraction failed: {e}")
        return ""


# Domains that are shopping/retail pages — never contain embeddable datasheets
_BLOCKED_URL_PATTERNS = (
    "google.com/search",
    "google.com/shopping",
    "amazon.com",
    "ebay.com",
    "aliexpress.com",
    "shopee",
    "walmart.com",
    "digikey.com/products",
    "mouser.com/ProductDetail",
    "rs-online.com",
    "farnell.com",
)


def is_datasheet_url(url: str) -> bool:
    """
    Returns False if the URL is obviously a shopping/retail page with no datasheet.
    Returns True if it looks like a legitimate datasheet or component data page.
    """
    url_lower = url.lower()
    for blocked in _BLOCKED_URL_PATTERNS:
        if blocked in url_lower:
            return False
    return True


async def fetch_url_with_playwright(url: str) -> bytes:
    """
    Fetch a datasheet URL using Playwright.
    - Retail/shopping URLs: rejected immediately with clear error
    - Direct PDF URLs: fast httpx download
    - HTML pages: render JS, find embedded PDF link, download
    Returns raw PDF bytes.
    """
    from playwright.async_api import async_playwright
    import httpx

    # Pre-filter: reject known shopping/retail URLs before wasting time
    if not is_datasheet_url(url):
        raise ValueError(
            f"URL appears to be a shopping or product listing page, not a datasheet: {url}. "
            "Please provide a direct PDF link (ending in .pdf) or a manufacturer/distributor datasheet page."
        )

    # Fast path: direct PDF URL
    if url.lower().endswith(".pdf"):
        async with httpx.AsyncClient(follow_redirects=True, timeout=30.0) as client:
            response = await client.get(url)
            response.raise_for_status()
            logger.info(f"[INGESTOR] Direct PDF download: {len(response.content)} bytes")
            return response.content

    # Slow path: render JS page, find PDF link
    # Use domcontentloaded instead of networkidle — avoids infinite hang on
    # pages with continuous background requests (Google, SPAs, etc.)
    browser = None
    async with async_playwright() as p:
        try:
            browser = await p.chromium.launch(headless=True)
            page = await browser.new_page()
            await page.goto(url, wait_until="domcontentloaded", timeout=15000)
            # Give JS a moment to render dynamic links
            await page.wait_for_timeout(2000)
            pdf_links = cast(
                list[str],
                await page.eval_on_selector_all(
                    "a[href$='.pdf'], a[href*='datasheet'], a[href*='Datasheet']",
                    "els => els.map(e => e.href)"
                )
            )
        finally:
            # Always close browser to prevent process leaks
            if browser:
                await browser.close()

        if pdf_links:
            pdf_url = pdf_links[0]
            async with httpx.AsyncClient(follow_redirects=True, timeout=30.0) as client:
                response = await client.get(pdf_url)
                response.raise_for_status()
                logger.info(f"[INGESTOR] Playwright found PDF: {pdf_url}")
                return response.content

        raise ValueError(f"No PDF link found on page: {url}")