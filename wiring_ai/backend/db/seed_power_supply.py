import asyncio
import json
import os
import sys
from dotenv import load_dotenv
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

db_dir = os.path.dirname(os.path.abspath(__file__))
load_dotenv(os.path.join(db_dir, ".env"))
load_dotenv(os.path.join(db_dir, "..", ".env"))

DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    raise RuntimeError("DATABASE_URL not found!")

engine = create_async_engine(DATABASE_URL, echo=False)

async def seed():
    params = {
        "id": "dc_power_supply",
        "name": "Adjustable DC Power Supply / Battery",
        "category": "power",
        "description": "Standardized adjustable DC power source & battery unit. Voltage can be configured to 3.3V, 5V, 6V, 7.4V (2S LiPo), 9V, 11.1V (3S LiPo), 12V, 24V or custom DC.",
        "pins": json.dumps([
            {"name": "VCC", "type": "power", "description": "Positive power rail (+)"},
            {"name": "GND", "type": "ground", "description": "Ground return rail (-)"}
        ]),
        "power": json.dumps({
            "voltage_type": "DC",
            "is_adjustable": True,
            "default_voltage": "7.4V",
            "supported_voltages": ["3.3V", "5V", "6V", "7.4V", "9V", "11.1V", "12V", "24V"]
        }),
        "constraints": json.dumps([]),
        "compatible_boards": json.dumps(["all", "arduino_uno", "arduino_nano", "esp32_devkit"]),
        "tags": json.dumps(["power", "battery", "dc_supply", "adjustable_voltage", "lipo", "external_power"]),
        "operating_voltage": 7.4,
        "datasheet_url": "",
        "datasheet_summary": "Standardized variable DC power source and battery pack unit with configurable positive VCC and GND terminals.",
        "qdrant_indexed": True
    }

    async with engine.connect() as conn:
        await conn.execute(text("""
            INSERT INTO components (
                id, name, category, description,
                pins, power, constraints, compatible_boards, tags,
                operating_voltage, datasheet_url, datasheet_summary, qdrant_indexed
            )
            VALUES (
                :id, :name, :category, :description,
                :pins, :power, :constraints, :compatible_boards, :tags,
                :operating_voltage, :datasheet_url, :datasheet_summary, :qdrant_indexed
            )
            ON CONFLICT (id) DO UPDATE SET
                name = EXCLUDED.name,
                category = EXCLUDED.category,
                description = EXCLUDED.description,
                pins = EXCLUDED.pins,
                power = EXCLUDED.power,
                constraints = EXCLUDED.constraints,
                compatible_boards = EXCLUDED.compatible_boards,
                tags = EXCLUDED.tags,
                operating_voltage = EXCLUDED.operating_voltage,
                datasheet_summary = EXCLUDED.datasheet_summary,
                qdrant_indexed = EXCLUDED.qdrant_indexed
        """), params)
        await conn.commit()
    print("SUCCESS: Seeded 'dc_power_supply' into PostgreSQL database!")

if __name__ == "__main__":
    asyncio.run(seed())
