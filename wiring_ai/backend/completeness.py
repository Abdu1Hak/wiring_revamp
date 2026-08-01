import time
from typing import List, Optional
from pipeline_types import StageResult, StageDetail, LogicalWiringPlan, CompletenessResult
from db.database import get_components_by_ids

async def run_completeness_check(
    input_component_ids: List[str],
    wiring_plan: LogicalWiringPlan,
    attempt: int = 1
) -> CompletenessResult:
    """
    Validates that every non-platform input component appears in the logical wiring plan connections.
    If components are missing and this is the first attempt, signals a retry.
    """
    start_time = time.time()
    
    # 1. Gather all component IDs present in the generated wiring plan connections
    output_ids = set()
    for conn in wiring_plan.connections:
        output_ids.add(conn.from_component)
        output_ids.add(conn.to_component)
        
    if wiring_plan.component_ids:
        output_ids.update(wiring_plan.component_ids)

    print("WHAT IS WIRING_PLAN")
    print(wiring_plan)
    # 2. Query component categories to ignore platforms like breadboards
    # (await because database.py is now async)
    unique_input_ids = list(set(input_component_ids))
    components = await get_components_by_ids(unique_input_ids)
    platform_ids = {c["id"] for c in components if c.get("category") == "platform"}
    
    # 3. Identify missing components
    missing_components = []
    for cid in input_component_ids:
        if cid in platform_ids:
            continue
        if cid not in output_ids:
            missing_components.append(cid)
            
    # Deduplicate missing components list
    missing_components = list(set(missing_components))
    
    duration_ms = (time.time() - start_time) * 1000.0
    
    if missing_components:
        should_retry = (attempt == 1)
        status = "warn" if should_retry else "fail"
        severity = "warning" if should_retry else "danger"
        message = f"Wiring plan omitted components: {', '.join(missing_components)}."
        
        return CompletenessResult(
            stage="completeness",
            status=status,
            message=message,
            details=[StageDetail(
                check="Component Completeness",
                status=status,
                message=message,
                severity=severity
            )],
            duration_ms=duration_ms,
            missing_components=missing_components,
            should_retry=should_retry
        )
    else:
        return CompletenessResult(
            stage="completeness",
            status="pass",
            message="All selected components are successfully wired in the plan.",
            details=[StageDetail(
                check="Component Completeness",
                status="pass",
                message="No missing components."
            )],
            duration_ms=duration_ms,
            missing_components=[],
            should_retry=False
        )
