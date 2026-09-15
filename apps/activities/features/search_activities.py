from datetime import datetime
from collections.abc import AsyncGenerator

from fastapi import Depends
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncConnection

from apps.activities.features.a_router import router
from apps.expenses.infrastructure.session import get_connection

class ActivitySearchCommand(BaseModel):
    name: str | None = None
    country: str | None = None
    region: str | None = None
    city: str | None = None
    start_date: datetime | None = None
    end_date: datetime | None = None
    categories: list[str] | None = None
    targets: list[str] | None = None
    activity_type: str | None = None
    latitude: float | None = None
    longitude: float | None = None
    distance: float | None = None
    take: int | None = None
    offset: int | None = None


class ActivityDto(BaseModel):
    id: int
    name: str
    description: str | None = None
    address: str | None = None
    country_code: str | None = None
    region: str | None = None
    city: str | None = None
    activity_type: str | None = None
    map_url: str | None = None
    web_url: str | None = None
    start_date: datetime | None = None
    end_time: datetime | None = None
    targets: list[str] = []
    categories: list[str] = []


async def get_db() -> AsyncGenerator[AsyncConnection]:
    async with get_connection() as conn:
        yield conn


SEARCH_ACTIVITIES = text(
    """
    SELECT *
    FROM search_activities(
        :name,
        :country_code,
        :region,
        :city,
        :activity_type,
        :target_names,
        :category_names,
        :start_date,
        :end_date,
        :latitude,
        :longitude,
        :distance,
        true,
        :limit,
        :offset
    )
    """
)


def row_to_activity(row: dict) -> ActivityDto:
    return ActivityDto(
        id=row["id"],
        name=row["name"],
        description=row["description"],
        address=row["address"],
        country_code=row["country_code"],
        region=row["region"],
        city=row["city"],
        activity_type=row["activity_type"],
        map_url=row["map_url"],
        web_url=row["website_url"],
        start_date=row["start_date"],
        end_time=row["end_date"],
        targets=row["targets"] or [],
        categories=row["categories"] or [],
    )


async def run_avtivity_search(command: ActivitySearchCommand, conn: AsyncConnection) -> list[ActivityDto]:
    parameters = {
        "name": command.name,
        "country_code": command.country,
        "region": command.region,
        "city": command.city,
        "activity_type": command.activity_type,
        "target_names": command.targets,
        "category_names": command.categories,
        "start_date": command.start_date,
        "end_date": command.end_date,
        "latitude": command.latitude,
        "longitude": command.longitude,
        "distance": command.distance,
        "limit": command.take if command.take is not None else 50,
        "offset": command.offset if command.offset is not None else 0,
    }
    result = await conn.execute(SEARCH_ACTIVITIES, parameters)
    return [row_to_activity(dict(row)) for row in result.mappings().all()]

@router.get("/activities/search", response_model=list[ActivityDto])
async def search_activities(
    command: ActivitySearchCommand,
    conn: AsyncConnection = Depends(get_db),
):
    return await run_avtivity_search(command, conn)