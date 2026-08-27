# models.py
# ---------
# This file defines the database TABLE STRUCTURE using SQLAlchemy's "Table" API.
#
# Think of it as a blueprint for the "components" table that lives in the database.
# Both database.py (for reading/writing) and Alembic (for migrations) import
# from here so there is ONE place that describes what the table looks like.
#
# SQLAlchemy's Column types map to PostgreSQL and SQLite types automatically:
#   String  -> VARCHAR / TEXT
#   Text    -> TEXT
#   Float   -> REAL / DOUBLE PRECISION
#   Integer -> INTEGER
#   Boolean -> BOOLEAN
#   JSON    -> JSONB (Postgres) / TEXT (SQLite - stored as JSON string)

from sqlalchemy import (
    MetaData,
    Table,
    Column,
    String,
    Text,
    Float,
    Integer,
    Boolean,
    JSON,
)

# MetaData is a container that holds all the table definitions.
# SQLAlchemy uses it to know what tables exist and how they relate.
metadata = MetaData()

# "components" table — mirrors the existing SQLite schema exactly.
# Each Column(...) corresponds to one column in the database table.
components_table = Table(
    "components",   # The actual table name in the database
    metadata,

    # --- Core identity fields ---
    Column("id",          String,  primary_key=True),   # e.g. "arduino_uno"
    Column("name",        Text,    nullable=False),     # e.g. "Arduino Uno"
    Column("category",    Text,    nullable=False),     # e.g. "board", "sensor"
    Column("description", Text,    nullable=False),

    # --- JSON payload fields ---
    # These are stored as JSONB in Postgres (queryable JSON) and as TEXT in SQLite.
    # The app-level _parse_component() function handles deserialization.
    Column("pins",             JSON),   # list of pin objects
    Column("interface",        JSON),   # { protocol, i2c_address, ... }
    Column("power",            JSON),   # { logic_voltage, voltage_range, operating_current_mA, is_external_powered }
    Column("constraints",      JSON),   # list of constraint objects
    Column("compatible_boards",JSON),   # list of board id strings
    Column("tags",             JSON),   # list of tag strings

    # --- Review / admin flags ---
    Column("_needs_review", Boolean, default=False),
    Column("_review_notes", Text),

    # --- Board-specific fields (NULL for non-board components) ---
    Column("board_pins",           JSON),    # full list of physical board pins
    Column("operating_voltage",    Float),   # e.g. 5.0 or 3.3
    Column("input_voltage_range",  JSON),    # e.g. [7.0, 12.0]
    Column("max_current_per_pin_mA", Float),
    Column("max_5v_rail_mA",       Float),
    Column("max_3v3_rail_mA",      Float),
    Column("total_digital_pins",   Integer),
    Column("total_analog_pins",    Integer),
    Column("total_pwm_pins",       Integer),
    Column("has_wifi",             Boolean, default=False),
    Column("has_bluetooth",        Boolean, default=False),

    # --- NEW -----
    Column("datasheet_url",         Text),
    Column("datasheet_summary",     Text),
    Column('qdrant_indexed', Boolean, default=False)
)
