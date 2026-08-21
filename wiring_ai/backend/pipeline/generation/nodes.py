""" ----------------------------------
# GENERATION NODES
# ? nodes. Each has ONE job. Each reads state, does work, returns updated state. 

1. project_exist() 
2. query_optimization() 
3. compatibility_check() 
4. rag_search()  
5. synthesize_wiring_node() 
 ----------------------------------
"""

from langgraph.types import interrupt
import logging 
import os 
import json 
import asyncio 
from pipeline.generation.state import Generation
from db.database import get_components_by_ids
from google import genai
from google.genai import types

logger = logging.getLogger(__name__)

# ---------- HELPER ----------------
def gemini_model():
    return genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

"""
# ---------- NODE 1: DOES PROJECT EXIST? -----------------------
async def project_exist(state: Generation):

    
    Because the app can support more than one projects in different directories. 
    check through other projects components to see if there is a match  
    
    # it really isnt a priority at the moment - focus on creating a successful project first
    return {} 
"""

# ----------- NODE 2: QUERY TRANSLATION ---------------------------


ROLE_ASSIGNMENT_PROMPT = """\
You are an electronics engineering assistant helping design a wiring diagram.
The user wants to build this project:
\"\"\"{scope}\"\"\"
They have selected these components:
{component_list}
Your job:
1. Assign each selected component a clear, concise role within THIS specific project.
2. Identify any components the project CRITICALLY NEEDS to function but are NOT selected (only if explicitly required by the user's description).
3. Identify any selected components that have NO logical role in this project (e.g. buzzers, shift registers, or sensors not mentioned in the scope).
4. Rewrite the project scope to be technically precise and complete.
Respond ONLY with valid JSON matching this exact schema:
{{
  "is_aligned": true,
  "role_assignments": {{
    "<component_id>": "<role description — specific to this project>"
  }},
  "missing_roles": [
    {{
      "role": "<what is missing>",
      "reason": "<why it is strictly needed for this specific project>",
      "suggestion": "<e.g. HC-SR04, Push Button, etc.>"
    }}
  ],
  "unassigned_components": [
    {{
      "component_id": "<id>",
      "reason": "<why this component has no purpose in the described project>"
    }}
  ],
  "enriched_scope": "<technically precise rewrite of the project scope>"
}}
Critical Rules:
- "is_aligned" is true ONLY if: every selected component has a real role AND missing_roles is empty AND unassigned_components is empty.
- DO NOT invent or assume missing components (such as proximity sensors, buttons, or displays) unless the user's project scope explicitly asks for that behavior. If the user asks for a simple servo lid opener, do not demand a proximity sensor!
- Be aggressive with "unassigned_components": if a component (like a buzzer, shift register, or display) is selected but has zero purpose in the user's described scope, flag it as unassigned!
- Be specific in role descriptions (e.g., "Actuator: Rotates 0-90° via PWM to lift lid").
"""



async def query_optimization(state: Generation): 
    """
    N2: Assigns role to scope, detects mismatches, enriches scope 
    Uses LangGraph interrupt() to surface results for user confirmation (HITL)
    """  

    state["status"] = "query_optimizing"

    scope = state["project_scope"]
    components_ids = state["component_ids"]
    
    component_list = "\n".join(f"- {cid}" for cid in components_ids)

    # Initialize default fallbacks
    role_assignments = {}
    missing_roles = []
    unassigned_components = []
    enriched_scope = scope
    is_aligned = False

    # Inject rejection feedback if user rejected and revised
    retry_note = ""
    if state.get("hitl_rejection_reason"):
        retry_note = (
            f"\n\nNote from user: {state['hitl_rejection_reason']}\n"
            "Please revise your role assignments accordingly."
        )

    prompt = ROLE_ASSIGNMENT_PROMPT.format(
        scope=scope + retry_note,
        component_list=component_list,
    )

    try:
        model = gemini_model()
        response = await model.aio.models.generate_content(
            model="gemini-3.5-flash-lite", 
            contents=prompt, 
            config=types.GenerateContentConfig(response_mime_type="application/json")
        )
        if not response or not response.text:
            raise ValueError("Empty or invalid response from Gemini model gemini-3.5-flash-lite")

        result = json.loads(response.text)

        logger.info(f"[N2] Model result: {result}")

        role_assignments = result.get("role_assignments", {})
        missing_roles = result.get("missing_roles", [])
        unassigned_components   = result.get("unassigned_components", [])
        enriched_scope          = result.get("enriched_scope", scope)
        is_aligned              = result.get("is_aligned", False)

        logger.info(
            f"[N2] Roles assigned: {len(role_assignments)} | "
            f"Missing: {len(missing_roles)} | "
            f"Unassigned: {len(unassigned_components)} | "
            f"Aligned: {is_aligned}"
        )
    except Exception as e:
        logger.error(f"[N2] LLM call failed: {e}")
        state["status"] = "failed"
        state["error"] = f"Role Assignment failed: {str(e)}"
        return state

    # HITL - Suspend graph, surface to user 
    # interrupt() pauses execution here and returns payload to sse 
    # execution resumes from this exact line once user responds 
    
    
    user_response: dict = interrupt({
        "type": "hitl_required",
        "role_assignments": role_assignments, 
        "missing_roles": missing_roles, 
        "unassigned_components": unassigned_components,
        "enriched_scope":        enriched_scope,
        "is_aligned":            is_aligned,
    })

    # - Resume: Process User's response 
    action = user_response.get("action") 

    # action maps 
    if action == "rejected": 
        # User disagreed — re-run with their feedback reason
        state["hitl_rejection_reason"] = user_response.get("reason", "")
        state["hitl_status"] = "rejected"
        logger.info(f"[N2] User rejected. Re-running with feedback: {state['hitl_rejection_reason']}")
        return await query_optimization(state)
    
    elif action == "edited": 
        final_assignments = user_response.get("role_assignments", role_assignments)
        state["hitl_user_edits"] = final_assignments
        state["hitl_status"] = "edited"
        logger.info("[N2] User edited something")
    
    else: 
        # confirmed 
        final_assignments = role_assignments
        state["hitl_status"] = "confirmed" 
    
    # Node states 
    # pyrefly: ignore [bad-assignment]
    state["role_assignments"]       = final_assignments
    state["missing_roles"]          = missing_roles
    state["unassigned_components"]  = unassigned_components
    state["enriched_scope"]         = enriched_scope
    state["is_aligned"]             = is_aligned
    state["status"]                 = "hitl_complete"

    return state 



