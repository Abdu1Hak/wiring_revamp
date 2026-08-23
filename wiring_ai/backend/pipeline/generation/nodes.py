""" ----------------------------------
# GENERATION NODES
# Nodes. Each has ONE job. Each reads state, does work, returns updated state. 

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
You are an expert electronics and embedded systems engineer.
Analyze the user's project scope and selected hardware batch.

Project Scope:
\"\"\"{scope}\"\"\"

Selected Hardware Batches:
{component_list}

Think step-by-step through the structured analysis first, then generate the JSON output:

1. "analysis":
   - "explicit_scope_items": List every hardware part, actuator, sensor, and power source explicitly mentioned in the scope text.
   - "unmentioned_selected": List any selected components that were NOT requested in the scope and have zero purpose in this project (e.g. shift registers, buzzers, or extra sensors).
   - "quantity_comparison": For each required component, compare scope count vs selected count.
   - "voltage_evaluation": If an adjustable DC power supply / battery is selected, check if its configured voltage is appropriate for the actuators and circuit in the scope (e.g. 6V/12V motors or high-load servos require 6V-12V power).
   - "electrical_necessities": Check if selected components strictly require an intermediary driver (e.g. H-Bridge), dedicated external power source, or essential passive companions (e.g. 220Ω–330Ω current-limiting resistor for a bare LED, 4.7kΩ pull-up resistor for DS18B20 OneWire sensors, or flyback protection).

2. "role_assignments": Assign a concise, technically specific role to each valid component instance (use indexed keys for multi-unit: "servo_1", "servo_2", "arduino_uno_1", "arduino_uno_2", etc.).

3. "categorized_roles": If components are divided into board categories (e.g. Board #1, Board #2), group the assigned roles by board category. If only 1 board category exists, output 1 unified category.

4. "quantity_adjustments": For any required component where selected quantity != scope count, record the difference. (Do not put these in missing_roles or unassigned_components).

5. "voltage_adjustments": If an adjustable power supply / battery is selected but its configured voltage does not match the circuit/motor requirements in the scope (e.g. configured at 5V for 6V-12V motors), suggest the recommended voltage (e.g. "7.4V" or "12V") and reason.

6. "missing_roles": List any component explicitly mentioned in the scope OR strictly required for electrical safety and circuit operation (e.g. motor driver, external power supply, 220Ω current-limiting resistor for bare LEDs, or 4.7kΩ pull-up for DS18B20) where 0 units are selected.

7. "unassigned_components": List any components from "unmentioned_selected" that have no purpose in this scope. Do NOT invent hypothetical uses (e.g. do NOT rationalize a shift register as 'pin expansion').

8. "enriched_scope": A technically precise rewrite of the scope detailing hardware topology, exact quantities, interfaces, and pin/logic requirements.

Respond ONLY with valid JSON matching this schema:
{{
  "analysis": {{
    "explicit_scope_items": ["..."],
    "unmentioned_selected": ["..."],
    "quantity_comparison": ["..."],
    "voltage_evaluation": ["..."],
    "electrical_necessities": ["..."]
  }},
  "is_aligned": true,
  "role_assignments": {{
    "<instance_key>": "<specific role description>"
  }},
  "categorized_roles": [
    {{
      "board_id": "arduino_uno_1",
      "board_name": "Arduino Uno (Board #1)",
      "roles": {{
        "<instance_key>": "<specific role description>"
      }}
    }}
  ],
  "quantity_adjustments": [
    {{
      "component_id": "<id>",
      "selected_quantity": 2,
      "recommended_quantity": 4,
      "reason": "<reason>"
    }}
  ],
  "voltage_adjustments": [
    {{
      "component_id": "dc_power_supply",
      "current_voltage": "5V",
      "recommended_voltage": "7.4V",
      "reason": "<clear explanation of why this voltage is recommended for the load>"
    }}
  ],
  "missing_roles": [
    {{
      "role": "<functional category>",
      "reason": "<reason>",
      "suggestion": "<part name>"
    }}
  ],
  "unassigned_components": [
    {{
      "component_id": "<id>",
      "reason": "<reason>"
    }}
  ],
  "enriched_scope": "<technically precise rewrite of scope>"
}}
"""



async def query_optimization(state: Generation): 
    """
    N2: Assigns role to scope, detects mismatches, quantity & voltage adjustments, enriches scope 
    Uses LangGraph interrupt() to surface results for user confirmation (HITL)
    """  

    state["status"] = "query_optimizing"

    scope = state["project_scope"]
    component_quantities = state.get("component_quantities", {})
    component_configs = state.get("component_configs", {}) or {}
    board_categories = state.get("board_categories") or []
    
    # Format list of hardware: if board_categories provided, group by category
    if board_categories and len(board_categories) > 1:
        category_blocks = []
        for b_idx, b in enumerate(board_categories):
            b_title = b.get("board_name") or f"Board #{b_idx + 1}"
            b_comps = b.get("components") or {}
            b_configs = b.get("configs") or {}
            lines = []
            for cid, quant in b_comps.items():
                if quant > 0:
                    cfg = b_configs.get(cid, {})
                    cfg_str = f" (Configured Voltage: {cfg.get('voltage')})" if cfg.get("voltage") else ""
                    lines.append(f"  - {cid} (Quantity: {quant}{cfg_str})")
            if lines:
                category_blocks.append(f"[{b_title}]:\n" + "\n".join(lines))
        component_list = "\n\n".join(category_blocks) if category_blocks else "(No components selected)"
    else:
        # Standard flat format
        comp_lines = []
        for comp_id, quant in component_quantities.items():
            if quant > 0:
                config = component_configs.get(comp_id, {})
                config_str = ""
                voltages = config.get("voltages")
                if voltages and isinstance(voltages, list):
                    if len(voltages) == 1:
                        config_str = f", Configured Voltage: {voltages[0]}"
                    else:
                        v_parts = [f"Unit #{i+1} Voltage: {v}" for i, v in enumerate(voltages[:quant])]
                        config_str = f", {', '.join(v_parts)}"
                elif config.get("voltage"):
                    config_str = f", Configured Voltage: {config['voltage']}"
                comp_lines.append(f"- {comp_id} (Quantity: {quant}{config_str})")
        component_list = "\n".join(comp_lines) or "(No components selected)"

    # Initialize default fallbacks
    role_assignments = {}
    categorized_roles = []
    missing_roles = []
    unassigned_components = []
    quantity_adjustments = []
    voltage_adjustments = []
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

        role_assignments           = result.get("role_assignments", {})
        categorized_roles          = result.get("categorized_roles", [])
        missing_roles              = result.get("missing_roles", [])
        unassigned_components      = result.get("unassigned_components", [])
        quantity_adjustments       = result.get("quantity_adjustments", [])
        voltage_adjustments        = result.get("voltage_adjustments", [])
        enriched_scope             = result.get("enriched_scope", scope)
        is_aligned                 = result.get("is_aligned", False)

        # ─── Golden Rule: If a component has a quantity adjustment (or is selected),
        # no other alert (unassigned_components or missing_roles) can occur on that component.
        def _norm(s: str) -> str:
            return s.lower().replace("-", "_").replace(" ", "_").strip()

        qa_comp_ids = {_norm(qa.get("component_id", "")) for qa in quantity_adjustments if qa.get("component_id")}
        va_comp_ids = {_norm(va.get("component_id", "")) for va in voltage_adjustments if va.get("component_id")}
        selected_comp_ids = {_norm(cid) for cid, q in component_quantities.items() if q > 0}
        protected_ids = qa_comp_ids | va_comp_ids | selected_comp_ids

        # 1. Filter unassigned_components: Never flag a component as unassigned if it is selected or in adjustments
        clean_unassigned = []
        for u in unassigned_components:
            u_id = _norm(u.get("component_id", ""))
            is_match = any(u_id == pid or u_id in pid or pid in u_id for pid in protected_ids if pid)
            if not is_match:
                clean_unassigned.append(u)
        unassigned_components = clean_unassigned

        # 2. Filter missing_roles: Never flag a missing role if that component is in adjustments or selected
        clean_missing = []
        for m in missing_roles:
            sugg = _norm(m.get("suggestion") or "")
            role_text = _norm(m.get("role") or "")
            is_match = any(
                (pid and (pid in sugg or (sugg and sugg in pid) or pid in role_text))
                for pid in protected_ids
            )
            if not is_match:
                clean_missing.append(m)
        missing_roles = clean_missing

        # ─── Automatic Breadboard 400-Point Allocation Rule ──────────────────
        # If a subsystem has >= 3 peripheral components OR any passive components (resistors, LEDs, etc.),
        # automatically allocate a Breadboard 400-Point for shared power rails (+5V/GND) and tie-points.
        PASSIVE_KEYWORDS = [
            "resistor", "led", "diode", "capacitor", "ldr", "thermistor",
            "potentiometer", "ds18b20", "switch", "button", "probe"
        ]

        def _needs_breadboard(comps_dict: dict) -> bool:
            total_items = 0
            has_passive = False
            for k, val in comps_dict.items():
                k_lower = k.lower()
                val_lower = str(val).lower()
                # Exclude microcontrollers from count
                if any(mcu in k_lower for mcu in ["arduino", "esp32", "pico", "stm32", "microcontroller"]):
                    continue
                total_items += 1
                if any(kw in k_lower or kw in val_lower for kw in PASSIVE_KEYWORDS):
                    has_passive = True
            return total_items >= 3 or has_passive

        if categorized_roles:
            for b_idx, cat in enumerate(categorized_roles):
                cat_roles = cat.get("roles", {})
                has_bb = any("breadboard" in rk.lower() for rk in cat_roles.keys())
                if not has_bb and _needs_breadboard(cat_roles):
                    bb_key = f"breadboard_{b_idx + 1}"
                    bb_role = (
                        f"Breadboard 400-Point ({cat.get('board_name', f'Board #{b_idx + 1}')}): "
                        "Shared power distribution rails (+5V/GND) and passive component tie-points"
                    )
                    cat_roles[bb_key] = bb_role
                    role_assignments[bb_key] = bb_role
        else:
            has_bb = any("breadboard" in rk.lower() for rk in role_assignments.keys())
            if not has_bb and _needs_breadboard(role_assignments):
                role_assignments["breadboard_1"] = (
                    "Breadboard 400-Point: Shared power distribution rails (+5V/GND) and passive component tie-points"
                )

        # Re-compute is_aligned
        is_aligned = (
            len(missing_roles) == 0
            and len(unassigned_components) == 0
            and len(quantity_adjustments) == 0
            and len(voltage_adjustments) == 0
            and len(role_assignments) > 0
        )

        logger.info(
            f"[N2] Roles assigned: {len(role_assignments)} | "
            f"Categorized boards: {len(categorized_roles)} | "
            f"Quantity adjustments: {len(quantity_adjustments)} | "
            f"Voltage adjustments: {len(voltage_adjustments)} | "
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
        "categorized_roles": categorized_roles,
        "missing_roles": missing_roles, 
        "unassigned_components": unassigned_components,
        "quantity_adjustments": quantity_adjustments,
        "voltage_adjustments": voltage_adjustments,
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
    state["role_assignments"]           = final_assignments
    state["categorized_roles"]          = categorized_roles
    state["missing_roles"]              = missing_roles
    state["unassigned_components"]      = unassigned_components
    state["quantity_adjustments"]       = quantity_adjustments
    state["voltage_adjustments"]        = voltage_adjustments
    state["enriched_scope"]             = enriched_scope
    state["is_aligned"]                 = is_aligned
    state["status"]                     = "hitl_complete"

    return state
