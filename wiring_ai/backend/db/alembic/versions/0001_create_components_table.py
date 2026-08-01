"""create components table

Revision ID: 0001
Revises:
Create Date: 2026-07-31

What this migration does:
    Creates the "components" table in PostgreSQL if it doesn't already exist.

    This is a "safe" migration — it uses CREATE TABLE IF NOT EXISTS behaviour
    via Alembic's op.create_table(), which means running it twice won't fail
    or wipe your data.

    If you ever need to undo this migration (roll back), the downgrade()
    function at the bottom drops the table. Be careful — that deletes all data!

How to run:
    alembic upgrade head        <- applies this migration (and all future ones)
    alembic downgrade -1        <- rolls back the last migration
    alembic history             <- shows all migrations and their status
"""

from alembic import op
import sqlalchemy as sa

# These two variables are REQUIRED by Alembic — they identify this migration
# and what migration it builds on (None = this is the first one).
revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    """
    Creates the components table.

    Column-by-column breakdown:
      id                     - Text primary key, e.g. "arduino_uno"
      name/category/description - Basic text info shown in the UI
      pins                   - JSONB: list of pin objects [{name, type, voltage}]
      power                  - JSONB: {voltage, current_mA, ...}
      constraints            - JSONB: list of hardware constraint rules
      compatible_boards      - JSONB: list of board id strings
      tags                   - JSONB: list of search tags
      _needs_review          - Boolean flag for data quality review
      _review_notes          - Admin notes (nullable)
      board_pins             - JSONB: full pin map (boards only, NULL otherwise)
      operating_voltage      - Float: e.g. 5.0 or 3.3 (boards only)
      input_voltage_range    - JSONB: [min, max] input voltage (boards only)
      max_current_per_pin_mA - Float: GPIO pin current limit (boards only)
      max_5v_rail_mA         - Float: 5V power rail capacity (boards only)
      max_3v3_rail_mA        - Float: 3.3V power rail capacity (boards only)
      total_digital_pins     - Integer (boards only)
      total_analog_pins      - Integer (boards only)
      total_pwm_pins         - Integer (boards only)
      has_wifi               - Boolean (boards only)
      has_bluetooth          - Boolean (boards only)
    """
    op.create_table(
        "components",

        # Core fields
        sa.Column("id",          sa.Text(), primary_key=True),
        sa.Column("name",        sa.Text(), nullable=False),
        sa.Column("category",    sa.Text(), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),

        # JSON payload fields — PostgreSQL stores these as JSONB (binary JSON),
        # which is faster and supports indexing/querying inside the JSON structure.
        sa.Column("pins",              sa.JSON(), nullable=True),
        sa.Column("power",             sa.JSON(), nullable=True),
        sa.Column("constraints",       sa.JSON(), nullable=True),
        sa.Column("compatible_boards", sa.JSON(), nullable=True),
        sa.Column("tags",              sa.JSON(), nullable=True),

        # Review flags
        sa.Column("_needs_review", sa.Boolean(), server_default="false"),
        sa.Column("_review_notes", sa.Text(),    nullable=True),

        # Board-specific fields (NULL for sensors, LEDs, resistors, etc.)
        sa.Column("board_pins",              sa.JSON(),    nullable=True),
        sa.Column("operating_voltage",       sa.Float(),   nullable=True),
        sa.Column("input_voltage_range",     sa.JSON(),    nullable=True),
        sa.Column("max_current_per_pin_mA",  sa.Float(),   nullable=True),
        sa.Column("max_5v_rail_mA",          sa.Float(),   nullable=True),
        sa.Column("max_3v3_rail_mA",         sa.Float(),   nullable=True),
        sa.Column("total_digital_pins",      sa.Integer(), nullable=True),
        sa.Column("total_analog_pins",       sa.Integer(), nullable=True),
        sa.Column("total_pwm_pins",          sa.Integer(), nullable=True),
        sa.Column("has_wifi",      sa.Boolean(), server_default="false"),
        sa.Column("has_bluetooth", sa.Boolean(), server_default="false"),
    )


def downgrade() -> None:
    """
    CAUTION: Drops the components table and all data in it.
    Only runs when you explicitly roll back: alembic downgrade -1
    """
    op.drop_table("components")
