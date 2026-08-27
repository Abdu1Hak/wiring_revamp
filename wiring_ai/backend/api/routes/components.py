# api/routes/components.py
# ---------------------------------------------------------------------------
# API ROUTER: Component Catalog Management
# ---------------------------------------------------------------------------
import logging
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import Optional, List
from db.database import (
    get_all_components,
    get_component_by_name,
    delete_component_by_id,
    update_component_name,
    update_component_metadata,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/components", tags=["components"])


class PowerDict(BaseModel):
    logic_voltage: Optional[float] = None
    voltage_range: Optional[List[float]] = None
    operating_current_mA: Optional[float] = None
    is_external_powered: Optional[bool] = None


class InterfaceDict(BaseModel):
    protocol: Optional[str] = None
    i2c_address: Optional[str] = None


class UpdateComponentRequest(BaseModel):
    name: Optional[str] = None
    power: Optional[PowerDict] = None
    interface: Optional[InterfaceDict] = None


@router.get("", response_model=None)
@router.get("/", response_model=None)
async def list_components():
    """
    Returns all onboarded components from the database, sorted by category and name.
    """
    try:
        components = await get_all_components()
        return components
    except Exception as e:
        logger.error(f"[Components API] Error fetching components: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to fetch components: {str(e)}")


@router.get("/{component_id}")
async def get_component(component_id: str):
    """
    Returns details for a single component by its ID or name.
    """
    try:
        component = await get_component_by_name(component_id)
        if not component:
            raise HTTPException(status_code=404, detail=f"Component '{component_id}' not found")
        return component
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[Components API] Error fetching component '{component_id}': {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to fetch component: {str(e)}")


@router.patch("/{component_id}")
@router.put("/{component_id}")
async def update_component(component_id: str, payload: UpdateComponentRequest):
    """
    Updates component details in the database.
    Supports:
    - name: component name
    - power: power dict (logic_voltage, voltage_range, operating_current_mA, is_external_powered)
    - interface: interface dict (protocol, i2c_address)
    """
    try:
        # Build update payload with only provided fields
        update_data = {}
        
        if payload.name:
            update_data["name"] = payload.name
        
        if payload.power:
            update_data["power"] = payload.power.dict(exclude_none=True)
        
        if payload.interface:
            update_data["interface"] = payload.interface.dict(exclude_none=True)
        
        if not update_data:
            raise HTTPException(status_code=400, detail="No fields to update")
        
        updated = await update_component_metadata(component_id, update_data)
        if not updated:
            raise HTTPException(status_code=404, detail=f"Component '{component_id}' not found")
        return updated
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[Components API] Error updating component '{component_id}': {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to update component: {str(e)}")


@router.delete("/{component_id}")
async def delete_component(component_id: str):
    """
    Deletes a component from the database.
    """
    try:
        await delete_component_by_id(component_id)
        return {"message": f"Component '{component_id}' deleted successfully"}
    except Exception as e:
        logger.error(f"[Components API] Error deleting component '{component_id}': {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to delete component: {str(e)}")

