"""
api/routes/preprocess.py
─────────────────────────────────────────────────────────────────────────
FastAPI route for the pre-processing pipeline.
KEY DESIGN: Dual-stream SSE
─────────────────────────────────────────────────────────────────────────
The SSE stream has TWO independent sources running concurrently:

  Source A: LangGraph graph.astream() — yields {node_name: state_update}
            as each graph node completes (fast, seconds between events)
            Why? because celery progress bars only loads after node 4 (dispatch ingestion)
            before that, user should know (if datasheet was valid) | (component already exist) 

  Source B: Redis polling — reads job:{job_id} hash every 500ms
            and yields Celery progress (slower, minutes of work)

Both sources write to an asyncio.Queue. The SSE generator reads from it
and yields SSE events to the frontend. When the graph finishes (END),

Source A sends a sentinel. When Redis shows "complete"/"failed",
Source B sends a sentinel. Both sentinels must arrive before SSE closes.

Frontend receives events like:
  data: {"type": "node", "node": "check_vector_db", "status": "checking", "message": "..."}
  data: {"type": "node", "node": "validate_datasheet", "message": "✓ Datasheet Recognized..."}
  data: {"type": "progress", "step": "chunking", "message": "Chunking Datasheet...", "progress": 50}
  data: {"type": "complete", "metadata": {...}}
  data: [DONE]
"""



import asyncio
import base64
import json
import logging
from typing import Optional
import redis.asyncio as aioredis
from fastapi import APIRouter, File, Form, UploadFile, HTTPException
from fastapi.responses import StreamingResponse
from pipeline.pre_processing.graph import preprocess_graph
from pipeline.pre_processing.state import PreProcessState

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/preprocess", tags=["pre-processing"])

import os
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")


# ─── SSE Helper ───────────────────────────────────────────────────────────────
def sse(data: dict) -> str:
    """Format a dict as an SSE message."""
    return f"data: {json.dumps(data)}\n\n"


# ─── Redis Progress Poller ────────────────────────────────────────────────────

async def poll_celery_progress(job_id: str, queue: asyncio.Queue):
    """
    Poll Redis hash job:{job_id} every 500ms.
    Puts progress events into the queue until job is done or timeout.
    """
    r = aioredis.from_url(REDIS_URL, decode_responses=True)
    last_step = None
    last_progress = None
    try:
        for _ in range(360):  # max 3 minutes (360 × 500ms)
            job_data = await r.hgetall(f"job:{job_id}")
            if job_data:
                step = job_data.get("step")
                status = job_data.get("status", "running")
                progress_val = int(job_data.get("progress", 0))
                # Only emit if step or progress percentage changed
                if step != last_step or progress_val != last_progress:
                    last_step = step
                    last_progress = progress_val
                    await queue.put(("progress", {
                        "type": "progress",
                        "step": step,
                        "message": job_data.get("message", ""),
                        "progress": progress_val,
                        "status": status,
                    }))
                if status in ("complete", "failed"):
                    metadata = {}
                    if status == "complete":
                        try:
                            metadata = json.loads(job_data.get("metadata", "{}"))
                        except json.JSONDecodeError:
                            pass
                    await queue.put(("progress_done", {
                        "type": "complete" if status == "complete" else "failed",
                        "metadata": metadata,
                        "error": job_data.get("error"),
                    }))
                    return
            await asyncio.sleep(0.5)

        # Timeout
        await queue.put(("progress_done", {
            "type": "failed",
            "error": "Ingestion timed out",
        }))
    except Exception as e:
        logger.error(f"[SSE:REDIS_POLL] Error polling job {job_id}: {e}")
        await queue.put(("progress_done", {"type": "failed", "error": str(e)}))
    finally:
        await r.aclose()

# ─── LangGraph Stream Runner ──────────────────────────────────────────────────

# # Human-readable labels for each node
NODE_MESSAGES = {
    "check_vector_db":    "Checking component catalog...",
    "validate_datasheet": "Analyzing uploaded datasheet...",
    "web_search":         "Searching web for datasheet...",
    "dispatch_ingestion": "Dispatching ingestion job...",
    "poll_and_finalize":  "Finalizing onboarding...",
}

async def run_graph_stream(initial_state: PreProcessState, queue: asyncio.Queue):
    """
    Run the LangGraph graph and put node events into the queue.
    Also signals when to start Redis polling (after dispatch node).
    """
    try:
        # this is the langraph call astream that runs the graph and yeilds once after each node completes. 
        async for chunk in preprocess_graph.astream(
            initial_state, stream_mode="updates"
        ):
            # Each astream yeilds a chunk, it extracts the node name and whatever that node wrote to state. 
            for node_name, node_state in chunk.items():
                node_state = node_state or {}
                logger.info(f"[GRAPH] Node completed: {node_name}")
                event = {
                    "type": "node",
                    "node": node_name,
                    "status": node_state.get("status", ""),
                    "message": node_state.get("validation_message")
                              or NODE_MESSAGES.get(node_name, node_name),
                }
                await queue.put(("graph", event))

                # Signal to start Redis polling when dispatch completes
                if node_name == "dispatch_ingestion" and node_state.get("job_id"):
                    await queue.put(("start_polling", node_state["job_id"]))

    except Exception as e:
        logger.error(f"[GRAPH] Stream error: {e}", exc_info=True)
        await queue.put(("graph", {"type": "error", "message": str(e)}))
    finally:
        await queue.put(("graph_done", None))


# ─── Main SSE Endpoint ────────────────────────────────────────────────────────

@router.post("/onboard")
async def onboard_component(
    component_id: str = Form(...),
    component_name: str = Form(...),
    datasheet_url: Optional[str] = Form(None),
    datasheet_file: Optional[UploadFile] = File(None),
):
    """
    Start the pre-processing pipeline for a new component.
    Returns an SSE stream of agent progress events.
    Form fields:
    - component_id: unique ID (e.g., "dht22")
    - component_name: display name (e.g., "DHT22 Temperature Sensor")
    - datasheet_url: optional URL to datasheet
    - datasheet_file: optional PDF file upload
    """
    # Read PDF bytes if uploaded
    pdf_bytes: Optional[bytes] = None
    if datasheet_file and datasheet_file.content_type in ("application/pdf", "application/octet-stream"):
        pdf_bytes = await datasheet_file.read()
        logger.info(f"[PREPROCESS] Received PDF upload: {datasheet_file.filename} ({len(pdf_bytes)} bytes)")
    elif datasheet_file:
        logger.warning(f"[PREPROCESS] Unexpected file type: {datasheet_file.content_type}")
    # Build initial LangGraph state
    initial_state: PreProcessState = {
        "component_id": component_id,
        "component_name": component_name,
        "pdf_bytes": pdf_bytes,
        "pdf_base64": None,
        "datasheet_url": datasheet_url,
        "already_indexed": False,
        "datasheet_valid": False,
        "needs_web_search": False,
        "extracted_component_name": None,
        "validation_message": "",
        "found_datasheet_url": None,
        "job_id": None,
        "extracted_metadata": None,
        "status": "pending",
        "error": None,
    }
    async def event_generator():
        queue: asyncio.Queue = asyncio.Queue()
        graph_done = False
        progress_done = False
        redis_task = None

        # Launch graph in background
        # This is the single line that kicks off the entire agent 
        
        graph_task = asyncio.create_task(run_graph_stream(initial_state, queue))
        try:
            while not (graph_done and (progress_done or redis_task is None)):
                try:
                    # The SSE Generator waiting room
                    # Waits for either the graph tasks to be put in queue or redis poller 
                    kind, data = await asyncio.wait_for(queue.get(), timeout=30.0)
                except asyncio.TimeoutError:
                    # Keepalive ping to prevent SSE timeout
                    yield ": ping\n\n"
                    continue
                if kind == "graph":
                    yield sse(data)
                elif kind == "start_polling":
                    job_id = data
                    # Start Redis polling task now that we have a job_id
                    redis_task = asyncio.create_task(
                        poll_celery_progress(job_id, queue)
                    )
                    logger.info(f"[SSE] Started Redis polling for job {job_id}")
                elif kind == "progress":
                    yield sse(data)
                elif kind == "progress_done":
                    yield sse(data)
                    progress_done = True
                elif kind == "graph_done":
                    graph_done = True
        except asyncio.CancelledError:
            logger.info("[SSE] Client disconnected")
        finally:
            graph_task.cancel()
            if redis_task:
                redis_task.cancel()
        yield sse({"type": "done"})
        yield "data: [DONE]\n\n"
    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",  # Disable nginx buffering
        },
    )


# ─── Job Status Polling (non-SSE fallback) ────────────────────────────────────
@router.get("/job/{job_id}")
async def get_job_status(job_id: str):
    """Polling fallback for clients that can't use SSE."""
    r = aioredis.from_url(REDIS_URL, decode_responses=True)
    try:
        job_data = await r.hgetall(f"job:{job_id}")
        if not job_data:
            raise HTTPException(status_code=404, detail=f"Job {job_id} not found")
        return job_data
    finally:
        await r.aclose()