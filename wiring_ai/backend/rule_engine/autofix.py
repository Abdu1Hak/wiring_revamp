import time
from typing import List
from pipeline_types import StageResult, StageDetail, AutoFix, AutoFixResult
from db.database import get_components_by_ids

async def run_auto_fix(
    selected_component_ids: List[str],
    compatibility_result: StageResult
) -> AutoFixResult:
    start_time = time.time()
    
    fixed_list = list(selected_component_ids)
    fixes = []
    
    # If the compatibility check halted the pipeline, skip auto-fix
    if compatibility_result.status == "halt":
        duration_ms = (time.time() - start_time) * 1000.0
        return AutoFixResult(
            stage="autofix",
            status="skip",
            message="Compatibility check halted the pipeline. Skipping auto-fix.",
            details=[],
            duration_ms=duration_ms,
            fixed_component_list=selected_component_ids,
            fixes_applied=[]
        )
        
    # Read the details array from the compatibility checker output
    leds_needing_resistor = []
    dht11s_needing_pullup = []
    buttons_needing_pulldown = []
    
    for detail in compatibility_result.details:
        # Check if the warning corresponds to an auto-fixable issue
        if detail.status == "warn":
            # 1. LED without resistor
            if detail.check == "LED Resistor":
                leds_needing_resistor.append(detail.message)
            # 2. DHT11 or Button/LDR without support component
            elif detail.check == "Missing Support Component":
                if "DHT11" in detail.message:
                    dht11s_needing_pullup.append(detail.message)
                elif "button" in detail.message.lower() or "push button" in detail.message.lower():
                    buttons_needing_pulldown.append(detail.message)
                elif "ldr" in detail.message.lower() or "photoresistor" in detail.message.lower():
                    buttons_needing_pulldown.append(detail.message)
            elif detail.check == "Missing resistor constraint" or detail.check == "Missing pull-up constraint":
                if "DHT11" in detail.message:
                    dht11s_needing_pullup.append(detail.message)
                elif "button" in detail.message.lower() or "ldr" in detail.message.lower() or "photoresistor" in detail.message.lower():
                    buttons_needing_pulldown.append(detail.message)

    # Apply LED Resistor Fixes
    for warning in leds_needing_resistor:
        # Extract LED name (usually "Red LED" or "Green LED" from "LED 'Name' is connected...")
        name = "LED"
        if "'" in warning:
            name = warning.split("'")[1]
            
        fixed_list.append("resistor_220")
        fixes.append(AutoFix(
            component_added_id="resistor_220",
            reason=f"LED '{name}' requires current-limiting resistor.",
            explanation=f"Added a 220Ω current-limiting resistor in series with the '{name}' anode to protect it from burning out and prevent GPIO pin damage.",
            triggered_by="led_red" if "red" in name.lower() else "led_green" if "green" in name.lower() else "led"
        ))
        
    # Apply DHT11 Pull-up Resistor Fixes
    for warning in dht11s_needing_pullup:
        fixed_list.append("resistor_4k7")
        fixes.append(AutoFix(
            component_added_id="resistor_4k7",
            reason="DHT11 Temperature Sensor requires a pull-up resistor.",
            explanation="Added a 4.7kΩ pull-up resistor between VCC and the DHT11 DATA pin to ensure stable communication on the single-bus line.",
            triggered_by="dht11"
        ))
        
    # Apply Button/LDR Pull-down Resistor Fixes
    for warning in buttons_needing_pulldown:
        name = "Button" if "button" in warning.lower() else "Photoresistor" if "ldr" in warning.lower() or "photoresistor" in warning.lower() else "Input Component"
        fixed_list.append("resistor_10k")
        fixes.append(AutoFix(
            component_added_id="resistor_10k",
            reason=f"{name} requires a pull-down/pull-up resistor.",
            explanation=f"Added a 10kΩ resistor to act as a pull-down/pull-up for the '{name}' pin to prevent floating inputs and ensure clean signal logic.",
            triggered_by="button" if "button" in name.lower() else "ldr"
        ))
        
    # If no fixes were applied, skip
    if not fixes:
        status = "skip"
        message = "No auto-fixes were required for this project configuration."
    else:
        status = "fix"
        message = f"Applied {len(fixes)} auto-fixes to resolve safety and compatibility warnings."
        
    duration_ms = (time.time() - start_time) * 1000.0
    
    # Generate stage detail entries for each applied fix
    details = []
    for fix in fixes:
        details.append(StageDetail(
            check="Auto-Fix Applied",
            status="pass",
            message=f"Automatically added component '{fix.component_added_id}' triggered by '{fix.triggered_by}'."
        ))
        
    return AutoFixResult(
        stage="autofix",
        status=status,
        message=message,
        details=details,
        duration_ms=duration_ms,
        fixed_component_list=fixed_list,
        fixes_applied=fixes
    )
