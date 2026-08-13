"""
rag/ingestor.py
─────────────────────────────────────────────────────────────────────────
PURPOSE: Raw content extraction ONLY.
- PDF bytes  → extract text via PyMuPDF
- URL        → headless browser fetch via Playwright (JS-rendered pages)
Called exclusively by the Celery task (T4). Never called directly by agent.
"""
import logging
from typing import cast
import pymupdf as fitz  # PyMuPDF

logger = logging.getLogger(__name__)


def extract_text_from_pdf_bytes(pdf_bytes: bytes) -> str:
    """
    Extract full text from PDF bytes using PyMuPDF.
    Returns concatenated text of all pages.
    """
    try:
        doc = fitz.open(stream=pdf_bytes, filetype="pdf")
        pages_text: list[str] = []
        for page_num, page in enumerate(doc):
            text = str(page.get_text("text"))
            if text.strip():
                pages_text.append(f"[Page {page_num + 1}]\n{text}")
        doc_len = len(doc)
        doc.close()
        full_text = "\n\n".join(pages_text)
        logger.info(f"[INGESTOR] Extracted {len(full_text)} chars from {doc_len} pages")
        return full_text
    except Exception as e:
        logger.error(f"[INGESTOR] PDF extraction failed: {e}")
        raise


def extract_first_pages_for_validation(pdf_bytes: bytes, num_pages: int = 3) -> str:
    """
    Extract only the first N pages — used by the LangGraph validate_datasheet_node
    before committing to a full ingest. Keeps the agent fast.
    """
    try:
        doc = fitz.open(stream=pdf_bytes, filetype="pdf")
        pages_text: list[str] = []
        for page_num in range(min(num_pages, len(doc))):
            text = str(doc[page_num].get_text("text"))
            pages_text.append(text)
        doc.close()
        return "\n\n".join(pages_text)
    except Exception as e:
        logger.error(f"[INGESTOR] Validation extraction failed: {e}")
        return ""


async def fetch_url_with_playwright(url: str) -> bytes:
    """
    Fetch a datasheet URL using Playwright.
    - Direct PDF URLs: fast httpx download
    - HTML pages: render JS, find embedded PDF link, download
    Returns raw PDF bytes.
    """
    from playwright.async_api import async_playwright
    import httpx

    # Fast path: direct PDF URL
    if url.lower().endswith(".pdf"):
        async with httpx.AsyncClient(follow_redirects=True, timeout=30.0) as client:
            response = await client.get(url)
            response.raise_for_status()
            logger.info(f"[INGESTOR] Direct PDF download: {len(response.content)} bytes")
            return response.content

    # Slow path: render JS page, find PDF link
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        await page.goto(url, wait_until="networkidle", timeout=30000)
        pdf_links = cast(
            list[str],
            await page.eval_on_selector_all(
                "a[href$='.pdf'], a[href*='datasheet']",
                "els => els.map(e => e.href)"
            )
        )
        await browser.close()

        if pdf_links:
            pdf_url = pdf_links[0]
            async with httpx.AsyncClient(follow_redirects=True, timeout=30.0) as client:
                response = await client.get(pdf_url)
                response.raise_for_status()
                logger.info(f"[INGESTOR] Playwright found PDF: {pdf_url}")
                return response.content

        raise ValueError(f"No PDF found at rendered page: {url}")