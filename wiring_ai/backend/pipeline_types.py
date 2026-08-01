from pydantic import BaseModel, Field
from typing import Literal, Optional, Any
from datetime import datetime
import uuid


class StageDetail(BaseModel):
    """Individual check within a pipeline stage."""
    check: str                    # what was checked: "LED has current limiter"
    status: Literal["pass", "warn", "fail"]
    message: str                  # result: "220Ω resistor present in component list"
    severity: Optional[Literal["info", "warning", "danger"]] = None


class StageResult(BaseModel):
    """Every stage returns this shape."""
    stage: Literal["input", "compatibility", "autofix", "llm_plan", "completeness", "pin_resolver", "safety", "result"]
    status: Literal["pass", "warn", "fail", "halt", "fix", "skip"]
    message: str                  # human-readable summary: "All components compatible"
    details: list[StageDetail]    # individual checks within this stage
    data: Optional[Any] = None    # stage-specific output data (wiring plan, resolved pins, etc.)
    timestamp: str = Field(default_factory=lambda: datetime.utcnow().isoformat())
    duration_ms: float            # how long this stage took


class LogicalConnection(BaseModel):
    """What the LLM outputs — logical, no physical pin numbers."""
    from_component: str           # component ID: "hc-sr04"
    from_pin: str                 # pin name: "TRIG"
    to_component: str             # component ID: "arduino-uno"
    to_pin_type: str              # pin TYPE not number: "DIGITAL", "DIGITAL_PWM", "ANALOG", "5V", "GND"
    connection_type: Literal["signal", "power", "ground"]
    notes: Optional[str] = None   # "any digital pin will work"


class LogicalWiringPlan(BaseModel):
    """The LLM's output — logical connections between components."""
    connections: list[LogicalConnection]
    component_ids: list[str]      # every component ID that appears in the plan


class ResolvedConnection(BaseModel):
    """What the pin resolver outputs — physical pin numbers assigned."""
    from_component: str
    from_pin: str
    to_component: str
    to_pin: str                   # now a PHYSICAL pin: "D9", "A0", "5V", "GND"
    connection_type: Literal["signal", "power", "ground"]
    wire_color: Optional[str] = None  # suggested wire color for the diagram


class ResolvedWiringPlan(BaseModel):
    """Final resolved plan with physical pin assignments."""
    connections: list[ResolvedConnection]
    pin_assignments: dict[str, dict[str, str]]  # { "hc-sr04": { "TRIG": "D9", "ECHO": "D10" } }


class PipelineResult(BaseModel):
    """The full pipeline result returned to the frontend."""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    stages: list[StageResult]     # results from every stage that ran
    final_status: Literal["success", "partial", "failed", "halted"]
    wiring_plan: Optional[ResolvedWiringPlan] = None  # only present if pipeline succeeded
    created_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat())


class AutoFix(BaseModel):
    component_added_id: str      # "resistor-220"
    reason: str                  # "Red LED requires current-limiting resistor"
    explanation: str             # "Without a resistor, the LED draws too much current..."
    triggered_by: str            # component ID that needs this: "led-red"


class AutoFixResult(StageResult):
    fixed_component_list: list[str] = []
    fixes_applied: list[AutoFix] = []


class LLMPlanResult(StageResult):
    wiring_plan: Optional[LogicalWiringPlan] = None


class CompletenessResult(StageResult):
    missing_components: list[str] = []
    should_retry: bool = False



