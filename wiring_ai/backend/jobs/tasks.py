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
    r.expire(f"job:{job_id}", 3600)  # 1 hour TTL



def _publish_complete(r: redis.Redis, job_id: str, metadata: dict):
    r.hset(f"job:{job_id}", mapping={
        "step": "complete",
        "message": "✓ Component onboarding complete!",
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
You are an expert hardware engineer. Extract structured electrical and pinout metadata from this component datasheet.
Return ONLY valid JSON matching this exact schema:
{{
  "name": "Full component display name",
  "category": "one of: microcontroller | sensor | actuator | display | passive | power | communication",
  "description": "One sentence technical description",
  "pins": [
    {{
      "name": "VCC",
      "type": "power",
      "voltage": 5.0,
      "required": true,
      "notes": "3.3V or 5V supply"
    }},
    {{
      "name": "DATA",
      "type": "digital",
      "voltage": 5.0,
      "required": true,
      "notes": "1-Wire data signal"
    }}
  ],
  "interface": {{
    "protocol": "one of: gpio | i2c | spi | uart | onewire | analog | passive | sub_peripheral",
    "i2c_address": "e.g. 0x27 or null"
  }},
  "power": {{
    "logic_voltage": 5.0,
    "voltage_range": [3.3, 5.0],
    "operating_current_mA": 2.5,
    "is_external_powered": false
  }},
  "constraints": [
    {{
      "type": "requires_pullup",
      "condition": "4.7kΩ pull-up resistor required on DATA pin",
      "resolution": "Add a 4.7kΩ pull-up resistor between VCC and DATA",
      "auto_fixable": false,
      "fix_component_id": null,
      "severity": "warning"
    }}
  ],
  "tags": ["temperature", "humidity", "1-Wire", "sensor"],
  "datasheet_summary": "2-3 sentence technical summary covering key specs, pin roles, and common use cases.",
  "compatible_boards": [],

  "operating_voltage": null,
  "input_voltage_range": null,
  "max_current_per_pin_mA": null,
  "max_5v_rail_mA": null,
  "max_3v3_rail_mA": null,
  "total_digital_pins": null,
  "total_analog_pins": null,
  "total_pwm_pins": null,
  "has_wifi": false,
  "has_bluetooth": false,
  "board_pins": null
}}
Rules:
- `pins`: list every pin found with its exact name and functional role. `type` MUST be one of: power | ground | digital | analog | pwm | i2c | spi | uart | onewire | passive.
  - Use `"pwm"` for pins that require hardware timer signals (servo control, buzzer tone, PWM LED channels).
  - Use `"digital"` for standard GPIO input/output pins.
  - Use `"analog"` for ADC input or DAC output pins.
  - Use `"passive"` for pins on resistors, diodes, capacitors, switches (no active logic).
  - `required`: true if pin must be connected for basic operation, false if optional.
  - `notes`: brief wiring note (pull-up needed, max voltage, polarity, etc.)
- `interface.protocol`:
  - "i2c" — uses SDA/SCL bus. Extract default 7-bit hex i2c_address (e.g. "0x27") if found in datasheet, else null.
  - "spi" — uses MOSI/MISO/SCK/CS.
  - "onewire" — uses Dallas 1-Wire or single-bus protocol (e.g. DS18B20, DHT11).
  - "analog" — purely analog sensor/input with no digital communication lines.
  - "passive" — resistor, diode, capacitor, switch, or transistor (no MCU protocol).
  - "sub_peripheral" — motor, pump, solenoid, or fan that connects via a driver IC or relay, NOT directly to MCU.
  - "gpio" — standard digital modules and sensors driven directly by MCU GPIO.
- `power`:
  - `logic_voltage`: 3.3 or 5.0 (the digital logic level it communicates at). Set to null for passives and sub_peripherals.
  - `voltage_range`: [min_voltage, max_voltage] numbers, e.g. [3.0, 5.5].
  - `operating_current_mA`: typical or max operating current draw in mA (number, e.g. 15.0).
  - `is_external_powered`: true for high-current loads (motors, heating elements, solenoids, relays, servos) that require an external battery/power supply; false for low-power sensors/logic modules powered from MCU 5V rail.
- `constraints`: include explicit circuit requirements (pull-up resistors, series resistors, flyback diodes, decoupling caps).
- `tags`: 3-6 relevant lowercase keywords.
- `Microcontroller / Board specific fields`:
  - IF AND ONLY IF `category` is "microcontroller" or "board":
    - Extract `operating_voltage` (e.g. 5.0 or 3.3), `input_voltage_range` (e.g. [7.0, 12.0]), `max_current_per_pin_mA` (e.g. 40.0), `max_5v_rail_mA` (e.g. 500.0), `max_3v3_rail_mA` (e.g. 150.0), `total_digital_pins` (e.g. 14), `total_analog_pins` (e.g. 6), `total_pwm_pins` (e.g. 6), `has_wifi`, `has_bluetooth`.
    - Extract `board_pins`: array of objects `[{"pin_id": "D0", "label": "0", "capabilities": ["digital", "uart_rx"], "voltage": 5.0, "max_current_mA": 40.0, "reserved": true, "reserved_reason": "USB Serial RX"}, ...]`.
  - For all other categories (sensors, actuators, passives, displays), leave all board fields as null.
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

        # Format power and interface cleanly
        power_dict = metadata.get("power", {})
        interface_dict = metadata.get("interface", {})
        category = metadata.get("category") or "other"

        # Auto-detect missing electrical profile for review gate
        needs_review = False
        review_notes = []
        if category not in ["passive", "platform"]:
            if not power_dict.get("voltage_range"):
                needs_review = True
                review_notes.append("Missing voltage range")
            if power_dict.get("operating_current_mA") is None and not power_dict.get("is_external_powered"):
                needs_review = True
                review_notes.append("Missing operating current (mA)")
            if not interface_dict.get("protocol"):
                needs_review = True
                review_notes.append("Missing interface protocol")

        db_params = {
            "id": id_val,
            "name": metadata.get("name") or component_id.replace("_", " ").title(),
            "category": category,
            "description": metadata.get("description") or "",
            "pins": json.dumps(metadata.get("pins", [])),
            "interface": json.dumps(interface_dict),
            "power": json.dumps(power_dict),
            "constraints": json.dumps(metadata.get("constraints", [])),
            "compatible_boards": json.dumps(metadata.get("compatible_boards", [])),
            "tags": json.dumps(metadata.get("tags", [])),
            "_needs_review": needs_review,
            "_review_notes": "; ".join(review_notes) if review_notes else None,
            "datasheet_url": datasheet_url or metadata.get("datasheet_url") or "",
            "datasheet_summary": metadata.get("datasheet_summary") or "",
        }

        engine = _get_db_engine()
        with engine.connect() as conn:
            # Upsert component record matching PostgreSQL components_table schema
            conn.execute(text("""
                INSERT INTO components (
                    id, name, category, description,
                    pins, interface, power, constraints, compatible_boards, tags,
                    _needs_review, _review_notes, datasheet_url, datasheet_summary, qdrant_indexed
                )
                VALUES (
                    :id, :name, :category, :description,
                    :pins, :interface, :power, :constraints, :compatible_boards, :tags,
                    :_needs_review, :_review_notes, :datasheet_url, :datasheet_summary, false
                )
                ON CONFLICT (id) DO UPDATE SET
                    name = EXCLUDED.name,
                    category = EXCLUDED.category,
                    description = EXCLUDED.description,
                    pins = EXCLUDED.pins,
                    interface = EXCLUDED.interface,
                    power = EXCLUDED.power,
                    constraints = EXCLUDED.constraints,
                    tags = EXCLUDED.tags,
                    _needs_review = EXCLUDED._needs_review,
                    _review_notes = EXCLUDED._review_notes,
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
                _publish_progress(r, job_id, "embedding", f"AI Rates are limited. Retrying in {wait_time}s...", 70)
            else:
                pct = 65 + int((b_num / total_b) * 20)
                _publish_progress(r, job_id, "embedding", f"Generating embeddings ({int((b_num/total_b)*100)}%)...", pct)

        embeddings = embed_chunks(texts, progress_callback=on_embed_progress)

        # ── Step 6: Upsert to Qdrant ─────────────────────────────────────────
        _publish_progress(r, job_id, "indexing", "Indexing in vector database...", 90)
        _ensure_qdrant_collection(qdrant)

        points = []
        for i, (chunk, vector) in enumerate(zip(chunks, embeddings)):
            points.append(PointStruct(
                id=str(uuid.uuid4()),
                vector=vector,
                payload={
                    "component_id": component_id,
                    "chunk_index": i,
                    "text": chunk["text"],
                    "page": chunk.get("page", 1),
                    "section": chunk.get("section", "general"),
                }
            ))

        # Batch upsert to Qdrant
        qdrant.upsert(collection_name=QDRANT_COLLECTION, points=points)
        logger.info(f"[CELERY:{job_id}] Upserted {len(points)} points to Qdrant")

        # ── Step 7: Mark Indexed in Postgres ─────────────────────────────────
        with engine.connect() as conn:
            conn.execute(
                text("UPDATE components SET qdrant_indexed = true WHERE id = :id"),
                {"id": component_id}
            )
            conn.commit()

        # ── Step 8: Complete ──────────────────────────────────────────────────
        _publish_complete(r, job_id, metadata)
        logger.info(f"[CELERY:{job_id}] ✓ Ingestion complete for {component_id}")
        return {"status": "complete", "component_id": component_id, "points_indexed": len(points)}

    except Exception as e:
        logger.error(f"[CELERY:{job_id}] Ingestion failed: {e}", exc_info=True)
        _publish_failed(r, job_id, str(e))
        raise