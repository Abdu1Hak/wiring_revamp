
"""
rag/chunker.py
─────────────────────────────────────────────────────────────────────────
PURPOSE: Split raw datasheet text into chunks suitable for embedding.
Strategy: RecursiveCharacterTextSplitter with technical document separators.
- chunk_size=512 tokens (~400 words) — enough context per chunk
- chunk_overlap=50  — prevents splitting a spec table mid-row
Called exclusively by the Celery task (T4).
"""
import logging
from typing import Optional
from langchain_text_splitters import RecursiveCharacterTextSplitter
logger = logging.getLogger(__name__)
# Separators ordered by preference for technical docs
TECHNICAL_SEPARATORS = [
    "\n\n\n",     # section breaks
    "\n\n",       # paragraph breaks
    "\n",         # line breaks
    ". ",         # sentence breaks
    ", ",         # clause breaks
    " ",          # word breaks
]
_splitter = RecursiveCharacterTextSplitter(
    chunk_size=512,
    chunk_overlap=50,
    separators=TECHNICAL_SEPARATORS,
    length_function=len,
)
def chunk_text(raw_text: str, component_id: str) -> list[dict]:
    """
    Split raw text into chunks. Returns list of chunk dicts:
    {
        "text": str,
        "chunk_index": int,
        "component_id": str,
        "char_start": int,
        "char_end": int,
    }
    """
    if not raw_text or not raw_text.strip():
        logger.warning(f"[CHUNKER] Empty text for {component_id}")
        return []
    raw_chunks = _splitter.split_text(raw_text)
    result = []
    char_pos = 0
    for idx, chunk_text in enumerate(raw_chunks):
        start = raw_text.find(chunk_text, char_pos)
        end = start + len(chunk_text)
        result.append({
            "text": chunk_text,
            "chunk_index": idx,
            "component_id": component_id,
            "char_start": start,
            "char_end": end,
        })
        char_pos = max(0, end - 50)  # account for overlap
    logger.info(f"[CHUNKER] {component_id}: {len(raw_chunks)} chunks from {len(raw_text)} chars")
    return result