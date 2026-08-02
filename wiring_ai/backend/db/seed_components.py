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
            {"name": "A0", "type": "analog_input", "voltage": 5, "required": False},
            {"name": "A1", "type": "analog_input", "voltage": 5, "required": False},
            {"name": "A2", "type": "analog_input", "voltage": 5, "required": False},
            {"name": "A3", "type": "analog_input", "voltage": 5, "required": False},
            {"name": "A4", "type": "analog_input", "voltage": 5, "required": False, "notes": "I2C SDA. Also usable as digital/analog IO."},
            {"name": "A5", "type": "analog_input", "voltage": 5, "required": False, "notes": "I2C SCL. Also usable as digital/analog IO."},
            {"name": "5V", "type": "power", "voltage": 5, "required": False, "notes": "5V regulated output power rail."},
            {"name": "3.3V", "type": "power", "voltage": 3.3, "required": False, "notes": "3.3V regulated output power rail (150mA max)."},
            {"name": "GND", "type": "ground", "voltage": 0, "required": False, "notes": "Ground connection (common negative reference)."},
            {"name": "VIN", "type": "power", "voltage": 12, "required": False, "notes": "Input voltage rail (7-12V barrel jack or external)."},
            {"name": "AREF", "type": "analog_input", "voltage": 5, "required": False, "notes": "Analog reference voltage."}
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
            {"pin_id": "D13", "label": "13", "capabilities": ["digital", "spi_sck"], "voltage": 5.0, "max_current_mA": 40.0, "reserved": True, "reserved_reason": "Pin 13 has onboard LED — may interfere with external circuits"},
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
        "has_bluetooth": False
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
            {"name": "TRIG", "type": "digital_input", "voltage": 5.0, "required": True, "notes": "Trigger pin. Needs minimum 10μs HIGH pulse"},
            {"name": "ECHO", "type": "digital_output", "voltage": 5.0, "required": True, "notes": "Echo pin. Outputs 5V TTL pulse proportional to distance"},
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
            {"name": "DATA", "type": "data", "required": True, "notes": "Bidirectional single-bus data line. Requires a 4.7kΩ or 10kΩ pull-up resistor to VCC."},
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
            {"name": "anode", "type": "digital_input", "voltage": 2.0, "required": True, "notes": "Positive lead (longer leg). Connects through series resistor."},
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
            {"name": "anode", "type": "digital_input", "voltage": 2.2, "required": True, "notes": "Positive lead (longer leg). Connects through series resistor."},
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
            {"name": "positive", "type": "digital_input", "voltage": 5.0, "required": True, "notes": "Connect to a digital/PWM pin"},
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
            {"name": "OUT", "type": "analog_output", "voltage": 5.0, "required": True, "notes": "Connect to analog input pin"},
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
            {"name": "SIGNAL", "type": "digital_input", "voltage": 5.0, "required": True, "notes": "Orange wire. Connect to PWM-capable pin."}
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