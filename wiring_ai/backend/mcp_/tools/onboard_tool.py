"""
MCP Tool for Deploying Celery Job to Worker
1. Will convert the pdf to a temp file on RAM so its easier for Redis 
2. Dispatch celery task
3. return job_id immediately 
"""

import os 
import tempfile 
import uuid 
import logging 
from typing import Optional

logger = logging.getLogger(__name__)

async def onboard_component_datasheet(
    component_id: str, 
    pdf_base64: Optional[str] = None, 
    datasheet_url: Optional[str] = None,
    ) -> dict: 

    """
    MCP Tool: Onboard a component's datasheet into the vector database.
    Args:
        component_id: Unique identifier for the component (e.g., "dht22")
        pdf_base64: Base64-encoded PDF bytes (if user uploaded)
        datasheet_url: Fallback URL if no PDF uploaded
    Returns:
        {"job_id": str, "status": "queued"}
    """

    import base64 
    from jobs.tasks import ingest_datasheet_task

    job_id = str(uuid.uuid4())
    pdf_path : Optional[str] = None 

    # if bytes provided: same to temp file so celery can read it 
    if pdf_base64:
        try:
            pdf_bytes = base64.b64decode(pdf_base64)
            tmp = tempfile.NamedTemporaryFile(
                suffix=".pdf",
                delete=False, 
                prefix=f"wiring_ai_{component_id}_"
            )
            tmp.write(pdf_bytes)
            tmp.close()
            pdf_path = tmp.name
            logger.info(f"[MCP:ONBOARD] Saved PDF to temp file {pdf_path}")
        except Exception as e:
            logger.error(f"[MCP:ONBOARD] Failed to save base64 PDF: {e}")
            raise ValueError(f"Invalid base64 encoding: {e}")
    
    if not pdf_path and not datasheet_url: 
        raise ValueError("No PDF provided: upload a PDF or provide datasheet_url.")

    
    # Dispatch Celery task (Non blocking, return immediately)
    # use .apply_async() instead of delay so you can add task_id  
    task = ingest_datasheet_task.apply_async(
        kwargs={
            "job_id": job_id,
            "component_id": component_id,
            "pdf_path": pdf_path,
            "datasheet_url": datasheet_url,
        },
        task_id=job_id,  # use our job_id as Celery task ID for easy lookup
    )
    logger.info(f"[MCP:ONBOARD] Dispatched Celery task {job_id} for {component_id}")

    return {"job_id": job_id, "celery_task_id": task.id, "status": "queued"} 

 