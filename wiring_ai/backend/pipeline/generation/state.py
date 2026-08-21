from typing import TypedDict, Optional, Dict, List 

class Generation(TypedDict): 

    # Inputs (set by fastapi before langgraph)
    session_id: str 
    project_scope: str 
    component_ids: list[str]
    revision_context: Optional[str]

    # Node 1: project_exist() 
    existing_project_id: Optional[str]  
    is_cached: bool   


    # Node 2: Query Optimization
    role_assignments: dict

    missing_roles: list[dict]       
    unassigned_components: list[dict]  
    enriched_scope: str              
    is_aligned: bool              

    hitl_rejection_reason: Optional[str]  
    hitl_user_edits: Optional[dict] 
    hitl_status: str

    # Node 3: pre_compatibility() 
    component_metadata: list[dict]   # full PostgreSQL records for selected components
    pre_compat_errors: list[dict]    # blockers: must fix before generation
    pre_compat_warnings: list[dict]  # cautions: non-blocking but noted
    auto_fixed_components: list[str] # component IDs added by autofix engine


    # Node 4: RAG 
    rag_context: dict 

    # Node 5: synthesize_wriring() 
    connections: list[dict]
    wiring_steps: list[str] 
    react_flow_schema: Optional[dict]

    # Node 6: Post check 
    post_compat_errors: list[dict]   # errors found on ACTUAL connections (not just metadata)
    retry_count: int  
    

    # Universal Update after each node 
    status: str 
    error: Optional[str] 