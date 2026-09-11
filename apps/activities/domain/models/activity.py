from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from apps.activities.domain.common.entity import Entity

@dataclass(kw_only=True, eq=False)
class Activity(Entity):
    name: str
    latitude: float
    longitude: float
    description: str | None = None
    address: str | None = None
    country_code: str | None = None
    region: str | None = None
    city: str | None = None
    activity_type: str | None = None
    map_url: str | None = None
    web_url: str | None = None
    start_date: datetime | None = None
    end_date: datetime | None = None
    is_active: bool = True