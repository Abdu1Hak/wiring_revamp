"""
api/routes/generate.py
─────────────────────────────────────────────────────────────────────────
Two endpoints handle the generation pipeline's HITL split:

POST /api/generate/start
  → Runs graph from N2 until interrupt() fires
  → SSE streams node events
  → Emits {type: "hitl_required", role_assignments: {...}}
  → SSE closes (graph is suspended in Redis)

POST /api/generate/confirm
  → Resumes suspended graph with user's action
  → SSE streams remaining nodes (N3 → N6)
  → Emits {type: "complete", react_flow_schema: {...}, steps: [...]}
Both use the same session_id as LangGraph thread_id so the Redis
checkpointer can stitch the two calls into one continuous graph run.
"""
import json
import logging
from typing import Literal, Optional

from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from langchain_core.runnables import RunnableConfig
from pydantic import BaseModel

from pipeline.generation.graph import get_generation_graph
from pipeline.generation.state import Generation
from langgraph.types import Command

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/generate", tags=["generation"])


# ─── Request Models ───────────────────────────────────────────────────────────
class StartRequest(BaseModel):
    session_id: str
    component_ids: list[str]
    project_scope: str
    revision_context: Optional[str] = None

class ConfirmRequest(BaseModel):
    session_id: str
    action: Literal["confirmed", "edited", "rejected"]
    role_assignments: Optional[dict] = None   # populated if action == "edited"
    reason: Optional[str] = None              # populated if action == "rejected"

# ─── SSE Helper ───────────────────────────────────────────────────────────────
def sse(data: dict) -> str:
    return f"data: {json.dumps(data)}\n\n"


NODE_MESSAGES = {
    "query_optimization": "Analyzing components and project scope...",
    "pre_compatibility":  "Running compatibility checks...",
    "rag_retrieval":      "Retrieving datasheet context...",
    "synthesize_wiring":  "Generating wiring diagram...",
    "post_check":         "Validating connections...",
}


# ─── Shared Streaming Helper ──────────────────────────────────────────────────

async def _stream_graph_events(graph_input, config: RunnableConfig): 

    graph = get_generation_graph()
    # pyrefly: ignore [missing-attribute]
    async for chunk in graph.astream( # polymorphic: dict -> state, None-> load from checkpointer, Command() -> load suspended state & inject payload as return of interrupt
        graph_input, # graph_states
        config=config, 
        stream_mode="updates"
    ):

        for node_name, node_state in chunk.items(): 

            # Langraph uses interrupt as the node when interrupt fires 
            if node_name == "__interrupt__": 
                payload = node_state[0].value
                logger.info("[GENERATE] HITL interrupt fires")
                yield sse(payload)
                return 
            
            logger.info(f"[GENERATE] Node completed: {node_name}")
            yield sse({
                "type":    "node",
                "node":    node_name,
                "status":  node_state.get("status", ""),
                "message": NODE_MESSAGES.get(node_name, node_name),
            })

            if node_state.get("status") == "complete": 
                yield sse({
                    "type":              "complete",
                    "react_flow_schema": node_state.get("react_flow_schema", {}),
                    "wiring_steps":      node_state.get("wiring_steps", []),
                    "session_id":        config["configurable"]["thread_id"],
                })
                return
            
            if node_state.get("status") == "failed":
                yield sse({"type": "failed", "error": node_state.get("error")})
                return
    
    yield sse({"type": "done"})
    yield "data: [DONE]\n\n"


# ------- POST Endpoint 1: api/generate/start --------------──────
@router.post("/start")
async def start_generation(request: StartRequest):
    """
    Kick off the generation pipeline from the beginning.
    Runs N2 (query_optimization), then suspends at HITL interrupt().
    """
    initial_state: Generation = {
        "session_id":             request.session_id,
        "component_ids":          request.component_ids,
        "project_scope":          request.project_scope,
        "revision_context":       request.revision_context,
        "existing_project_id":    None,
        "is_cached":              False,
        "role_assignments":       {},
        "missing_roles":          [],
        "unassigned_components":  [],
        "enriched_scope":         "",
        "is_aligned":             False,
        "hitl_status":            "pending",
        "hitl_user_edits":        None,
        "hitl_rejection_reason":  None,
        "component_metadata":     [],
        "pre_compat_errors":      [],
        "pre_compat_warnings":    [],
        "auto_fixed_components":  [],
        "rag_context":            {},
        "connections":            [],
        "wiring_steps":           [],
        "react_flow_schema":      None,
        "post_compat_errors":     [],
        "retry_count":            0,
        "status":                 "pending",
        "error":                  None,
    }
   
    # thread_id links this call to the /confirm call that follows
    config: RunnableConfig = {"configurable": {"thread_id": request.session_id}}
    
    return StreamingResponse(
        _stream_graph_events(initial_state, config),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )



# ------- POST Endpoint 2: api/generate/confirm --------------
@router.post("/confirm")
async def confirm_generation(request: ConfirmRequest):
    """
    Resume the suspended graph with the user's HITL decision.
    Uses the same session_id (thread_id) to find the suspended state in Redis.
    """
    config: RunnableConfig = {"configurable": {"thread_id": request.session_id}}
    resume_payload = {
        "action":           request.action,
        "role_assignments": request.role_assignments or {},
        "reason":           request.reason or "",
    }
    return StreamingResponse(
        _stream_graph_events(Command(resume=resume_payload), config),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )





# StreamingResponse 
# instead of waiting for chunks to finsih and streaming only the output json
# this keeps an HTTP connection open and streams data chunk-by-chunk in real time 
# Parameters:
# 1. content - async generator or gen that yeilds bytes/string
# 2. headers - for the http browser to run critical motions 
# 3. media - informs browser so it knows how to parse incoming stream 






