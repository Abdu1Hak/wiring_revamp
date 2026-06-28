from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List

app = FastAPI()

# Allows frontend to call backend during development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Pydantic Model 
class GenerateProjectRequest(BaseModel):
    # Include all the feilds with its value type
    scope: str
    selectedComponents: List[str]

# backend houses a catalog of components instead of the frontend doing it
COMPONENT_CATALOG = [
    {
        "id": "arduino_uno",
        "name": "Arduino Uno",
        "category": "microcontroller",
        "description": "Beginner-friendly microcontroller board.",
        "pins": ["5V", "3.3V", "GND", "D2", "D3", "D4", "D5", "D9", "D10", "A0"],
    },
    {
        "id": "esp32",
        "name": "ESP32",
        "category": "microcontroller",
        "description": "WiFi and Bluetooth capable microcontroller.",
        "pins": ["3.3V", "GND", "GPIO2", "GPIO4", "GPIO5", "GPIO18", "GPIO19"],
    },
    {
        "id": "raspberry_pi_pico",
        "name": "Raspberry Pi Pico",
        "category": "microcontroller",
        "description": "Low-cost RP2040 microcontroller board.",
        "pins": ["3V3", "GND", "GP0", "GP1", "GP2", "GP3", "VBUS"],
    },
    {
        "id": "hc_sr04",
        "name": "HC-SR04 Ultrasonic Sensor",
        "category": "sensor",
        "description": "Measures distance using ultrasonic pulses.",
        "pins": ["VCC", "GND", "TRIG", "ECHO"],
    },
    {
        "id": "led",
        "name": "LED",
        "category": "output",
        "description": "Simple light output component.",
        "pins": ["anode", "cathode"],
    },
    {
        "id": "resistor_220",
        "name": "220 Ohm Resistor",
        "category": "passive",
        "description": "Limits current, commonly used with LEDs.",
        "pins": ["leg_1", "leg_2"],
    },
    {
        "id": "buzzer",
        "name": "Buzzer",
        "category": "output",
        "description": "Produces sound when powered.",
        "pins": ["positive", "negative"],
    },
    {
        "id": "servo_motor",
        "name": "Servo Motor",
        "category": "actuator",
        "description": "Rotates to a controlled angle.",
        "pins": ["VCC", "GND", "SIGNAL"],
    },
    {
        "id": "dht11",
        "name": "DHT11 Temperature Sensor",
        "category": "sensor",
        "description": "Measures temperature and humidity.",
        "pins": ["VCC", "DATA", "GND"],
    },
    {
        "id": "potentiometer",
        "name": "Potentiometer",
        "category": "input",
        "description": "Variable resistor often used as an analog input.",
        "pins": ["VCC", "OUT", "GND"],
    },
]

# This is a backend route, a get request is used when the frontend (client) wants to retrieve data
@app.get("/")
def root():
    return {"message": "Wiring AI backend is running"}

# this is a backend route, a post request is used when the frontend (client) wants to send data to the backend
@app.post("/api/generate-project")
def generate_project(request: GenerateProjectRequest): # Example of a request body parameter   
  
    # The backend is expecting json data sent to this address, where pyndantic converts it to an object
    print("SCOPE RECEIVED:", request.scope)
    print("COMPONENTS RECEIVED:", request.selectedComponents)

    selected_component_objects = [component for component in COMPONENT_CATALOG if component["id"] in request.selectedComponents]
    print("Selected Components:", selected_component_objects)

    return {
        "title": "Arduino Distance LED Alert",
        "summary": "An Arduino project where an ultrasonic sensor turns on an LED when an object is closer than 2 feet.",
        "components": selected_component_objects,
        "steps": [
            {
                "id": "step_1",
                "title": "Connect sensor power",
                "instruction": "Connect VCC on the HC-SR04 sensor to 5V on the Arduino."
            },
            {
                "id": "step_2",
                "title": "Connect sensor ground",
                "instruction": "Connect GND on the HC-SR04 sensor to GND on the Arduino."
            },
            {
                "id": "step_3",
                "title": "Connect trigger pin",
                "instruction": "Connect TRIG on the HC-SR04 sensor to digital pin D9 on the Arduino."
            },
            {
                "id": "step_4",
                "title": "Connect echo pin",
                "instruction": "Connect ECHO on the HC-SR04 sensor to digital pin D10 on the Arduino."
            },
            {
                "id": "step_5",
                "title": "Connect LED",
                "instruction": "Connect Arduino pin D3 to the LED anode through a 220 ohm resistor, then connect the LED cathode to GND."
            }
        ],
        "connections": [
            {
                "id": "conn_1",
                "fromComponent": "arduino_uno",
                "fromPin": "5V",
                "toComponent": "hc_sr04",
                "toPin": "VCC",
                "label": "Power"
            },
            {
                "id": "conn_2",
                "fromComponent": "arduino_uno",
                "fromPin": "GND",
                "toComponent": "hc_sr04",
                "toPin": "GND",
                "label": "Ground"
            },
            {
                "id": "conn_3",
                "fromComponent": "arduino_uno",
                "fromPin": "D9",
                "toComponent": "hc_sr04",
                "toPin": "TRIG",
                "label": "Trigger signal"
            },
            {
                "id": "conn_4",
                "fromComponent": "arduino_uno",
                "fromPin": "D10",
                "toComponent": "hc_sr04",
                "toPin": "ECHO",
                "label": "Echo signal"
            },
            {
                "id": "conn_5",
                "fromComponent": "arduino_uno",
                "fromPin": "D3",
                "toComponent": "led",
                "toPin": "anode",
                "label": "LED control"
            }
        ]
    }


@app.get("/api/components")
def components():
    return COMPONENT_CATALOG