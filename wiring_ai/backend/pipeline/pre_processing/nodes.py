""" ----------------------------------
# PRE_PROCESSING NODES
# Five nodes. Each has ONE job. Each reads state, does work, returns updated state. 

1. check_vector_db_node
2. validate_datasheet_node
3. web_search_node 
4. dispatch_ingestion_node 
5. poll and finalize_node
 ----------------------------------
"""

import asyncio
import base64
import json
import logging
import os
from typing import Optional
import redis.asyncio as aioredis
from qdrant_client import AsyncQdrantClient
from qdrant_client.models import Filter, FieldCondition, MatchValue
from google import genai
from pipeline.pre_processing.state import PreProcessState
from google.genai import types

logger = logging.getLogger(__name__)


QDRANT_COLLECTION = "datasheets"
QDRANT_URL = os.getenv("QDRANT_URL", "http://localhost:6333")
REDIS_URL  = os.getenv("REDIS_URL", "redis://localhost:6379/0")
MCP_SERVER_URL = os.getenv("MCP_SERVER_URL", "http://localhost:8000/mcp")

# ---------- HELPER ----------------
def gemini_model():
    return genai.Client(api_key=os.getenv("GEMINI_API_KEY"))


# ---------- NODE 1: Check Vector DB node -------------------

async def check_vector_db_node(state: PreProcessState):
    """Check if component already exists in Qdrant (maybe different name)."""
    
    component_id = state["component_id"]
    logger.info(f"[NODE: check_vector_db] Checking {component_id}")

    state["status"] = "checking"
    state["already_indexed"] = False 

    try: 
        # -- Fast path: redis cache --- 
        r = aioredis.from_url(REDIS_URL, decode_responses=True)
        cached = await r.get(f"component: {component_id}:indexed")
        await r.aclose() 

        if cached == "true": 
            logger.info(f"[NODE: check_vector_db] Redis Cache hit: {component_id} already indexed")
            state["already_indexed"] = True 
            state["status"] = "already indexed"
            state["validation_message"] = f"{state['component_name']} is already in the catalog" 
            return state 

        # -- Authoratative Path: Qdrant Check: Does the component id key to a set of vector values match it
        client = AsyncQdrantClient(url=QDRANT_URL)
        results, _ = await client.scroll(
            collection_name=QDRANT_COLLECTION,
            scroll_filter=Filter(
                must=[FieldCondition(
                    key="component_id",
                    match=MatchValue(value=component_id)
                )]
            ),
            limit=1,
            with_payload=False,
            with_vectors=False,
        )
        await client.close()

        # if it does:
        if results:
            logger.info(f"[NODE:check_vector_db] Qdrant hit: {component_id} already indexed")
            # Back-fill Redis cache
            r2 = aioredis.from_url(REDIS_URL, decode_responses=True)
            await r2.set(f"component:{component_id}:indexed", "true", ex=86400)
            await r2.aclose()

            state["already_indexed"] = True
            state["status"] = "already_indexed"
            state["validation_message"] = f"'{state['component_name']}' is already in the catalog."

        else: 
            logger.info(f"[NODE: check_vector_db] Not indexed - proceed to validation")
        
    except Exception as e: 
        logger.warning(f"[NODE: check_vector_db] Error: {e}")
    
    return state 
    # all it did was check if component id was in redis cache or qdrant vector database

     


# --------- NODE 2: validate datasheet node 
VALIDATION_PROMPT = """\
You are a hardware engineering expert. Analyze this document text and determine if it is a \
legitimate electronic component datasheet.
A legitimate datasheet must have MOST of:
- Component name and part number
- Electrical specifications (voltage ratings, current draw, resistance, etc.)
- Pin configuration or connection diagram
- Operating conditions or absolute maximum ratings
The document should NOT be:
- A user manual or getting started guide
- A product marketing brochure
- An unrelated technical document
Document text (first 3 pages):
---
{text}
---
Respond ONLY with valid JSON:
{{
  "is_datasheet": true,
  "confidence": 0.95,
  "component_name": "extracted component name or null if unclear",
  "key_specs_found": ["Voltage: 3.3-5V", "Pins: 4", "Protocol: 1-Wire"],
  "reason": "Brief explanation of your determination"
}}
"""

# pyrefly: ignore [bad-return]
async def validate_datasheet_node(state: PreProcessState)-> PreProcessState: 
    
    """
    Flow -
    - No pdf uploaded -> needs web search = True (go find one lol)
    - PDF uploaded -> extract first 3 pages -> gemini analysis 
        - Valid: datasheet_valid = True 
        - Invalid: needs_web_search = True 
    """
    logger.info(f"[NODE:validate_datasheet] component={state['component_id']}")
    state["status"] = "validating"
    state["datasheet_valid"] = False
    state["needs_web_search"] = False

    pdf_bytes: Optional[bytes] = state.get("pdf_bytes")

    # -- No file provided -> go to web search automatically ---------
    if not pdf_bytes: 
        logger.info("[NODE:validate_datasheet] No PDF provided — triggering web search")
        state["needs_web_search"] = True
        state["validation_message"] = f"No datasheet provided. Searching the web for '{state['component_name']}'..."
        return state 
    
    # -- file provided -> validate with gemini 
    try: 
        from rag.ingestor import extract_first_pages_for_validation
        preview_text = extract_first_pages_for_validation(pdf_bytes, num_pages=3)

        if len(preview_text.strip()) < 100: 
            # cant extract text - likely a scanned pdf 
            logger.warning("[NODE: validate_datasheet] PDF Appears to be image-based")
            state["needs_web_search"] = True
            state["validation_message"] = (
                "Uploaded file appears to be a scanned image — "
                f"searching web for '{state['component_name']}' datasheet..."
            )
            return state
        
        model = gemini_model()
        prompt = VALIDATION_PROMPT.format(text=preview_text[:4000])

        # Enforce JSON output mode
        response = model.models.generate_content(
            model="gemini-2.5-flash-lite",
            contents=prompt,
            config=types.GenerateContentConfig(response_mime_type="application/json"),
        )
        if not response.text: 
            raise ValueError("No response from Gemini validation")
        # Safely strip markdown wrappers if present
        clean_text = response.text.strip()
        if clean_text.startswith("```"):
            clean_text = clean_text.strip("`").removeprefix("json").strip()
        result = json.loads(clean_text)

        is_valid   = result.get("is_datasheet", False)
        confidence = result.get("confidence", 0.0)
        comp_name  = result.get("component_name")
        reason     = result.get("reason", "")

        # if gemini deems it a valid datasheet and scores an overall positive confidence. 
        if is_valid and confidence >= 0.7:
            logger.info(f"[NODE:validate_datasheet] ✓ Valid datasheet | confidence={confidence:.2f}")
            state["datasheet_valid"] = True
            state["extracted_component_name"] = comp_name
            state["validation_message"] = (
                f"✓ Datasheet Recognized: {comp_name or state['component_name']} "
                f"(confidence: {confidence:.0%}) — Initiating Onboarding..."
            )
            # Pre-encode bytes to base64 for MCP tool (JSON-serializable)
            state["pdf_base64"] = base64.b64encode(pdf_bytes).decode("utf-8")
        else: 
            logger.info(f"[NODE:validate_datasheet] ✗ Not a datasheet | reason={reason}")
            state["needs_web_search"] = True
            state["validation_message"] = (
                f"⚠ Incorrect datasheet file detected ({reason}). "
                f"Searching the web for '{state['component_name']}'..."
            )

    except Exception as e:
        logger.error(f"[NODE:validate_datasheet] Validation error: {e}", exc_info=True)
        # On error: be lenient, try web search
        state["needs_web_search"] = True
        state["validation_message"] = f"Could not validate PDF — falling back to web search..."

    return state 


# ------ Node 3: web_search_node : enter tavily ----------------


async def web_search_node(state: PreProcessState) -> PreProcessState: 
    """
    Uses Tavily API for structured results with PDF links 
    Downloads the first viable pdf and encodes to base64 for MCP tool
    """
    component_name = state["component_name"]
    logger.info(f"[NODE:web_search] Searching web for '{component_name}' datasheet")
    state["status"] = "searching"

    try:
        from tavily import TavilyClient
        import httpx
        tavily = TavilyClient(api_key=os.getenv("TAVILY_API_KEY", ""))
        query = f"{component_name} datasheet filetype:pdf electrical specifications"
        # list of dicts (i think) containing search results
        results = tavily.search(
            query=query,
            search_depth="advanced",
            max_results=5,
            include_raw_content=False,
        )

        # Find a URL that looks like a PDF
        pdf_url = None
        for result in results.get("results", []):
            url = result.get("url", "")
            if ".pdf" in url.lower() or "datasheet" in url.lower():
                pdf_url = url
                break
        
        if not pdf_url and results.get("results"):
            # take the first results URL as fall back 
            pdf_url = results["results"][0].get("url")
        
        if not pdf_url: 
            raise ValueError("No PDF URL found in search results")
        
        logger.info(f"[NODE:web_search] Found candidate URL: {pdf_url}")
        state["found_datasheet_url"] = pdf_url

        # Attempt PDF download
        async with httpx.AsyncClient(follow_redirects=True, timeout=30) as client:
            response = await client.get(pdf_url)
            response.raise_for_status()
            pdf_bytes = response.content
        
        state["pdf_base64"] = base64.b64encode(pdf_bytes).decode("utf-8")
        state["datasheet_url"] = pdf_url
        state["validation_message"] = (
            f"✓ Found datasheet via web search: {pdf_url[:60]}... — Initiating Onboarding..."
        )
        logger.info(f"[NODE:web_search] Downloaded {len(pdf_bytes)} bytes from {pdf_url}")
    
    except Exception as e: 
        logger.error(f"[NODE:web_search] Web search failed: {e}")
        state["status"] = "failed"
        state["error"] = f"Web search for '{component_name}' datasheet failed: {e}"
    
    return state
    
    
# ------ Node 4: dispatch ingestion node ----------------- 

async def dispatch_ingestion_node(state: PreProcessState) -> PreProcessState: 
    """
    Call the MCP tool to dispatch celery task 
    Call tool via SSE transport - it doesn't know about celery 
    """
    logger.info(f"[NODE:dispatch_ingestion] component={state['component_id']}")
    state["status"] = "dispatching"

    try:
        from mcp import ClientSession
        from mcp.client.sse import sse_client
    
        mcp_args = {
            "component_id" : state["component_id"]    
        }
        if state.get("pdf_base64"):
            mcp_args["pdf_base64"] = state["pdf_base64"]
        if state.get("datasheet_url") or state.get("found_datasheet_url"):
            # pyrefly: ignore [bad-assignment]
            mcp_args["datasheet_url"] = state.get("datasheet_url") or state.get("found_datasheet_url")

        async with sse_client(f"{MCP_SERVER_URL}/sse") as (read, write): 
            async with ClientSession(read, write) as session: 
                await session.initialize()
                result = await session.call_tool("onboard_component_datasheet", mcp_args)

        # MCP Returns: {"job_id": str, "status": "queued"}
        # all this just to retrieve job_id 
        if getattr(result, "isError", False):
            first_block = result.content[0] if getattr(result, "content", None) else None
            error_text = getattr(first_block, "text", "Unknown MCP error")
            raise RuntimeError(f"MCP tool execution failed: {error_text}")

        if not getattr(result, "content", None):
            raise RuntimeError("MCP tool returned empty response")

        first_block = result.content[0]
        raw_text = getattr(first_block, "text", None)
        if not raw_text:
            raise RuntimeError("MCP tool response missing text payload")

        tool_result: dict = json.loads(raw_text)
        job_id = str(tool_result.get("job_id", ""))

        state["job_id"] = job_id
        state["status"] = "dispatched"
        logger.info(f"[NODE:dispatch_ingestion] ✓ Dispatched job_id={job_id}")

    except Exception as e:
        logger.error(f"[NODE:dispatch_ingestion] Dispatch failed: {e}", exc_info=True)
        state["status"] = "failed"
        state["error"] = f"Failed to dispatch ingestion job: {e}"
    
    return state

        

# ------- Node 5: poll and finalize node ----------


async def poll_and_finalize_node(state: PreProcessState) -> PreProcessState:
    """
    Polls Redis Hash every 1s (for 3 minutes max)
    
    FastAPI will poll the redis hash and stream in asynchronosly without any conflict for PROGRESS
    This node only polls to ask "Are we done yet?" 


    """

    job_id = state.get("job_id")
    if not job_id:
        state["status"] = "failed"
        state["error"] = "No job_id to poll"
        return state
    
    logger.info(f"[NODE:finalize] Polling Redis for job {job_id}")
    r = aioredis.from_url(REDIS_URL, decode_responses=True)

    try:
        for _ in range(180):  # poll for up to 3 minutes
            job_data = await r.hgetall(f"job:{job_id}")
            # retreive job data, if nothing chill for one second 
            if not job_data:
                await asyncio.sleep(1)
                continue
            
            job_status = job_data.get("status", "running")

            if job_status == "complete": 
                metadata_str = job_data.get("metadata", "{}")
                state["extracted_metadata"] = json.loads(metadata_str)
                state["status"] = "complete"
                state["validation_message"] = "✓ Component successfully onboarded to catalog!"
                
                # Cache the indexed status in Redis
                await r.set(
                    f"component:{state['component_id']}:indexed",
                    "true",
                    ex=86400
                )
                logger.info(f"[NODE:finalize] ✓ Job {job_id} complete")
                break

            elif job_status == "failed":
                error = job_data.get("error", "Unknown Celery error")
                state["status"] = "failed"
                state["error"] = str(error)
                logger.error(f"[NODE:finalize] ✗ Job {job_id} failed: {error}")
                break
            await asyncio.sleep(1)
        else:
            state["status"] = "failed"
            state["error"] = "Ingestion timed out after 3 minutes"
            logger.error(f"[NODE:finalize] Timeout waiting for job {job_id}")
    finally:
        await r.aclose()
    return state