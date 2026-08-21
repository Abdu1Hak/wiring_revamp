"""
jobs/tasks.py
─────────────────────────────────────────────────────────────────────────
PURPOSE: Heavy async execution — all I/O-bound work lives here.
Celery does NOT natively support asyncio. All clients here are SYNCHRONOUS:
- redis.Redis (sync)
- QdrantClient (sync)  
- sqlalchemy Engine (sync, separate from FastAPI's async engine)
- google.generativeai (sync)
The LangGraph agent NEVER calls this directly.
It calls the MCP tool → which dispatches THIS task → returns job_id.
"""

import os 
import asyncio
import logging
from datetime import datetime, timezone 
import json 
from google import genai
from google.genai import types 
import uuid 
import time 

from jobs.celery_app import celery_app
from rag.chunker import chunk_text
from rag.embedder import embed_chunks 
from rag.ingestor import extract_text_from_pdf_bytes

import redis
from db.database import get_component_by_name
from redis_cache.redis_client import set_cached_data
from sqlalchemy import create_engine, text
from dotenv import load_dotenv
from qdrant_client import QdrantClient
from qdrant_client.models import (
    Distance,
    VectorParams,
    PointStruct,
)
import asyncio
from db.database import delete_component_by_id

QDRANT_HOST = os.getenv("QDRANT_HOST", "localhost")
QDRANT_PORT = int(os.getenv("QDRANT_PORT", "6333"))
QDRANT_API_KEY = os.getenv("QDRANT_API_KEY", None)

logger = logging.getLogger(__name__)

# ------ Sync Clients ------------
# Your FastAPI will support an async db engine, whereas celery live workers only respond to sync engines 

from redis_cache.redis_client import get_redis_client
client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

def _get_qdarnt_client() -> QdrantClient:
    return QdrantClient(
        host=QDRANT_HOST,
        port=QDRANT_PORT,
        api_key=QDRANT_API_KEY,
        https=False,
        timeout=30,
    )

_qdrant_client = QdrantClient(
    host=QDRANT_HOST,
    port=QDRANT_PORT,
    api_key=QDRANT_API_KEY,
    https=False,
    timeout=30,
)

def _get_db_engine():
    url = os.getenv("DATABASE_URL")
    # remove +asyncpg with sync engine 
    # pyrefly: ignore [missing-attribute]
    sync_url = url.replace("+asyncpg", "")
    return create_engine(sync_url, pool_pre_ping=True, echo=False)

# In tasks.py:
def _get_sync_redis_client() -> redis.Redis:
    return redis.Redis.from_url(
        os.getenv("REDIS_URL", "redis://:redis_password@localhost:6379/0"),
        decode_responses=True
    )


# -------- Progress Publisher -------------

QDRANT_COLLECTION = "datasheets"

def _publish_progress(r: redis.Redis, job_id: str, step: str, message: str, progress: int ):
    """ Write progress to Redis Hash - Polled by FastAPI SSE Endpoint"""

    r.hset(f"job:{job_id}", mapping={
        "step": step, 
        "message": message, 
        "progress": str(progress),
        "status": "running",
        "updated_at": datetime.now(timezone.utc).isoformat(), 
    })
    r.expire(f"job:{job_id}", 3600) # 1 hour
    logger.info(f"[Celery: {job_id}] {progress}% - {message}")

def _publish_complete(r: redis.Redis, job_id: str, metadata: dict):
    r.hset(f"job:{job_id}", mapping={
        "step": "complete",
        "message": "Component successfully onboarded",
        "progress": "100",
        "status": "complete",
        "metadata": json.dumps(metadata),
        "updated_at": datetime.now().isoformat(),
    })
    r.expire(f"job:{job_id}", 3600)


def _publish_failed(r: redis.Redis, job_id: str, error: str):
    r.hset(f"job:{job_id}", mapping={
        "step": "failed",
        "message": f"Onboarding failed: {error}",
        "progress": "0",
        "status": "failed",
        "error": error,
        "updated_at": datetime.now().isoformat(),
    })
    r.expire(f"job:{job_id}", 3600)


# ─── Metadata Extraction via Gemini ──────────────────────────────────────────

METADATA_PROMPT = """\
You are a hardware engineering assistant. Extract structured metadata from this datasheet.
Return ONLY valid JSON matching this exact schema:
{{
  "name": "Full component display name",
  "category": "one of: microcontroller | sensor | actuator | display | passive | power | communication",
  "description": "One sentence technical description",
  "pins": [
    {{
      "name": "VCC",
      "type": "power",
      "description": "3.3V or 5V supply"
    }},
    {{
      "name": "DATA",
      "type": "digital",
      "description": "1-Wire data signal"
    }}
  ],
  "power": {{
    "operating_voltage": "3.3-5V",
    "current_mA": 2.5
  }},
  "constraints": [
    {{
      "type": "requires_pullup",
      "description": "4.7kΩ pull-up resistor required on DATA pin"
    }}
  ],
  "tags": ["temperature", "humidity", "1-Wire", "sensor"],
  "datasheet_summary": "2-3 sentence technical summary covering key specs, pin roles, and common use cases.",
  "compatible_boards": []
}}
Rules:
- `pins`: list every pin found in the datasheet with its pin number and exact functional role (e.g. "Pin 1 (Anode E)", "Pin 6 (Digit 4 Common Cathode)"). Do NOT list generic names like "Pin 1" or "1". `type` is one of: power | digital | analog | pwm | i2c | spi | uart | ground
- `power`: extract operating voltage range or Forward Voltage Vf as a string (e.g. "2.05-2.6V" or "3.3-5V") and max/typical DC current draw in mA (e.g. 25)
- `constraints`: ONLY include if the datasheet explicitly mentions a requirement (pull-up, current-limiting resistor, decoupling cap, etc.)
- `tags`: 3-6 relevant keywords
- `compatible_boards`: leave as empty list — unknown from datasheet alone
- For microcontrollers/boards: add a "board_info" key with total_digital_pins, total_analog_pins, total_pwm_pins, has_wifi, has_bluetooth
Datasheet text:
{text}
"""
# pyrefly: ignore [bad-function-definition]
def _extract_metadata_with_gemini(raw_text: str, component_id: str, r: redis.Redis = None, job_id: str = None) -> dict: 
    """ Use Gemini to extract metadata from datasheet text """
    prompt = METADATA_PROMPT.format(text=raw_text[:40000])
    backoffs = [10, 20, 30, 45, 60]

    last_error = None
    for attempt, wait_time in enumerate(backoffs):
        try: 
            response = client.models.generate_content(
                model="gemini-3.5-flash-lite",
                contents=prompt,
                config=types.GenerateContentConfig(
                    response_mime_type="application/json"
                ),
            )

            if response.text:
                clean_text = response.text.strip()
                if clean_text.startswith("```"):
                    clean_text = clean_text.strip("`").removeprefix("json").strip()
                metadata = json.loads(clean_text)
                metadata["component_id"] = component_id
                return metadata
            break
        except Exception as e:
            last_error = e
            err_str = str(e).lower()
            if "429" in err_str or "quota" in err_str or "overloaded" in err_str or "resource_exhausted" in err_str:
                logger.warning(f"[Metadata Extraction] Rate limited (attempt {attempt+1}/{len(backoffs)}). Retrying in {wait_time}s...")
                if r and job_id:
                    _publish_progress(r, job_id, "rate_limited", f"AI Rates are limited. Retrying in {wait_time}s...", 35)
                time.sleep(wait_time)
            else:
                logger.error(f"[Metadata Extraction] Failed for {component_id}: {e}")
                raise e

    raise RuntimeError(f"Metadata extraction failed for '{component_id}' after retries: {last_error}")
        
    

# --------- Qdrant Setup ------------------------

def _ensure_qdrant_collection(client: QdrantClient):
    collection_names = [c.name for c in client.get_collections().collections]
    if QDRANT_COLLECTION not in collection_names:
        try:
            client.create_collection(
                collection_name=QDRANT_COLLECTION,
                vectors_config=VectorParams(size=768, distance=Distance.COSINE),
            )
            logger.info(f"[CELERY] Created Qdrant collection: {QDRANT_COLLECTION}")
        except Exception as e:
            if "already exists" not in str(e).lower():
                raise


# ------- MAIN CELERY TASK ------------------------


@celery_app.task(name="jobs.tasks.ingest_datasheet_task", bind=True, max_retries=5, default_retry=30,)
# pyrefly: ignore [bad-unpacking]
def ingest_datasheet_task(self, component_id:str, job_id: str, pdf_path:str|None=None, datasheet_url: str | None = None,):
    """
    Full datasheet ingestion pipeline:
    1. Load PDF → extract text
    2. Extract metadata with Gemini → seed PostgreSQL
    3. Chunk text
    4. Embed chunks (Gemini text-embedding-004)
    5. Upsert into Qdrant
    6. Update component record (qdrant_indexed=True)
    Progress is published to Redis hash: job:{job_id}
    """

    r = _get_sync_redis_client()
    qdrant = _get_qdarnt_client()

    try:
        # ── Step 1: Load / Fetch PDF ─────────────────────────────────────────
        _publish_progress(r, job_id, "loading", "Loading datasheet...", 10)
        pdf_bytes: bytes | None = None
        if pdf_path and os.path.exists(pdf_path):
            with open(pdf_path, "rb") as f:
                pdf_bytes = f.read()
            logger.info(f"[CELERY:{job_id}] Loaded PDF from temp path ({len(pdf_bytes)} bytes)")
        elif datasheet_url:
            import httpx
            _publish_progress(r, job_id, "fetching", "Fetching datasheet from web...", 15)
            response = httpx.get(datasheet_url, follow_redirects=True, timeout=30)
            response.raise_for_status()
            pdf_bytes = response.content
            logger.info(f"[CELERY:{job_id}] Downloaded PDF from URL ({len(pdf_bytes)} bytes)")
        else:
            raise ValueError("Neither pdf_path nor datasheet_url provided")

        # ── Step 2: Extract Text ─────────────────────────────────────────────
        _publish_progress(r, job_id, "extracting", "Extracting text from datasheet...", 25)
        raw_text = extract_text_from_pdf_bytes(pdf_bytes)
        if not raw_text.strip():
            raise ValueError("PDF contained no extractable text (may be image-based)")

        # ── Step 3: Extract Metadata → Seed PostgreSQL ───────────────────────
        _publish_progress(r, job_id, "analyzing", "Analyzing component metadata...", 35)
        metadata = _extract_metadata_with_gemini(raw_text, component_id, r, job_id)
        # Prepare clean parameters for INSERT into components table
        id_val = metadata.get("id") or metadata.get("component_id") or component_id

        voltage_min = metadata.get("voltage_min")
        voltage_max = metadata.get("voltage_max")
        if voltage_min is None and "power" in metadata and isinstance(metadata["power"], dict):
            v_str = str(metadata["power"].get("operating_voltage", ""))
            import re
            nums = [float(n) for n in re.findall(r"\d+\.?\d*", v_str)]
            if len(nums) >= 2:
                voltage_min, voltage_max = nums[0], nums[1]
            elif len(nums) == 1:
                voltage_min, voltage_max = nums[0], nums[0]

        current_mA = metadata.get("current_mA")
        if current_mA is None and "power" in metadata and isinstance(metadata["power"], dict):
            current_mA = metadata["power"].get("current_mA")

        pin_count = metadata.get("pin_count")
        if pin_count is None and "pins" in metadata and isinstance(metadata["pins"], list):
            pin_count = len(metadata["pins"])

        requires_resistor = metadata.get("requires_resistor", False)
        requires_pullup = metadata.get("requires_pullup", False)
        if "constraints" in metadata and isinstance(metadata["constraints"], list):
            for c in metadata["constraints"]:
                c_str = str(c).lower()
                if "resistor" in c_str:
                    requires_resistor = True
                if "pullup" in c_str or "pull-up" in c_str:
                    requires_pullup = True

        db_params = {
            "id": id_val,
            "name": metadata.get("name") or component_id.replace("_", " ").title(),
            "category": metadata.get("category") or "other",
            "description": metadata.get("description") or "",
            "pins": json.dumps(metadata.get("pins", [])),
            "power": json.dumps(metadata.get("power", {})),
            "constraints": json.dumps(metadata.get("constraints", [])),
            "compatible_boards": json.dumps(metadata.get("compatible_boards", [])),
            "tags": json.dumps(metadata.get("tags", [])),
            "operating_voltage": float(voltage_min) if voltage_min is not None else None,
            "datasheet_url": datasheet_url or metadata.get("datasheet_url") or "",
            "datasheet_summary": metadata.get("datasheet_summary") or "",
        }

        engine = _get_db_engine()
        with engine.connect() as conn:
            # Upsert component record matching PostgreSQL components_table schema
            conn.execute(text("""
                INSERT INTO components (
                    id, name, category, description,
                    pins, power, constraints, compatible_boards, tags,
                    operating_voltage, datasheet_url, datasheet_summary, qdrant_indexed
                )
                VALUES (
                    :id, :name, :category, :description,
                    :pins, :power, :constraints, :compatible_boards, :tags,
                    :operating_voltage, :datasheet_url, :datasheet_summary, false
                )
                ON CONFLICT (id) DO UPDATE SET
                    name = EXCLUDED.name,
                    category = EXCLUDED.category,
                    description = EXCLUDED.description,
                    pins = EXCLUDED.pins,
                    power = EXCLUDED.power,
                    constraints = EXCLUDED.constraints,
                    tags = EXCLUDED.tags,
                    operating_voltage = EXCLUDED.operating_voltage,
                    datasheet_url = EXCLUDED.datasheet_url,
                    datasheet_summary = EXCLUDED.datasheet_summary
            """), db_params)
            conn.commit()
        # ── Step 4: Chunk Text ───────────────────────────────────────────────
        _publish_progress(r, job_id, "chunking", "Chunking datasheet...", 50)
        chunks = chunk_text(raw_text, component_id)
        if not chunks:
            raise ValueError("Chunking produced no output")
        # ── Step 5: Embed Chunks ─────────────────────────────────────────────
        _publish_progress(r, job_id, "embedding", "Generating embeddings (0%)...", 65)
        texts = [c["text"] for c in chunks]

        def on_embed_progress(b_num, total_b, is_rate_limited=False, wait_time=0):
            if is_rate_limited:
                _publish_progress(r, job_id, "rate_limited", f"AI Rates are limited. Retrying in {wait_time}s...", 65)
            else:
                pct = 65 + int((b_num / total_b) * 20)  # 65% to 85%
                _publish_progress(r, job_id, "embedding", f"Generating embeddings ({b_num}/{total_b})...", pct)

        vectors = embed_chunks(texts, progress_callback=on_embed_progress)
        # ── Step 6: Upsert into Qdrant ───────────────────────────────────────
        _publish_progress(r, job_id, "storing", "Storing in vector database...", 80)
        _ensure_qdrant_collection(qdrant)
        points = [
            PointStruct(
                id=str(uuid.uuid4()),
                vector=vector,
                payload={
                    "component_id": chunk["component_id"],
                    "chunk_index": chunk["chunk_index"],
                    "text": chunk["text"],
                    "char_start": chunk["char_start"],
                    "char_end": chunk["char_end"],
                    "component_name": metadata.get("name", component_id),
                    "category": metadata.get("category", "unknown"),
                }
            )
            for chunk, vector in zip(chunks, vectors)
        ]
        qdrant.upsert(collection_name=QDRANT_COLLECTION, points=points)
        logger.info(f"[CELERY:{job_id}] Upserted {len(points)} vectors into Qdrant")
        # ── Step 7: Mark as Indexed in PostgreSQL ────────────────────────────
        _publish_progress(r, job_id, "updating_catalog", "Updating component catalog...", 95)
        with engine.connect() as conn:
            conn.execute(text(
                "UPDATE components SET qdrant_indexed = true WHERE id = :id"
            ), {"id": component_id})
            conn.commit()
        # Clean up temp file
        if pdf_path and os.path.exists(pdf_path):
            os.remove(pdf_path)
        # ── Complete ─────────────────────────────────────────────────────────
        _publish_complete(r, job_id, metadata)
        logger.info(f"[CELERY:{job_id}] ✓ Ingestion complete for {component_id}")
        return {"status": "complete", "component_id": component_id, "chunks": len(chunks)}
    
    
    except Exception as exc:
        logger.error(f"[CELERY:{job_id}] ✗ Ingestion failed: {exc}", exc_info=True)
        err_str = str(exc).lower()
        if "429" in err_str or "quota" in err_str or "overloaded" in err_str or "resource_exhausted" in err_str:
            _publish_progress(r, job_id, "rate_limited", f"AI Rates are limited. Retrying in 30s...", 0)
        else:
            _publish_failed(r, job_id, str(exc))

        # Automatic Rollback: delete inindexed orphan row from PostgreSQL if pipeline failed 
        try: 
            # how to call async function inside a synchronous celery agent
            asyncio.run(delete_component_by_id(component_id))
            logger.info(f"[CLEANUP] Purged PostgreSQL and Qdrant entries for '{component_id}'")
        
        except Exception as cleanup_err:
            logger.warning(f"[CLEANUP] Failed to purge '{component_id}': {cleanup_err}")


        raise self.retry(exc=exc, countdown=30)