"""
STATES

Design notes:
- `pdf_bytes` is bytes: kept in-memory only during the agent run (not stored in Redis)
- `pdf_base64` is the serialized form passed to the MCP tool (bytes aren't JSON-serializable)
- `sse_events` accumulates events for the FastAPI SSE endpoint to yield
"""
from typing import TypedDict, Optional 

class PreProcessState(TypedDict):

    # ─── Input (set by FastAPI before invoking graph) ─────────────────────────
    component_id: str           # e.g., "dht22"
    component_name: str         # e.g., "DHT22 Temperature Sensor"
    pdf_bytes: Optional[bytes]  # raw bytes from frontend upload
    pdf_base64: Optional[str]   # base64-encoded PDF for MCP tool call
    datasheet_url: Optional[str]  # URL if user typed one in

    # ─── check_vector_db_node output ──────────────────────────────────────────
    already_indexed: bool        # skip all ingestion if True

    # ─── validate_datasheet_node output ───────────────────────────────────────
    datasheet_valid: bool        # True if uploaded PDF is a real datasheet
    needs_web_search: bool       # True if no PDF or invalid PDF
    extracted_component_name: Optional[str]   # LLM-extracted name from PDF
    validation_message: str      # Human-readable result for frontend

    # ─── web_search_node output ───────────────────────────────────────────────
    found_datasheet_url: Optional[str]   # URL found by Tavily search

    # ─── dispatch_ingestion_node output ───────────────────────────────────────
    job_id: Optional[str]        # Celery task ID (also the Redis key prefix)

    # ─── finalize_node output ────────────────────────────────────────────────
    extracted_metadata: Optional[dict]  # metadata Celery extracted from datasheet
    
    # ─── Control ─────────────────────────────────────────────────────────────
    status: str    # "checking"|"validating"|"searching"|"dispatched"|"complete"|"failed"
    error: Optional[str]
