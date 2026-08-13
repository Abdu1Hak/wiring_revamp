import time
import copy
from typing import List, Optional
from pipeline_types import StageResult, StageDetail
from db.database import get_components_by_ids

def check_voltage_compatibility(components: List[dict], board: Optional[dict]) -> List[StageDetail]:
    details = []
    if not board:
        return details
        
    board_voltage = board.get("operating_voltage")
    if board_voltage is None:
        return details

    for comp in components:
        if comp["category"] in ["passive", "platform", "board"]:
            continue
            
        # Skip LEDs for voltage compatibility checks as they are current-driven 
        # and their forward voltage is not a VCC supply voltage
        if "led" in comp["id"].lower() or "led" in comp["name"].lower() or "led" in comp.get("tags", []):
            continue
            
        comp_power = comp.get("power")
        if not comp_power:
            continue
            
        comp_voltage = comp_power.get("voltage")
        if comp_voltage is not None:
            if comp_voltage != board_voltage:
                if comp["id"] == "hc_sr04" and board_voltage == 3.3:
                    details.append(StageDetail(
                        check="Voltage Compatibility",
                        status="warn",
                        message="HC-SR04 runs at 5V but board is 3.3V. ECHO pin will output 5V into 3.3V GPIO — needs level shifting.",
                        severity="danger"
                    ))
                else:
                    details.append(StageDetail(
                        check="Voltage Compatibility",
                        status="warn",
                        message=f"Voltage mismatch: Component '{comp['name']}' runs at {comp_voltage}V but board '{board['name']}' operates at {board_voltage}V.",
                        severity="warning"
                    ))
                    
    # If no mismatched voltages found, add a pass check
    if not any(d.check == "Voltage Compatibility" for d in details):
        details.append(StageDetail(
            check="Voltage Compatibility",
            status="pass",
            message=f"All components are voltage-compatible with the board operating voltage ({board_voltage}V).",
            severity="info"
        ))
        
    return details


def check_current_budget(components: List[dict], board: Optional[dict]) -> List[StageDetail]:
    details = []
    if not board:
        return details

    board_voltage = board.get("operating_voltage", 5.0)
    rail_limit = board.get("max_5v_rail_mA", 500.0) if board_voltage == 5.0 else board.get("max_3v3_rail_mA", 500.0)
    max_current_per_pin_mA = board.get("max_current_per_pin_mA", 40.0)

    total_current = 0.0
    for comp in components:
        if comp["category"] in ["passive", "platform", "board"]:
            continue
        comp_power = comp.get("power")
        if comp_power:
            total_current += comp_power.get("current_mA", 0.0)

    if total_current > rail_limit:
        details.append(StageDetail(
            check="Current Budget",
            status="fail",
            message=f"Exceeds board power capacity: Total current draw is {total_current}mA, which exceeds board operating rail limit of {rail_limit}mA.",
            severity="danger"
        ))
    elif total_current > 0.8 * rail_limit:
        details.append(StageDetail(
            check="Current Budget",
            status="warn",
            message=f"Approaching current limit: Total current draw is {total_current}mA (exceeds 80% of board operating rail limit {rail_limit}mA).",
            severity="warning"
        ))
    else:
        details.append(StageDetail(
            check="Current Budget",
            status="pass",
            message=f"Total current draw ({total_current}mA) is within safe limits of the board rail ({rail_limit}mA).",
            severity="info"
        ))

    # GPIO Pin current check
    for comp in components:
        if comp["category"] in ["passive", "platform", "board"]:
            continue
        comp_power = comp.get("power")
        if comp_power:
            curr = comp_power.get("current_mA", 0.0)
            if curr > max_current_per_pin_mA:
                details.append(StageDetail(
                    check="Pin Current Limit",
                    status="warn",
                    message=f"Component '{comp['name']}' draws {curr}mA, which exceeds board max current per GPIO pin ({max_current_per_pin_mA}mA) if powered directly from a pin.",
                    severity="warning"
                ))

    return details


def check_pin_availability(components: List[dict], board: Optional[dict]) -> List[StageDetail]:
    details = []
    if not board:
        return details

    digital_needed = 0
    analog_needed = 0
    pwm_needed = 0
    i2c_needed = False

    for comp in components:
        if comp["category"] == "board":
            continue
        for pin in comp.get("pins", []):
            ptype = pin.get("type")
            pname = pin.get("name", "").upper()
            if ptype in ["digital_input", "digital_output", "digital_io", "data"]:
                digital_needed += 1
            elif ptype == "analog_input":
                analog_needed += 1
            elif ptype in ["pwm", "analog_output"]:
                pwm_needed += 1
            elif ptype in ["i2c_sda", "i2c_scl"] or pname in ["SDA", "SCL"]:
                i2c_needed = True

    unreserved_board_pins = [p for p in board.get("board_pins", []) if not p.get("reserved")]
    allocated_pins = set()

    # 1. Check I2C availability
    if i2c_needed:
        sda_pins = [p for p in unreserved_board_pins if "i2c_sda" in p.get("capabilities", [])]
        scl_pins = [p for p in unreserved_board_pins if "i2c_scl" in p.get("capabilities", [])]
        if not sda_pins or not scl_pins:
            details.append(StageDetail(
                check="Pin Availability",
                status="fail",
                message="I2C bus required but no I2C pins are available on the board.",
                severity="danger"
            ))
            return details
        # Reserve them
        for p in sda_pins + scl_pins:
            allocated_pins.add(p["pin_id"])

    # 2. Check PWM
    available_pwm = [p for p in unreserved_board_pins if "pwm" in p.get("capabilities", []) and p["pin_id"] not in allocated_pins]
    if pwm_needed > len(available_pwm):
        details.append(StageDetail(
            check="Pin Availability",
            status="fail",
            message=f"Not enough PWM pins: Required {pwm_needed}, but only {len(available_pwm)} available.",
            severity="danger"
        ))
        return details
    for i in range(pwm_needed):
        allocated_pins.add(available_pwm[i]["pin_id"])

    # 3. Check Analog
    available_analog = [p for p in unreserved_board_pins if "analog" in p.get("capabilities", []) and p["pin_id"] not in allocated_pins]
    if analog_needed > len(available_analog):
        details.append(StageDetail(
            check="Pin Availability",
            status="fail",
            message=f"Not enough analog pins: Required {analog_needed}, but only {len(available_analog)} available.",
            severity="danger"
        ))
        return details
    for i in range(analog_needed):
        allocated_pins.add(available_analog[i]["pin_id"])

    # 4. Check Digital
    available_digital = [p for p in unreserved_board_pins if "digital" in p.get("capabilities", []) and p["pin_id"] not in allocated_pins]
    if digital_needed > len(available_digital):
        details.append(StageDetail(
            check="Pin Availability",
            status="fail",
            message=f"Not enough digital pins: Required {digital_needed}, but only {len(available_digital)} available.",
            severity="danger"
        ))
        return details

    details.append(StageDetail(
        check="Pin Availability",
        status="pass",
        message=f"Board has sufficient pins for all components (Digital needed: {digital_needed}, Analog needed: {analog_needed}, PWM needed: {pwm_needed}).",
        severity="info"
    ))
    return details


def check_led_resistor(components: List[dict]) -> List[StageDetail]:
    details = []
    resistors = [c for c in components if c["category"] == "passive" and "resistor" in c["id"].lower()]
    has_resistor = len(resistors) > 0

    for comp in components:
        is_led = comp["category"] == "output" and ("led" in comp["id"].lower() or "led" in comp["name"].lower() or "led" in comp.get("tags", []))
        if is_led and not has_resistor:
            details.append(StageDetail(
                check="LED Resistor",
                status="warn",
                message=f"LED '{comp['name']}' is connected without a series current-limiting resistor.",
                severity="danger"
            ))
            
    if not details:
        # Check if LEDs are present to say "pass"
        leds = [c for c in components if c["category"] == "output" and ("led" in c["id"].lower() or "led" in c["name"].lower() or "led" in c.get("tags", []))]
        if leds:
            details.append(StageDetail(
                check="LED Resistor",
                status="pass",
                message="LEDs have accompanying current-limiting resistor(s) in selection.",
                severity="info"
            ))
    return details


def check_missing_support_components(components: List[dict]) -> List[StageDetail]:
    details = []
    resistors = [c for c in components if c["category"] == "passive" and "resistor" in c["id"].lower()]
    has_resistor = len(resistors) > 0

    for comp in components:
        for constraint in comp.get("constraints", []):
            ctype = constraint.get("type")
            if ctype in ["requires_resistor", "requires_pullup"]:
                if not has_resistor:
                    details.append(StageDetail(
                        check="Missing Support Component",
                        status="warn",
                        message=constraint.get("condition", f"Missing component required by {comp['name']}"),
                        severity=constraint.get("severity", "warning")
                    ))
                    
    if not details:
        # Check if any components with these constraints are present to add pass
        constrained_comps = [c for c in components if any(const.get("type") in ["requires_resistor", "requires_pullup"] for const in c.get("constraints", []))]
        if constrained_comps:
            details.append(StageDetail(
                check="Missing Support Component",
                status="pass",
                message="All required passive pullup/series components are satisfied.",
                severity="info"
            ))
    return details


async def run_compatibility_check(
    selected_component_ids: List[str],
    project_description: str
) -> StageResult:
    start_time = time.time()
    
    # Fetch unique components from DB (await because database.py is now async)
    unique_ids = list(set(selected_component_ids))
    db_components = {c["id"]: c for c in await get_components_by_ids(unique_ids)}
    
    # Map back to full selected list, preserving duplicates (deepcopying to prevent shared mutations)
    components = []
    for cid in selected_component_ids:
        if cid in db_components:
            components.append(copy.deepcopy(db_components[cid]))
    
    # Stage Details collector
    details = []
    
    # Find board
    board = next((c for c in components if c["category"] == "board"), None)
    
    if not board:
        details.append(StageDetail(
            check="Board Selection",
            status="fail",
            message="No microcontroller board was selected. A board is required for compatibility checking.",
            severity="danger"
        ))
    else:
        # Check 1: Voltage Compatibility
        details.extend(check_voltage_compatibility(components, board))
        
        # Check 2: Current Budget
        details.extend(check_current_budget(components, board))
        
        # Check 3: Pin Availability
        details.extend(check_pin_availability(components, board))
        
        # Check 4: LED Resistor
        details.extend(check_led_resistor(components))
        
        # Check 5: Missing Support Components
        details.extend(check_missing_support_components(components))
        
    # Determine stage status
    any_danger_fail = any(d.status == "fail" and d.severity == "danger" for d in details)
    any_fail = any(d.status == "fail" for d in details)
    any_warn = any(d.status == "warn" for d in details)
    
    if any_danger_fail:
        stage_status = "halt"
        message = "Compatibility checks failed with critical safety risks. Pipeline halted."
    elif any_fail:
        stage_status = "fail"
        message = "Compatibility checks failed."
    elif any_warn:
        stage_status = "warn"
        message = "Compatibility checks passed with warnings."
    else:
        stage_status = "pass"
        message = "All compatibility checks passed."
        
    duration_ms = (time.time() - start_time) * 1000.0
    
    return StageResult(
        stage="compatibility",
        status=stage_status,
        message=message,
        details=details,
        duration_ms=duration_ms
    )
