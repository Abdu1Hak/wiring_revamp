"""
list_models.py
──────────────
Query Google Gemini API directly to list all active, available models for your API key.
"""

import os
from dotenv import load_dotenv
from google import genai

def list_available_models():
    load_dotenv()
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        print("❌ No GEMINI_API_KEY found.")
        return

    client = genai.Client(api_key=api_key)
    print("🔍 Fetching active models for your key...\n")
    try:
        models = client.models.list()
        for m in models:
            # Filter for content generation models
            name = getattr(m, 'name', '') or str(m)
            methods = getattr(m, 'supported_generation_methods', []) or getattr(m, 'supported_actions', [])
            print(f"• {name}")
    except Exception as e:
        print(f"Error fetching models: {e}")

if __name__ == "__main__":
    list_available_models()
