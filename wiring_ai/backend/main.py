from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List

# IMPORT DATABASE AND AI_SERVICE FUNCTIONS
from db.database import get_all_components, get_components_by_ids
from ai_service import generate_ai_wiring_plan
from compatibility import run_compatibility_check
from autofix import run_auto_fix

app = FastAPI()

# Allows frontend to call backend during development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Pydantic Model 
class GenerateProjectRequest(BaseModel):
    # Include all the feilds with its value type
    scope: str
    selectedComponents: List[str]

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