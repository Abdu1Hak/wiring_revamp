"""
rag/embedder.py
─────────────────────────────────────────────────────────────────────────
PURPOSE: Convert text chunks → 768-dim vectors using Gemini text-embedding-004.
Free tier limits: 1,500 requests/day, 100 requests/minute.
Strategy: batch in groups of 20, with exponential backoff on 429.
Called exclusively by the Celery task (T4).
"""

import os
import logging
from typing import Optional
import time 
from dotenv import load_dotenv
from google import genai
from google.genai import types

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# ENVIRONMENT & CLIENT SETUP
# ---------------------------------------------------------------------------

_this_dir = os.path.dirname(os.path.abspath(__file__))
_backend_dir = os.path.dirname(_this_dir)
load_dotenv(os.path.join(_backend_dir, "db", ".env"))
load_dotenv(os.path.join(_backend_dir, ".env"))
load_dotenv()

# Reuse the same Gemini client pattern as ai_service.py
_client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

# ---------------------------------------------------------------------------
# EMBEDDING MODEL CONFIGURATION
# ---------------------------------------------------------------------------
EMBEDDING_MODEL = "models/gemini-embedding-001"   # Google's latest embedding model
EMBEDDING_DIMENSIONS = 768                      # Match Qdrant collection vector size
MAX_BATCH_SIZE = 20                            # Optimal batch size for Gemini API rate limits

# ---------------------------------------------------------------------------
# BATCH TEXT EMBEDDING
# ---------------------------------------------------------------------------
def embed_chunks(texts: list[str], progress_callback=None) -> list[list[float]]:
    """
    Embed a list of text strings in batches.
    Returns list of float vectors.
    """
    if not texts:
        return []

    all_embeddings = []
    total_batches = (len(texts) + MAX_BATCH_SIZE - 1) // MAX_BATCH_SIZE

    # Process in batches of MAX_BATCH_SIZE to respect API limits
    for batch_start in range(0, len(texts), MAX_BATCH_SIZE):
        batch = texts[batch_start : batch_start + MAX_BATCH_SIZE]
        batch_num = (batch_start // MAX_BATCH_SIZE) + 1

        logger.info(
            f"[Embedder] Embedding batch {batch_num}/{total_batches} "
            f"({len(batch)} texts)"
        )

        if progress_callback:
            progress_callback(batch_num, total_batches)

        # Try 5 times with exponential backoff on 429
        success = False
        for attempt in range(5):
            try:
                response = _client.models.embed_content(
                    model=EMBEDDING_MODEL,
                    contents=batch,
                    config=types.EmbedContentConfig(output_dimensionality=768),
                )

                if response.embeddings:
                    batch_vectors = [emb.values for emb in response.embeddings if emb.values is not None]
                    all_embeddings.extend(batch_vectors)

                logger.info(
                    f"[Embedder] Finished batch {batch_num}/{total_batches} ({len(all_embeddings)} total vectors)."
                )
                success = True
                break  # Exit retry loop on success!

            except Exception as e:
                err_str = str(e).lower()
                if "429" in err_str or "quota" in err_str or "resource_exhausted" in err_str or "overloaded" in err_str:
                    wait_time = (attempt + 1) * 15  # 15s, 30s, 45s, 60s
                    logger.warning(f"[EMBEDDER] Rate limited (429/Overloaded). Retrying batch {batch_num} in {wait_time}s...")
                    if progress_callback:
                        progress_callback(batch_num, total_batches, is_rate_limited=True, wait_time=wait_time)
                    time.sleep(wait_time)
                else:
                    logger.error(f"[EMBEDDER] Embedding failed: {e}")
                    raise

        if not success:
            raise RuntimeError(f"Embedding failed after 5 attempts for batch {batch_num}")

        # 1.0s delay between batches to stay well within Gemini RPM limits
        time.sleep(1.0)

    return all_embeddings 


def embed_single(text: str) -> list[float]:
    """Embed a single query string. Used at retrieval time."""
    result = embed_chunks([text])
    return result[0]
