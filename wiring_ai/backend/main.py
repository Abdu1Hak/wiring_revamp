import time
from typing import List
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from celery.result import AsyncResult

# IMPORT DATABASE, REDIS AND CELERY TASKS
from db.database import get_all_components, get_components_by_ids
from ai_service import generate_ai_wiring_plan
from compatibility import run_compatibility_check
from autofix import run_auto_fix
from celery_app import celery_app
from tasks import lookup_component_task
from redis_client import get_cached_data

app = FastAPI()

# Allows frontend to call backend during development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Pydantic Models
class GenerateProjectRequest(BaseModel):
    scope: str
    selectedComponents: List[str]


class ComponentLookupRequest(BaseModel):
    component_name: str

# backend houses a catalog of components instead of the frontend doing it

# This is a backend route, a get request is used when the frontend (client) wants to retrieve data
@app.get("/")
def root():
    return {"message": "Wiring AI backend is running"}

# this is a backend route, a post request is used when the frontend (client) wants to send data to the backend
@app.post("/api/generate-project")
async def generate_project(request: GenerateProjectRequest): # Example of a request body parameter   
  
    # The backend is expecting json data sent to this address, where pyndantic converts it to an object
    print("SCOPE RECEIVED:", request.scope)
    print("COMPONENT IDS RECEIVED:", request.selectedComponents)

    # 1. Run Stage 2: Compatibility Check
    compat_result = await run_compatibility_check(request.selectedComponents, request.scope)
    
    # 2. Run Stage 3: Auto-Fix Engine
    autofix_result = await run_auto_fix(request.selectedComponents, compat_result)
    
    # Get the final component list after auto-fixes
    final_component_ids = autofix_result.fixed_component_list
    final_components = await get_components_by_ids(final_component_ids)
    
    # If the compatibility check halted the pipeline
    if compat_result.status == "halt":
        warnings = [d.message for d in compat_result.details if d.status in ["warn", "fail"]]
        return {
            "scope": request.scope,
            "components": await get_components_by_ids(request.selectedComponents),
            "compatResult": compat_result.model_dump(),
            "autofixResult": autofix_result.model_dump(),
            "aiResult": {
                "title": "Project Halted",
                "compatible": False,
                "compatibilitySummary": compat_result.message,
                "missingComponents": [],
                "warnings": warnings,
                "steps": [],
                "connections": []
            }
        }

    ai_result = generate_ai_wiring_plan(
        scope = request.scope, 
        selected_components=final_components,
    )
    
    # If auto-fixes were applied, inject warnings or messages
    if autofix_result.status == "fix":
        ai_result.setdefault("warnings", [])
        for fix in autofix_result.fixes_applied:
            ai_result["warnings"].append(f"Auto-fixed: {fix.reason} ({fix.explanation})")

    return {
        "scope": request.scope, 
        "components": final_components, 
        "compatResult": compat_result.model_dump(),
        "autofixResult": autofix_result.model_dump(),
        "aiResult": ai_result,    
    }


@app.get("/api/components")
async def components():
    # get_all_components is now async — we must await it
    return await get_all_components()


# ==============================================================================
# FASTAPI + REDIS + CELERY EXCHANGE ENDPOINTS (main.py)
# ==============================================================================
# HOW THE 3-STEP EXCHANGE WORKS:
#
# STEP 1: POST /components/lookup (FastAPI checks Redis first)
#   - User submits component name.
#   - FastAPI reads Redis RAM (`get_cached_data`).
#   - If Redis HAS data ("CACHE HIT"): Returns result in < 2ms! (No DB or Celery needed).
#   - If Redis DOES NOT HAVE data ("CACHE MISS"):
#     - FastAPI calls `lookup_component_task.delay(name)`.
#     - This drops a task ticket into Redis broker and returns `{"status": "pending", "task_id": "..."}` in < 1ms.
#
# STEP 2: CELERY WORKER (Runs in background Terminal 2)
#   - Worker sees task ticket in Redis broker, queries PostgreSQL, stores JSON in Redis,
#     and writes status="SUCCESS" to Redis result backend.
#
# STEP 3: GET /jobs/{task_id} (Frontend Polls Status)
#   - React frontend polls `GET /jobs/{task_id}` every 500ms.
#   - FastAPI uses `AsyncResult(task_id)` to query Redis for current task state.
#   - When state == "SUCCESS", returns finished data to frontend!
# ==============================================================================


@app.post("/components/lookup")
async def lookup_component_endpoint(request: ComponentLookupRequest):
    """
    Component Lookup Endpoint:
    Demonstrates Redis Caching -> Celery Fallback -> Background Worker Execution.
    """
    normalized_name = request.component_name.strip().lower()
    redis_key = f"component_lookup:{normalized_name}"

    # Measure exact time taken to check Redis
    start_time = time.perf_counter()
    cached_data = await get_cached_data(redis_key)
    elapsed_ms = round((time.perf_counter() - start_time) * 1000, 2)

    # PATH A: REDIS CACHE HIT (< 2ms response time)
    if cached_data:
        return {
            "status": "complete",
            "source": "redis",
            "elapsed_ms": elapsed_ms,
            "data": {
                "category": cached_data.get("category", "N/A"),
                "description": cached_data.get("description", "")
            }
        }

    # PATH B: REDIS CACHE MISS -> DISPATCH TASK TO CELERY BROKER (< 1ms dispatch time)
    # `.delay()` sends a JSON task ticket to Redis without blocking FastAPI!
    task = lookup_component_task.delay(normalized_name)

    return {
        "status": "pending",
        "source": "celery",
        "task_id": task.id,
        "elapsed_ms": elapsed_ms
    }


@app.get("/jobs/{task_id}")
def get_job_status(task_id: str):
    """
    Poll Endpoint for Celery Task State:
    Queries Redis Result Backend for status (PENDING -> STARTED -> SUCCESS / FAILURE).
    """
    # AsyncResult checks Redis for task_id status
    task_result = AsyncResult(task_id, app=celery_app)
    response = {
        "task_id": task_id,
        "status": task_result.status,  # PENDING, STARTED, SUCCESS, FAILURE
    }

    if task_result.status == "SUCCESS":
        response["result"] = task_result.result
    elif task_result.status == "FAILURE":
        response["error"] = str(task_result.result)

    return response