"""
test_gemini.py
──────────────
Quick script to verify your GEMINI_API_KEY and test connection to gemini-3.6-flash.
Run with:
    python test_gemini.py
"""

import os
import time
from dotenv import load_dotenv
from google import genai
from google.genai import types

def test_gemini_connection():
    load_dotenv()
    api_key = os.getenv("GEMINI_API_KEY")
    
    if not api_key:
        print("❌ ERROR: GEMINI_API_KEY not found in .env file!")
        return

    print("🔑 Loaded GEMINI_API_KEY successfully.")
    print(f"📡 Key prefix: {api_key[:8]}... | Length: {len(api_key)}")
    print("🚀 Sending test prompt to 'gemini-3.5-flash-lite'...")

    t0 = time.time()
    try:
        client = genai.Client(api_key=api_key)
        response = client.models.generate_content(
            model="gemini-3.5-flash-lite",
            contents="Say 'Gemini 3.5 Flash Lite is connected and operational!' and list 3 key hardware components for robotics in 1 sentence.",
        )
        elapsed = time.time() - t0
        
        print("\n" + "=" * 50)
        print(f"✅ SUCCESS! (Response received in {elapsed:.2f}s)")
        print("=" * 50)
        # pyrefly: ignore [missing-attribute]
        print(response.text.strip())
        print("=" * 50 + "\n")
        
    except Exception as e:
        print("\n" + "!" * 50)
        print(f"❌ Gemini API Call Failed: {e}")
        print("!" * 50 + "\n")

if __name__ == "__main__":
    test_gemini_connection()
