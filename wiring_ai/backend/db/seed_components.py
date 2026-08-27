# creates/fills component database
# Usually a one time operation to seed the database

import sqlite3
import json

DB_NAME = "wiring_ai.db"

components = [
    # 1. Arduino Uno
    {
        "id": "arduino_uno",
        "name": "Arduino Uno",
        "category": "board",
        "description": "Beginner-friendly microcontroller board.",
        "pins": [
            {"name": "D0", "type": "digital_io", "voltage": 5, "required": False, "notes": "Reserved for USB serial RX. Avoid using."},
            {"name": "D1", "type": "digital_io", "voltage": 5, "required": False, "notes": "Reserved for USB serial TX. Avoid using."},
            {"name": "D2", "type": "digital_io", "voltage": 5, "required": False, "notes": "Interrupt capable."},
            {"name": "D3", "type": "digital_io", "voltage": 5, "required": False, "notes": "PWM and interrupt capable."},
            {"name": "D4", "type": "digital_io", "voltage": 5, "required": False},
            {"name": "D5", "type": "digital_io", "voltage": 5, "required": False, "notes": "PWM capable."},
            {"name": "D6", "type": "digital_io", "voltage": 5, "required": False, "notes": "PWM capable."},
            {"name": "D7", "type": "digital_io", "voltage": 5, "required": False},
            {"name": "D8", "type": "digital_io", "voltage": 5, "required": False},
            {"name": "D9", "type": "digital_io", "voltage": 5, "required": False, "notes": "PWM capable."},
            {"name": "D10", "type": "digital_io", "voltage": 5, "required": False, "notes": "PWM and SPI SS capable."},
            {"name": "D11", "type": "digital_io", "voltage": 5, "required": False, "notes": "PWM and SPI MOSI capable."},
            {"name": "D12", "type": "digital_io", "voltage": 5, "required": False, "notes": "SPI MISO capable."},
            {"name": "D13", "type": "digital_io", "voltage": 5, "required": False, "notes": "Pin 13 has onboard LED — may interfere with external circuits."},
            {"name": "A0", "type": "analog", "voltage": 5, "required": False},
            {"name": "A1", "type": "analog", "voltage": 5, "required": False},
            {"name": "A2", "type": "analog", "voltage": 5, "required": False},
            {"name": "A3", "type": "analog", "voltage": 5, "required": False},
            {"name": "A4", "type": "analog", "voltage": 5, "required": False, "notes": "I2C SDA. Also usable as digital/analog IO."},
            {"name": "A5", "type": "analog", "voltage": 5, "required": False, "notes": "I2C SCL. Also usable as digital/analog IO."},
            {"name": "5V", "type": "power", "voltage": 5, "required": False, "notes": "5V regulated output power rail."},
            {"name": "3.3V", "type": "power", "voltage": 3.3, "required": False, "notes": "3.3V regulated output power rail (150mA max)."},
            {"name": "GND", "type": "ground", "voltage": 0, "required": False, "notes": "Ground connection (common negative reference)."},
            {"name": "VIN", "type": "power", "voltage": 12, "required": False, "notes": "Input voltage rail (7-12V barrel jack or external)."},
            {"name": "AREF", "type": "analog", "voltage": 5, "required": False, "notes": "Analog reference voltage."}
        ],
        "power": {
            "voltage": 5.0,
            "voltage_tolerance": [4.5, 5.5],
            "current_mA": 50.0,
            "current_max_mA": 200.0
        },
        "constraints": [],
        "compatible_boards": [],
        "tags": ["mcu", "board", "microcontroller", "arduino", "uno"],
        "_needs_review": False,
        
        # Board fields
        "board_pins": [
            {"pin_id": "D0", "label": "0", "capabilities": ["digital", "uart_rx"], "voltage": 5.0, "max_current_mA": 40.0, "reserved": True, "reserved_reason": "Reserved for USB serial RX. Avoid using in circuits to prevent interference with uploading code."},
            {"pin_id": "D1", "label": "1", "capabilities": ["digital", "uart_tx"], "voltage": 5.0, "max_current_mA": 40.0, "reserved": True, "reserved_reason": "Reserved for USB serial TX. Avoid using in circuits to prevent interference with uploading code."},
            {"pin_id": "D2", "label": "2", "capabilities": ["digital", "interrupt"], "voltage": 5.0, "max_current_mA": 40.0, "reserved": False},
            {"pin_id": "D3", "label": "3", "capabilities": ["digital", "pwm", "interrupt"], "voltage": 5.0, "max_current_mA": 40.0, "reserved": False},
            {"pin_id": "D4", "label": "4", "capabilities": ["digital"], "voltage": 5.0, "max_current_mA": 40.0, "reserved": False},
            {"pin_id": "D5", "label": "5", "capabilities": ["digital", "pwm"], "voltage": 5.0, "max_current_mA": 40.0, "reserved": False},
            {"pin_id": "D6", "label": "6", "capabilities": ["digital", "pwm"], "voltage": 5.0, "max_current_mA": 40.0, "reserved": False},
            {"pin_id": "D7", "label": "7", "capabilities": ["digital"], "voltage": 5.0, "max_current_mA": 40.0, "reserved": False},
            {"pin_id": "D8", "label": "8", "capabilities": ["digital"], "voltage": 5.0, "max_current_mA": 40.0, "reserved": False},
            {"pin_id": "D9", "label": "9", "capabilities": ["digital", "pwm"], "voltage": 5.0, "max_current_mA": 40.0, "reserved": False},
            {"pin_id": "D10", "label": "10", "capabilities": ["digital", "pwm", "spi_ss"], "voltage": 5.0, "max_current_mA": 40.0, "reserved": False},
            {"pin_id": "D11", "label": "11", "capabilities": ["digital", "pwm", "spi_mosi"], "voltage": 5.0, "max_current_mA": 40.0, "reserved": False},
            {"pin_id": "D12", "label": "12", "capabilities": ["digital", "spi_miso"], "voltage": 5.0, "max_current_mA": 40.0, "reserved": False},
            {"pin_id": "D13", "label": "13", "capabilities": ["digital", "spi_sck"], "voltage": 5.0, "max_current_mA": 40.0, "reserved": False, "notes": "Pin 13 has onboard LED"},
            {"pin_id": "A0", "label": "A0", "capabilities": ["analog", "digital"], "voltage": 5.0, "max_current_mA": 40.0, "reserved": False},
            {"pin_id": "A1", "label": "A1", "capabilities": ["analog", "digital"], "voltage": 5.0, "max_current_mA": 40.0, "reserved": False},
            {"pin_id": "A2", "label": "A2", "capabilities": ["analog", "digital"], "voltage": 5.0, "max_current_mA": 40.0, "reserved": False},
            {"pin_id": "A3", "label": "A3", "capabilities": ["analog", "digital"], "voltage": 5.0, "max_current_mA": 40.0, "reserved": False},
            {"pin_id": "A4", "label": "A4", "capabilities": ["analog", "digital", "i2c_sda"], "voltage": 5.0, "max_current_mA": 40.0, "reserved": False},
            {"pin_id": "A5", "label": "A5", "capabilities": ["analog", "digital", "i2c_scl"], "voltage": 5.0, "max_current_mA": 40.0, "reserved": False},
            {"pin_id": "5V", "label": "5V", "capabilities": ["power_5v"], "voltage": 5.0, "max_current_mA": 500.0, "reserved": False},
            {"pin_id": "3V3", "label": "3.3V", "capabilities": ["power_3v3"], "voltage": 3.3, "max_current_mA": 150.0, "reserved": False},
            {"pin_id": "GND1", "label": "GND", "capabilities": ["ground"], "voltage": 0.0, "max_current_mA": 400.0, "reserved": False},
            {"pin_id": "GND2", "label": "GND", "capabilities": ["ground"], "voltage": 0.0, "max_current_mA": 400.0, "reserved": False},
            {"pin_id": "GND3", "label": "GND", "capabilities": ["ground"], "voltage": 0.0, "max_current_mA": 400.0, "reserved": False},
            {"pin_id": "VIN", "label": "VIN", "capabilities": ["power_vin"], "voltage": 12.0, "max_current_mA": 1000.0, "reserved": False},
            {"pin_id": "AREF", "label": "AREF", "capabilities": ["analog"], "voltage": 5.0, "max_current_mA": 1.0, "reserved": False}
        ],
        "operating_voltage": 5.0,
        "input_voltage_range": [7.0, 12.0],
        "max_current_per_pin_mA": 40.0,
        "max_5v_rail_mA": 500.0,
        "max_3v3_rail_mA": 150.0,
        "total_digital_pins": 14,
        "total_analog_pins": 6,
        "total_pwm_pins": 6,
        "has_wifi": False,
        "has_bluetooth": False,
        "power": {"logic_voltage": 5.0, "voltage_range": [5.0, 5.0], "operating_current_mA": 500.0, "is_external_powered": False},
        "interface": {"protocol": "gpio", "i2c_address": None},
    },
    # 2. Breadboard
    {
        "id": "breadboard",
        "name": "Breadboard",
        "category": "platform",
        "description": "Used for building temporary circuits.",
        "pins": [],
        "power": {
            "voltage": 0.0,
            "current_mA": 0.0
        },
        "constraints": [],
        "compatible_boards": ["arduino_uno"],
        "tags": ["breadboard", "prototyping", "solderless", "board"],
        "_needs_review": False
    },
    # 3. HC-SR04
    {
        "id": "hc_sr04",
        "name": "HC-SR04 Ultrasonic Sensor",
        "category": "sensor",
        "description": "Measures distance using ultrasonic sound.",
        "pins": [
            {"name": "VCC", "type": "power", "voltage": 5.0, "required": True, "notes": "5V power supply"},
            {"name": "TRIG", "type": "digital ", "voltage": 5.0, "required": True, "notes": "Trigger pin. Needs minimum 10μs HIGH pulse"},
            {"name": "ECHO", "type": "digital ", "voltage": 5.0, "required": True, "notes": "Echo pin. Outputs 5V TTL pulse proportional to distance"},
            {"name": "GND", "type": "ground", "voltage": 0.0, "required": True, "notes": "Ground connection"}
        ],
        "power": {
            "voltage": 5.0,
            "voltage_tolerance": [4.5, 5.5],
            "current_mA": 15.0,
            "current_max_mA": 15.0
        },
        "constraints": [
            {
                "type": "voltage_mismatch_risk",
                "condition": "ECHO connected to a board with 3.3V logic level (e.g. ESP32 or Raspberry Pi Pico). ECHO pin outputs 5V TTL which can damage 3.3V GPIO pins.",
                "resolution": "Use a voltage divider (1kΩ and 2kΩ resistors) or a logic level shifter on the ECHO pin connection to step down 5V to 3.3V.",
                "auto_fixable": False,
                "severity": "danger"
            }
        ],
        "compatible_boards": ["arduino_uno"],
        "tags": ["distance", "ultrasonic", "proximity", "sensor"],
        "_needs_review": False
    },
    # 4. DHT11
    {
        "id": "dht11",
        "name": "DHT11 Temperature Sensor",
        "category": "sensor",
        "description": "Measures temperature and humidity.",
        "pins": [
            {"name": "VCC", "type": "power", "voltage": 5.0, "required": True, "notes": "3V to 5.5V power supply"},
            {"name": "DATA", "type": "digital", "required": True, "notes": "Bidirectional single-bus data line. Requires a 4.7kΩ or 10kΩ pull-up resistor to VCC."},
            {"name": "GND", "type": "ground", "voltage": 0.0, "required": True, "notes": "Ground connection"}
        ],
        "power": {
            "voltage": 5.0,
            "voltage_tolerance": [3.0, 5.5],
            "current_mA": 1.0,
            "current_max_mA": 2.5
        },
        "constraints": [
            {
                "type": "requires_pullup",
                "condition": "DHT11 data pin connected without pull-up resistor.",
                "resolution": "Add a 4.7kΩ (or 10kΩ) pull-up resistor between VCC and the DHT11 DATA pin.",
                "auto_fixable": True,
                "fix_component_id": "resistor_4k7",
                "severity": "warning"
            }
        ],
        "compatible_boards": ["arduino_uno"],
        "tags": ["temperature", "humidity", "weather", "sensor"],
        "_needs_review": True,
        "_review_notes": "Current draw during active conversion and transmission needs validation against official Aosong datasheet."
    },
    # 5. Photoresistor (LDR)
    {
        "id": "ldr",
        "name": "Photoresistor LDR",
        "category": "sensor",
        "description": "Changes resistance based on light level.",
        "pins": [
            {"name": "leg_1", "type": "passive", "required": True, "notes": "Pin 1 of photoresistor (interchangeable)"},
            {"name": "leg_2", "type": "passive", "required": True, "notes": "Pin 2 of photoresistor (interchangeable)"}
        ],
        "power": {
            "voltage": 0.0,
            "current_mA": 0.0
        },
        "constraints": [
            {
                "type": "requires_pullup",
                "condition": "Photoresistor connected without pull-down series resistor to form voltage divider.",
                "resolution": "Connect a 10kΩ pull-down resistor in series with LDR leg_2 to GND, and read analog voltage from the node between LDR and resistor.",
                "auto_fixable": True,
                "fix_component_id": "resistor_10k",
                "severity": "warning"
            }
        ],
        "compatible_boards": ["arduino_uno"],
        "tags": ["light", "ldr", "photoresistor", "analog", "sensor"],
        "_needs_review": False
    },
    # 6. Red LED
    {
        "id": "led_red",
        "name": "Red LED",
        "category": "output",
        "description": "Simple red light output.",
        "pins": [
            {"name": "anode", "type": "digital ", "voltage": 2.0, "required": True, "notes": "Positive lead (longer leg). Connects through series resistor."},
            {"name": "cathode", "type": "ground", "voltage": 0.0, "required": True, "notes": "Negative lead (shorter leg, flat side). Connects to GND."}
        ],
        "power": {
            "voltage": 2.0,
            "voltage_tolerance": [1.8, 2.2],
            "current_mA": 10.0,
            "current_max_mA": 20.0
        },
        "constraints": [
            {
                "type": "requires_resistor",
                "condition": "Red LED connected without series current-limiting resistor.",
                "resolution": "Add a 220Ω resistor in series with Red LED anode when using a 5V board.",
                "auto_fixable": True,
                "fix_component_id": "resistor_220",
                "severity": "danger"
            }
        ],
        "compatible_boards": ["arduino_uno"],
        "tags": ["led", "red", "light", "indicator"],
        "_needs_review": False
    },
    # 7. Green LED
    {
        "id": "led_green",
        "name": "Green LED",
        "category": "output",
        "description": "Simple green light output.",
        "pins": [
            {"name": "anode", "type": "digital ", "voltage": 2.2, "required": True, "notes": "Positive lead (longer leg). Connects through series resistor."},
            {"name": "cathode", "type": "ground", "voltage": 0.0, "required": True, "notes": "Negative lead (shorter leg, flat side). Connects to GND."}
        ],
        "power": {
            "voltage": 2.2,
            "voltage_tolerance": [2.0, 3.2],
            "current_mA": 10.0,
            "current_max_mA": 20.0
        },
        "constraints": [
            {
                "type": "requires_resistor",
                "condition": "Green LED connected without series current-limiting resistor.",
                "resolution": "Add a 220Ω resistor in series with Green LED anode when using a 5V board.",
                "auto_fixable": True,
                "fix_component_id": "resistor_220",
                "severity": "danger"
            }
        ],
        "compatible_boards": ["arduino_uno"],
        "tags": ["led", "green", "light", "indicator"],
        "_needs_review": True,
        "_review_notes": "Verify exact forward voltage for the green LED (typically 2.2V - 3.2V depending on chemical composition)."
    },
    # 8. Active Buzzer
    {
        "id": "buzzer",
        "name": "Active Buzzer",
        "category": "output",
        "description": "Produces sound when power is applied.",
        "pins": [
            {"name": "positive", "type": "digital ", "voltage": 5.0, "required": True, "notes": "Connect to a digital/PWM pin"},
            {"name": "negative", "type": "ground", "voltage": 0.0, "required": True, "notes": "Connect to GND"}
        ],
        "power": {
            "voltage": 5.0,
            "voltage_tolerance": [4.0, 6.0],
            "current_mA": 30.0,
            "current_max_mA": 40.0
        },
        "constraints": [
            {
                "type": "max_current_exceeded",
                "condition": "Active buzzer current draw exceeds microcontroller GPIO pin safety limit.",
                "resolution": "Use a transistor switch circuit (e.g. PN2222 NPN) if buzzer draws more than 20mA from a GPIO pin.",
                "auto_fixable": False,
                "severity": "warning"
            }
        ],
        "compatible_boards": ["arduino_uno"],
        "tags": ["buzzer", "sound", "audio", "active"],
        "_needs_review": True,
        "_review_notes": "Verify current draw limit — some active buzzers draw up to 35mA, which exceeds recommended 20mA Arduino pin limit."
    },
    # 9. Push Button
    {
        "id": "button",
        "name": "Push Button",
        "category": "input",
        "description": "Simple digital input switch.",
        "pins": [
            {"name": "leg_1", "type": "passive", "required": True},
            {"name": "leg_2", "type": "passive", "required": True}
        ],
        "power": {
            "voltage": 0.0,
            "current_mA": 0.0
        },
        "constraints": [
            {
                "type": "requires_pullup",
                "condition": "Push button connected without a pull-up or pull-down resistor.",
                "resolution": "Enable internal pull-up in code (INPUT_PULLUP) or add a 10kΩ pull-down resistor.",
                "auto_fixable": False,
                "severity": "warning"
            }
        ],
        "compatible_boards": ["arduino_uno"],
        "tags": ["button", "switch", "input", "digital"],
        "_needs_review": False
    },
    # 10. Potentiometer
    {
        "id": "potentiometer",
        "name": "Potentiometer",
        "category": "input",
        "description": "Variable resistor for analog input.",
        "pins": [
            {"name": "VCC", "type": "power", "voltage": 5.0, "required": True, "notes": "Connect to VCC rail (5V or 3.3V)"},
            {"name": "OUT", "type": "analog", "voltage": 5.0, "required": True, "notes": "Connect to analog input pin"},
            {"name": "GND", "type": "ground", "voltage": 0.0, "required": True, "notes": "Connect to GND rail"}
        ],
        "power": {
            "voltage": 5.0,
            "voltage_tolerance": [0.0, 5.5],
            "current_mA": 0.5,
            "current_max_mA": 1.0
        },
        "constraints": [],
        "compatible_boards": ["arduino_uno"],
        "tags": ["potentiometer", "analog", "input", "dial", "knob"],
        "_needs_review": False
    },
    # 11. Servo SG90
    {
        "id": "servo_sg90",
        "name": "Servo SG90",
        "category": "actuator",
        "description": "Micro servo motor SG90.",
        "pins": [
            {"name": "VCC", "type": "power", "voltage": 5.0, "required": True, "notes": "Red wire. Connect to 5V rail."},
            {"name": "GND", "type": "ground", "voltage": 0.0, "required": True, "notes": "Brown wire. Connect to GND."},
            {"name": "PWM", "type": "digital ", "voltage": 5.0, "required": True, "notes": "Orange wire. Connect to PWM-capable pin."}
        ],
        "power": {
            "voltage": 5.0,
            "voltage_tolerance": [4.8, 6.0],
            "current_mA": 250.0,
            "current_max_mA": 650.0
        },
        "constraints": [
            {
                "type": "max_current_exceeded",
                "condition": "Servo stall/operating current exceeds Arduino's 5V regulator limit if multiple components are active.",
                "resolution": "Provide external power supply (e.g. 5V battery) for the servo, connecting the external GND to Arduino GND.",
                "auto_fixable": False,
                "severity": "warning"
            }
        ],
        "compatible_boards": ["arduino_uno"],
        "tags": ["servo", "motor", "actuator", "sg90"],
        "_needs_review": True,
        "_review_notes": "SG90 stall current is ~650mA; check if running directly off Arduino 5V pin is safe for light loads."
    },
    # 12. 220Ω Resistor
    {
        "id": "resistor_220",
        "name": "220 Ohm Resistor",
        "category": "passive",
        "description": "Current-limiting resistor, common for LEDs.",
        "pins": [
            {"name": "pin1", "type": "passive", "required": True},
            {"name": "pin2", "type": "passive", "required": True}
        ],
        "power": {
            "voltage": 0.0,
            "current_mA": 0.0
        },
        "constraints": [],
        "compatible_boards": ["arduino_uno"],
        "tags": ["resistor", "passive", "current-limiting", "220"],
        "_needs_review": False
    },
    # 13. 1kΩ Resistor
    {
        "id": "resistor_1k",
        "name": "1k Ohm Resistor",
        "category": "passive",
        "description": "1k Ohm Resistor.",
        "pins": [
            {"name": "pin1", "type": "passive", "required": True},
            {"name": "pin2", "type": "passive", "required": True}
        ],
        "power": {
            "voltage": 0.0,
            "current_mA": 0.0
        },
        "constraints": [],
        "compatible_boards": ["arduino_uno"],
        "tags": ["resistor", "passive", "1k"],
        "_needs_review": False
    },
    # 14. 10kΩ Resistor
    {
        "id": "resistor_10k",
        "name": "10k Ohm Resistor",
        "category": "passive",
        "description": "10k Ohm Resistor.",
        "pins": [
            {"name": "pin1", "type": "passive", "required": True},
            {"name": "pin2", "type": "passive", "required": True}
        ],
        "power": {
            "voltage": 0.0,
            "current_mA": 0.0
        },
        "constraints": [],
        "compatible_boards": ["arduino_uno"],
        "tags": ["resistor", "passive", "10k"],
        "_needs_review": False
    },
    # 15. 4.7kΩ Resistor
    {
        "id": "resistor_4k7",
        "name": "4.7k Ohm Resistor",
        "category": "passive",
        "description": "4.7k Ohm Resistor.",
        "pins": [
            {"name": "pin1", "type": "passive", "required": True},
            {"name": "pin2", "type": "passive", "required": True}
        ],
        "power": {
            "voltage": 0.0,
            "current_mA": 0.0
        },
        "constraints": [],
        "compatible_boards": ["arduino_uno"],
        "tags": ["resistor", "passive", "4.7k"],
        "_needs_review": False
    },

    # 16. Breadboard Power Supply Module
    {
        "id": "power_supply_module",
        "name": "Breadboard Power Supply Module",
        "category": "power",
        "description": "Breadboard-mountable power supply with selectable 3.3V/5V dual output rails. Accepts 6.5V-12V DC barrel jack or 5V USB. Max 700mA per rail. Independently switchable rails A and B.",
        "pins": [
            {"name": "OUT_A", "type": "power", "required": False, "notes": "Rail A output — jumper-selectable 3.3V or 5V. To breadboard +ve rail side A."},
            {"name": "OUT_B", "type": "power", "required": False, "notes": "Rail B output — jumper-selectable 3.3V or 5V. To breadboard +ve rail side B."},
            {"name": "GND_A", "type": "ground", "required": True, "notes": "Ground for rail A. To breadboard -ve rail side A."},
            {"name": "GND_B", "type": "ground", "required": True, "notes": "Ground for rail B. To breadboard -ve rail side B."},
            {"name": "DC_IN", "type": "power", "required": True, "notes": "6.5V-12V DC barrel jack input (centre-positive 5.5x2.1mm)."},
            {"name": "USB_IN", "type": "power", "required": False, "notes": "Mini-USB 5V input alternative."},
            {"name": "ON_OFF", "type": "digital ", "required": False, "notes": "Slide switch to enable/disable output."}
        ],
        "power": {"voltage": 5.0, "voltage_tolerance": [3.3, 5.0], "current_mA": 700.0, "current_max_mA": 700.0},
        "constraints": [
            {"type": "shared_ground", "condition": "Module GND not connected to Arduino GND when both sources active.", "resolution": "Always connect module GND rail to Arduino GND for common reference. Floating grounds cause undefined logic levels.", "auto_fixable": False, "severity": "danger"},
            {"type": "input_voltage_range", "condition": "Input below 6.5V or above 12V on DC jack.", "resolution": "Use 7V-12V adapter or 5V USB. Outside range causes under-voltage or IC damage.", "auto_fixable": False, "severity": "danger"}
        ],
        "compatible_boards": ["arduino_uno"],
        "tags": ["power", "supply", "breadboard", "3.3v", "5v", "regulator", "module"],
        "_needs_review": False
    },

    # 17. 10kΩ NTC Thermistor
    {
        "id": "thermistor_10k",
        "name": "10k NTC Thermistor",
        "category": "sensor",
        "description": "Negative Temperature Coefficient thermistor, 10kΩ at 25°C (B=3950K). Resistance falls as temperature rises. Used in voltage-divider with a 10kΩ fixed resistor on analog input. Range: -55°C to +125°C.",
        "pins": [
            {"name": "leg_1", "type": "passive", "required": True, "notes": "Terminal 1 — polarity-insensitive. Connect to VCC side of voltage divider."},
            {"name": "leg_2", "type": "passive", "required": True, "notes": "Terminal 2 — connect through 10kΩ resistor to GND. Read analog voltage at junction."}
        ],
        "power": {"voltage": 0.0, "current_mA": 0.0},
        "constraints": [
            {"type": "requires_voltage_divider", "condition": "Thermistor connected directly to analog pin without series resistor.", "resolution": "Wire thermistor between VCC and analog pin, add 10kΩ from analog pin to GND. Read junction voltage to compute resistance and temperature.", "auto_fixable": True, "fix_component_id": "resistor_10k", "severity": "warning"}
        ],
        "compatible_boards": ["arduino_uno"],
        "tags": ["thermistor", "ntc", "temperature", "analog", "sensor", "10k"],
        "_needs_review": False
    },

    # 18. SW-520D Tilt Ball Switch
    {
        "id": "tilt_switch_sw520d",
        "name": "SW-520D Tilt Ball Switch",
        "category": "sensor",
        "description": "Mercury-free tilt sensor. Conductive ball bearing inside cylindrical housing completes circuit when tilted beyond ~45°. Acts as a digital switch for orientation, vibration, or motion detection.",
        "pins": [
            {"name": "pin_a", "type": "passive", "required": True, "notes": "Terminal A — connect to digital input pin with pull-up resistor."},
            {"name": "pin_b", "type": "passive", "required": True, "notes": "Terminal B — connect to GND. Polarity-insensitive."}
        ],
        "power": {"voltage": 0.0, "current_mA": 0.0},
        "constraints": [
            {"type": "requires_pullup", "condition": "Tilt switch connected to digital input without pull-up, causing floating pin.", "resolution": "Use INPUT_PULLUP in code or add 10kΩ pull-up from input pin to VCC. Reads LOW when tilted (closed), HIGH when upright (open).", "auto_fixable": False, "severity": "warning"}
        ],
        "compatible_boards": ["arduino_uno"],
        "tags": ["tilt", "sw520d", "switch", "orientation", "motion", "sensor"],
        "_needs_review": False
    },

    # 19. 1N4007 Rectifier Diode
    {
        "id": "diode_1n4007",
        "name": "1N4007 Rectifier Diode",
        "category": "passive",
        "description": "General-purpose silicon rectifier diode. 1A forward current, 1000V PIV, ~0.7V forward voltage drop. Used as flyback protection across inductive loads (relays, motors) and in rectifier circuits.",
        "pins": [
            {"name": "anode", "type": "digital ", "voltage": 0.7, "required": True, "notes": "Positive terminal (no band). Current flows in during forward bias."},
            {"name": "cathode", "type": "digital ", "voltage": 0.7, "required": True, "notes": "Negative terminal (silver/white stripe). Current exits here."}
        ],
        "power": {"voltage": 0.7, "voltage_tolerance": [0.6, 1.1], "current_mA": 1000.0, "current_max_mA": 1000.0},
        "constraints": [
            {"type": "flyback_orientation", "condition": "Diode installed with wrong polarity for flyback protection on relay/motor.", "resolution": "For flyback protection: place anode toward GND, cathode toward VCC across the inductive load. Diode clamps reverse EMF spikes.", "auto_fixable": False, "severity": "warning"}
        ],
        "compatible_boards": ["arduino_uno"],
        "tags": ["diode", "1n4007", "rectifier", "flyback", "protection", "passive"],
        "_needs_review": False
    },

    # 20. PN2222 NPN Transistor
    {
        "id": "transistor_pn2222",
        "name": "PN2222 NPN Transistor",
        "category": "passive",
        "description": "General-purpose NPN BJT in TO-92 package. 600mA collector current, 40V VCEO, hFE~100 at 10mA. Used as digital switch to drive loads beyond Arduino 20mA GPIO limit (relays, motors, buzzers). Requires base resistor.",
        "pins": [
            {"name": "emitter", "type": "ground", "voltage": 0.0, "required": True, "notes": "Emitter — connect to GND. Leftmost pin on flat-side-facing TO-92 package."},
            {"name": "base", "type": "digital ", "voltage": 5.0, "required": True, "notes": "Base — control input via 1kΩ resistor from Arduino GPIO. HIGH turns transistor ON."},
            {"name": "collector", "type": "digital ", "voltage": 5.0, "required": True, "notes": "Collector — connects to negative terminal of load. Load positive connects to VCC. Rightmost pin on flat-facing TO-92."}
        ],
        "power": {"voltage": 5.0, "voltage_tolerance": [0.0, 40.0], "current_mA": 100.0, "current_max_mA": 600.0},
        "constraints": [
            {"type": "requires_base_resistor", "condition": "Base connected directly to GPIO without current-limiting resistor.", "resolution": "Add 1kΩ in series with base. Limits base current to ~4mA at 5V, providing saturation drive for IC<100mA.", "auto_fixable": True, "fix_component_id": "resistor_1k", "severity": "danger"},
            {"type": "flyback_protection", "condition": "Inductive load at collector without flyback diode.", "resolution": "Place 1N4007 diode across inductive load — cathode to VCC, anode to collector — to clamp back-EMF spikes.", "auto_fixable": True, "fix_component_id": "diode_1n4007", "severity": "danger"}
        ],
        "compatible_boards": ["arduino_uno"],
        "tags": ["transistor", "pn2222", "npn", "bjt", "switch", "driver", "passive"],
        "_needs_review": False
    },

    # 21. Passive Buzzer
    {
        "id": "buzzer_passive",
        "name": "Passive Buzzer",
        "category": "output",
        "description": "Passive piezoelectric buzzer with no internal oscillator. Requires external PWM square wave to produce sound. Frequency determines pitch. Use Arduino tone() function on a PWM pin. Range: 1kHz-5kHz typical.",
        "pins": [
            {"name": "positive", "type": "digital ", "voltage": 5.0, "required": True, "notes": "Positive terminal (+). Connect to PWM-capable pin (D3/D5/D6/D9/D10/D11). Use tone(pin, freq)."},
            {"name": "negative", "type": "ground", "voltage": 0.0, "required": True, "notes": "Negative terminal. Connect to GND."}
        ],
        "power": {"voltage": 5.0, "voltage_tolerance": [3.0, 5.5], "current_mA": 20.0, "current_max_mA": 30.0},
        "constraints": [
            {"type": "requires_pwm_pin", "condition": "Passive buzzer connected to non-PWM digital pin.", "resolution": "Connect to PWM pin (D3/D5/D6/D9/D10/D11) and use tone(pin, frequency). A plain HIGH/LOW produces no sound.", "auto_fixable": False, "severity": "warning"}
        ],
        "compatible_boards": ["arduino_uno"],
        "tags": ["buzzer", "passive", "piezo", "sound", "audio", "pwm", "tone"],
        "_needs_review": False
    },

    # 22. 3-6V DC Toy Motor
    {
        "id": "dc_motor_toy",
        "name": "3-6V DC Toy Motor",
        "category": "actuator",
        "description": "Small brushed DC motor (130-size, RE-130 equivalent). 3V-6V operating range. No-load ~70mA at 3V, stall up to 800mA. ~8000-15000 RPM no-load. Cannot drive from GPIO directly — needs transistor or motor driver IC.",
        "pins": [
            {"name": "terminal_positive", "type": "power", "voltage": 5.0, "required": True, "notes": "Motor + terminal. Connect to collector of PN2222 or motor driver output. Swap polarity to reverse direction."},
            {"name": "terminal_negative", "type": "ground", "voltage": 0.0, "required": True, "notes": "Motor - terminal. Connect to GND."}
        ],
        "power": {"voltage": 5.0, "voltage_tolerance": [3.0, 6.0], "current_mA": 70.0, "current_max_mA": 800.0},
        "constraints": [
            {"type": "max_current_exceeded", "condition": "DC motor connected directly to Arduino GPIO.", "resolution": "Drive via PN2222 transistor: GPIO → 1kΩ → Base, Collector → motor(-), motor(+) → 5V. Add 1N4007 flyback diode across motor terminals.", "auto_fixable": False, "severity": "danger"},
            {"type": "flyback_protection", "condition": "Motor connected without flyback diode.", "resolution": "Place 1N4007 diode across motor terminals — cathode toward VCC, anode toward GND — to clamp back-EMF spikes.", "auto_fixable": True, "fix_component_id": "diode_1n4007", "severity": "danger"}
        ],
        "compatible_boards": ["arduino_uno"],
        "tags": ["motor", "dc", "toy", "actuator", "fan", "brushed", "130"],
        "_needs_review": False
    },

    # 23. Blue LED
    {
        "id": "led_blue",
        "name": "Blue LED",
        "category": "output",
        "description": "Blue GaN LED. Forward voltage ~3.0V-3.4V (higher than red/green). Requires correctly sized resistor — smaller value than red/green due to higher Vf. Typical current 10mA-20mA.",
        "pins": [
            {"name": "anode", "type": "digital ", "voltage": 3.2, "required": True, "notes": "Positive lead (longer leg). Connect through 180Ω resistor to GPIO or VCC."},
            {"name": "cathode", "type": "ground", "voltage": 0.0, "required": True, "notes": "Negative lead (shorter leg, flat side). Connect to GND."}
        ],
        "power": {"voltage": 3.2, "voltage_tolerance": [3.0, 3.4], "current_mA": 10.0, "current_max_mA": 20.0},
        "constraints": [
            {"type": "requires_resistor", "condition": "Blue LED connected without series resistor from 5V supply.", "resolution": "Add 180Ω resistor in series: R = (5V - 3.2V) / 0.010A = 180Ω for 10mA. Use 100Ω for ~18mA.", "auto_fixable": False, "severity": "danger"}
        ],
        "compatible_boards": ["arduino_uno"],
        "tags": ["led", "blue", "light", "indicator", "gan"],
        "_needs_review": False
    },

    # 24. Yellow LED
    {
        "id": "led_yellow",
        "name": "Yellow LED",
        "category": "output",
        "description": "Yellow AlInGaP LED. Forward voltage ~1.8V-2.2V, similar to red. Typical current 10mA-20mA. Use 220Ω series resistor at 5V. Common for status and warning indicators.",
        "pins": [
            {"name": "anode", "type": "digital ", "voltage": 2.0, "required": True, "notes": "Positive lead (longer leg). Connect through 220Ω resistor to GPIO or VCC."},
            {"name": "cathode", "type": "ground", "voltage": 0.0, "required": True, "notes": "Negative lead (shorter leg, flat side). Connect to GND."}
        ],
        "power": {"voltage": 2.0, "voltage_tolerance": [1.8, 2.2], "current_mA": 10.0, "current_max_mA": 20.0},
        "constraints": [
            {"type": "requires_resistor", "condition": "Yellow LED connected without series current-limiting resistor.", "resolution": "Add 220Ω resistor in series with anode at 5V: R = (5V - 2.0V) / 0.010A = 300Ω; 220Ω gives ~14mA.", "auto_fixable": True, "fix_component_id": "resistor_220", "severity": "danger"}
        ],
        "compatible_boards": ["arduino_uno"],
        "tags": ["led", "yellow", "light", "indicator", "status"],
        "_needs_review": False
    },

    # 25. RGB Common Cathode LED
    {
        "id": "led_rgb",
        "name": "RGB Common Cathode LED",
        "category": "output",
        "description": "4-pin RGB LED, common cathode. Three LED dice (R/G/B) share one GND. Each channel driven individually with its own resistor. Mix PWM for any colour. Vf: Red~2.0V, Green~2.2V, Blue~3.2V.",
        "pins": [
            {"name": "red_anode", "type": "digital ", "voltage": 2.0, "required": True, "notes": "Red channel anode. Through 220Ω to PWM GPIO. Longest leg on through-hole package."},
            {"name": "common_cathode", "type": "ground", "voltage": 0.0, "required": True, "notes": "Common cathode (GND). Second-longest pin, next to red anode."},
            {"name": "green_anode", "type": "digital ", "voltage": 2.2, "required": True, "notes": "Green channel anode. Through 220Ω to PWM GPIO."},
            {"name": "blue_anode", "type": "digital ", "voltage": 3.2, "required": True, "notes": "Blue channel anode. Through 100Ω-180Ω to PWM GPIO (higher Vf = smaller resistor from 5V)."}
        ],
        "power": {"voltage": 3.2, "voltage_tolerance": [2.0, 3.4], "current_mA": 20.0, "current_max_mA": 60.0},
        "constraints": [
            {"type": "requires_resistor", "condition": "RGB channel connected without current-limiting resistor.", "resolution": "Each channel needs its own resistor: Red/Green → 220Ω, Blue → 180Ω at 5V. Never share one resistor — different Vf causes unequal brightness.", "auto_fixable": True, "fix_component_id": "resistor_220", "severity": "danger"},
            {"type": "requires_pwm_for_colour_mixing", "condition": "RGB connected to non-PWM pins for colour mixing.", "resolution": "Connect R/G/B to PWM pins (D3/D5/D6/D9/D10/D11) and use analogWrite() for smooth blending.", "auto_fixable": False, "severity": "info"}
        ],
        "compatible_boards": ["arduino_uno"],
        "tags": ["led", "rgb", "colour", "common-cathode", "pwm", "light"],
        "_needs_review": False
    },

    # 26. 1-Digit 7-Segment LED Display
    {
        "id": "display_7seg_1dig",
        "name": "1-Digit 7-Segment LED Display",
        "category": "display",
        "description": "Single-digit common cathode 7-segment display. Segments A-G + decimal point. Requires 8 GPIO pins + GND driven directly, or use 74HC595 to save pins. Vf ~2.0V per segment, 10mA-15mA each.",
        "pins": [
            {"name": "seg_a", "type": "digital ", "voltage": 2.0, "required": False, "notes": "Segment A — top horizontal bar. Through 220Ω to GPIO."},
            {"name": "seg_b", "type": "digital ", "voltage": 2.0, "required": False, "notes": "Segment B — upper-right vertical bar."},
            {"name": "seg_c", "type": "digital ", "voltage": 2.0, "required": False, "notes": "Segment C — lower-right vertical bar."},
            {"name": "seg_d", "type": "digital ", "voltage": 2.0, "required": False, "notes": "Segment D — bottom horizontal bar."},
            {"name": "seg_e", "type": "digital ", "voltage": 2.0, "required": False, "notes": "Segment E — lower-left vertical bar."},
            {"name": "seg_f", "type": "digital ", "voltage": 2.0, "required": False, "notes": "Segment F — upper-left vertical bar."},
            {"name": "seg_g", "type": "digital ", "voltage": 2.0, "required": False, "notes": "Segment G — middle horizontal bar."},
            {"name": "seg_dp", "type": "digital ", "voltage": 2.0, "required": False, "notes": "Decimal point segment. Optional."},
            {"name": "common_cathode_1", "type": "ground", "voltage": 0.0, "required": True, "notes": "Common cathode pin 1 (package pin 3). Connect to GND."},
            {"name": "common_cathode_2", "type": "ground", "voltage": 0.0, "required": True, "notes": "Common cathode pin 2 (package pin 8). Connect to GND."}
        ],
        "power": {"voltage": 2.0, "voltage_tolerance": [1.8, 2.5], "current_mA": 80.0, "current_max_mA": 120.0},
        "constraints": [
            {"type": "requires_resistor", "condition": "Segment connected directly to 5V GPIO without resistor.", "resolution": "Add 220Ω in series with each segment anode: R = (5V - 2.0V) / 0.010A = 300Ω; 220Ω gives ~14mA per segment.", "auto_fixable": True, "fix_component_id": "resistor_220", "severity": "danger"},
            {"type": "gpio_pin_count", "condition": "Driving 8 segments directly uses 8 GPIO pins.", "resolution": "Use 74HC595 shift register to drive all segments with only 3 SPI pins (DATA/CLOCK/LATCH). Still needs 220Ω per segment output.", "auto_fixable": False, "severity": "info"}
        ],
        "compatible_boards": ["arduino_uno"],
        "tags": ["display", "7-segment", "led", "digit", "numeric", "common-cathode"],
        "_needs_review": False
    }
]

# ---------------------------------------------------------------------------
# Seed function — replaces the old sqlite3 version
# ---------------------------------------------------------------------------
# How it works:
#   1. Reads DATABASE_URL from .env (same logic as database.py)
#   2. If set  → connects to PostgreSQL, truncates and re-inserts all rows
#   3. If not set → connects to SQLite and does the same
#   4. The components data list above is unchanged — no data loss
# ---------------------------------------------------------------------------

import asyncio
import os
from dotenv import load_dotenv
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy import delete, insert, text

from .models import components_table, metadata

db_dir = os.path.dirname(os.path.abspath(__file__))
load_dotenv(os.path.join(db_dir, ".env"))
load_dotenv()


async def seed_database_async():
    DATABASE_URL = os.getenv("DATABASE_URL")

    if not DATABASE_URL:
        raise RuntimeError(
            "DATABASE_URL environment variable is missing in backend/.env. "
            "PostgreSQL configuration is required."
        )

    engine = create_async_engine(DATABASE_URL, echo=False)
    
    AsyncSessionLocal = async_sessionmaker(
        bind=engine,
        expire_on_commit=False,
    )

    db_label = DATABASE_URL.split("@")[-1]  # "localhost:5432/wiring_ai"
    print(f"[Seed] Targeting PostgreSQL: {db_label}")

    async with AsyncSessionLocal() as session:
        async with session.begin():
            # Delete all existing rows first (clean slate).
            # We use DELETE instead of TRUNCATE because SQLite doesn't support TRUNCATE.
            await session.execute(delete(components_table))

            # Build the list of row dicts to insert.
            # PostgreSQL's JSON columns accept Python dicts/lists directly.
            # SQLite's JSON columns also accept them (SQLAlchemy handles serialisation).
            rows = []
            for comp in components:
                rows.append({
                    "id":          comp["id"],
                    "name":        comp["name"],
                    "category":    comp["category"],
                    "description": comp["description"],

                    # JSON fields — passed as Python objects, not json.dumps() strings
                    "pins":              comp.get("pins", []),
                    "power":             comp.get("power"),
                    "interface":         comp.get("interface"),
                    "constraints":       comp.get("constraints", []),
                    "compatible_boards": comp.get("compatible_boards", []),
                    "tags":              comp.get("tags", []),

                    "_needs_review": comp.get("_needs_review", False),
                    "_review_notes": comp.get("_review_notes"),

                    # Board-specific fields (None for non-board components)
                    "board_pins":              comp.get("board_pins"),
                    "operating_voltage":       comp.get("operating_voltage"),
                    "input_voltage_range":     comp.get("input_voltage_range"),
                    "max_current_per_pin_mA":  comp.get("max_current_per_pin_mA"),
                    "max_5v_rail_mA":          comp.get("max_5v_rail_mA"),
                    "max_3v3_rail_mA":         comp.get("max_3v3_rail_mA"),
                    "total_digital_pins":      comp.get("total_digital_pins"),
                    "total_analog_pins":       comp.get("total_analog_pins"),
                    "total_pwm_pins":          comp.get("total_pwm_pins"),
                    "has_wifi":      comp.get("has_wifi", False),
                    "has_bluetooth": comp.get("has_bluetooth", False),
                })

            await session.execute(insert(components_table), rows)

    await engine.dispose()
    print(f"[Seed] Successfully seeded {len(components)} components.")


if __name__ == "__main__":
    asyncio.run(seed_database_async())