"""
pipelines/generation/graph.py
─────────────────────────────────────────────────────────────────────────
Generation pipeline LangGraph StateGraph.
KEY: The Redis checkpointer is REQUIRED here (unlike pre-processing).
Why: The HITL interrupt() suspends the graph mid-execution and the state
     must persist across two separate HTTP requests (start + confirm).
     MemorySaver only survives within one process invocation — useless for HTTP.
Graph topology:
  [START]
     │
  query_optimization ──(hitl interrupt here)──► user responds ──►
     │
  pre_compatibility
     │
  rag_retrieval
     │
  synthesize_wiring ◄──────────────────────────────────────┐
     │                                                      │ retry (max 2)
  post_check ──(errors found)──────────────────────────────┘
     │
     │ (clean)
  [END]
"""

import os
from langgraph.graph import StateGraph, END 
from langgraph.checkpoint.redis.aio import AsyncRedisSaver

from .state import Generation 
from .nodes import query_optimization 

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")



# ----- routing function -------
def route_after_post_check(state: Generation) -> str:
    """Retry synthesis if post-check found errors, otherwise finish."""
    if state["post_compat_errors"] and state["retry_count"] < 2:
        return "retry"
    return "done"


# ----- Graph Builder ---------- 

def build_generation_graph(checkpointer=None): 

    # pyrefly: ignore [bad-specialization]
    g = StateGraph(Generation)
    
    # register nodes 
    # g.add_node("project_exist", project_exist)
    g.add_node("query_optimization", query_optimization)

    # set entry point 
    g.set_entry_point("query_optimization")

    # conditional edges 

    return g.compile(checkpointer=checkpointer) 


generation_graph = None 

def get_generation_graph():
    global generation_graph
    if generation_graph is None:
        # Fallback build if lifespan hasn't set checkpointer yet
        generation_graph = build_generation_graph()
    return generation_graph

async def init_generation_graph(): 
    """
    initialize graph with async redis checkpointer
    usage in main.py startup -> runs fastapi lifespan -> generation_graph 
    """
    global generation_graph
    checkpointer = AsyncRedisSaver(redis_url=REDIS_URL)
    await checkpointer.asetup()
    generation_graph = build_generation_graph(checkpointer)


