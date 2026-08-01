# take with Gemini

import os
import json
from dotenv import load_dotenv
from google import genai

db_env = os.path.join(os.path.dirname(os.path.abspath(__file__)), "db", ".env")
load_dotenv(db_env)
load_dotenv()

# Create a client manager 
client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

# extract json embeddings from the text
def extract_json(text):
    text = text.strip()

    if text.startswith("```json"):
        text = text.replace("```json", "").replace("```", "").strip()
    elif text.startswith("```"):
        text = text.replace("```", "").strip()

    return json.loads(text)


def generate_ai_wiring_plan(scope, selected_components):
    prompt = f"""
You are Wiring AI, an assistant for beginner Arduino, ESP32, and Raspberry Pi electronics projects.

Your job:
1. Check if the user's selected components can reasonably satisfy the project scope.
2. If compatible, reiterate how the project components fit the scope and generate ALL beginner-friendly wiring steps.
3. If not compatible, explain what is missing.

Project scope:
{scope}

Selected components:
{json.dumps(selected_components, indent=2)}

Return JSON only. No markdown.

Use this exact structure:
{{
  "title": "short project title",
  "compatible": true,
  "compatibilitySummary": "short explanation",
  "missingComponents": [],
  "warnings": [],
  "steps": [
    {{
      "id": "step_1",
      "title": "short title",
      "instruction": "clear beginner wiring instruction"
    }}
  ],
  "connections": [
    {{
      "id": "conn_1",
      "fromComponent": "component_id",
      "fromPin": "pin name",
      "toComponent": "component_id",
      "toPin": "pin name",
      "label": "short label"
    }}
  ]
}}

Rules:
- Only use selected components in connections.
- If a resistor is needed for an LED but not selected, set compatible to false and include it in missingComponents.
- If no microcontroller is selected, set compatible to false.
- If project needs something in its scope and it is missing from selected components, set compatible to false.
- If compatible is false, still give a short explanation, but steps and connections can be empty.
- Keep instructions simple.
"""

    response = client.models.generate_content(
        model="gemini-2.5-flash-lite",
        contents=prompt,
    )

    raw_text = response.text
    print("RAW GEMINI OUTPUT:")
    print(raw_text)

    data = extract_json(raw_text)

    return normalize_ai_result(data)


def normalize_ai_result(data):
    data.setdefault("title", "Untitled Wiring Project")
    data.setdefault("compatible", False)
    data.setdefault("compatibilitySummary", "")
    data.setdefault("missingComponents", [])
    data.setdefault("warnings", [])
    data.setdefault("steps", [])
    data.setdefault("connections", [])

    # Take exisitng steps and jsonify it with id, title, instruction (otherwise the AI task would be too long)
    for i, step in enumerate(data["steps"], start=1):
        step.setdefault("id", f"step_{i}")
        step.setdefault("title", f"Step {i}")
        step.setdefault("instruction", "")
    # same for connections - algorithimically scale it to many steps
    for i, conn in enumerate(data["connections"], start=1):
        conn.setdefault("id", f"conn_{i}")
        conn.setdefault("fromComponent", "")
        conn.setdefault("fromPin", "")
        conn.setdefault("toComponent", "")
        conn.setdefault("toPin", "")
        conn.setdefault("label", "")

    return data