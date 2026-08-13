from mcp.server import MCPServer 
from typing import TypedDict, Any
from mcp_.tools.onboard_tool import onboard_component_datasheet

mcp = MCPServer("Wiring AI")

# -------- Pre Processing Tool -----------------------
tool_description = (
    "Onboard a component's datasheet into the vector database. "
    "Accepts a base64-encoded PDF or a URL. "
    "Returns a job_id to track ingestion progress via Redis."
)
mcp.tool(description=tool_description)(onboard_component_datasheet)


# Generation Tool
@mcp.tool()
async def search_datasheets_by_category(
    component_ids: list[str],
    category: str,
    query: str
) -> list[str]:
    """
    RAG search across datasheets for a specific information category.
    Categories: pin_mapping | passive_requirements | signal_protocol |
                electrical_tolerances | circuit_warnings
    Returns: top-K relevant chunks.
    """
    return [f"[STUB] chunk for {category} / {component_ids}"]


# Post-processing tool
@mcp.tool()
async def retrieve_project_context(
    session_id: str,
    component_ids: list[str]
) -> dict:
    """
    Retrieve full project context for a session.
    Checks Redis cache first, falls back to Qdrant retrieval.
    Returns: wiring plan + relevant datasheet chunks.
    """
    return {"wiring_plan": {}, "chunks": [], "source": "stub"}


# ─── ASGI app for mounting in FastAPI ────────────────────────────────────────
mcp_asgi_app = mcp.sse_app()