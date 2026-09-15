from __future__ import annotations

from sqlalchemy import Boolean, Column, Integer, MetaData, String, Table, text
from sqlalchemy.dialects.postgresql import TIMESTAMP
from sqlalchemy.types import UserDefinedType

metadata = MetaData()


class Geography(UserDefinedType):
    def get_col_spec(self, **kwargs: object) -> str:
        return "GEOGRAPHY(POINT, 4326)"


activities = Table(
    "activities",
    metadata,
    Column("id", Integer, primary_key=True),
    Column("name", String(255), nullable=False),
    Column("description", String),
    Column("address", String(500)),
    Column("country_code", String(2)),
    Column("region", String(100)),
    Column("city", String(100)),
    Column("location", Geography, nullable=False),
    Column("activity_type", String(20), nullable=False),
    Column("map_url", String(500)),
    Column("website_url", String(500)),
    Column("start_date", TIMESTAMP(timezone=True)),
    Column("end_date", TIMESTAMP(timezone=True)),
    Column("is_active", Boolean, nullable=False, server_default=text("true")),
    Column("version", Integer, nullable=False, server_default=text("1")),
    Column("created_at", TIMESTAMP(timezone=True), server_default=text("now()")),
    Column("updated_at", TIMESTAMP(timezone=True), server_default=text("now()")),
)
