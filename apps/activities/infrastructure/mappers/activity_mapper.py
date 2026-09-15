from __future__ import annotations

from sqlalchemy import func, literal_column
from sqlalchemy.engine import Row
from sqlalchemy.sql.selectable import NamedFromClause

from apps.activities.domain.models.activity import Activity
from apps.activities.infrastructure.tables import activities


def activity_latitude_column(activities_alias: NamedFromClause = activities):
    location_geometry = activities_alias.c.location.op("::")(literal_column("geometry"))
    return func.ST_Y(location_geometry).label("latitude")


def activity_longitude_column(activities_alias: NamedFromClause = activities):
    location_geometry = activities_alias.c.location.op("::")(literal_column("geometry"))
    return func.ST_X(location_geometry).label("longitude")


def row_to_activity(row: Row, activities_alias: NamedFromClause = activities) -> Activity:
    m = row._mapping
    if activities_alias.c.id not in m:
        return None
    else:
        return Activity(
            id=m[activities_alias.c.id],
            name=m[activities_alias.c.name],
            description=m[activities_alias.c.description],
            address=m[activities_alias.c.address],
            country_code=m[activities_alias.c.country_code],
            region=m[activities_alias.c.region],
            city=m[activities_alias.c.city],
            latitude=m["latitude"],
            longitude=m["longitude"],
            activity_type=m[activities_alias.c.activity_type],
            map_url=m[activities_alias.c.map_url],
            web_url=m[activities_alias.c.website_url],
            start_date=m[activities_alias.c.start_date],
            end_date=m[activities_alias.c.end_date],
            is_active=m[activities_alias.c.is_active],
            version=m[activities_alias.c.version],
            created_at=m[activities_alias.c.created_at],
            updated_at=m[activities_alias.c.updated_at],
        )

def activity_to_insert_values(activity: Activity) -> dict:
    return {
        "name": activity.name,
        "description": activity.description,
        "address": activity.address,
        "country_code": activity.country_code,
        "region": activity.region,
        "city": activity.city,
        "location": _activity_location_value(activity),
        "activity_type": activity.activity_type,
        "map_url": activity.map_url,
        "website_url": activity.web_url,
        "start_date": activity.start_date,
        "end_date": activity.end_date,
        "is_active": activity.is_active,
    }

def activity_to_update_values(activity: Activity) -> dict:
    return {
        "name": activity.name,
        "description": activity.description,
        "address": activity.address,
        "country_code": activity.country_code,
        "region": activity.region,
        "city": activity.city,
        "location": _activity_location_value(activity),
        "activity_type": activity.activity_type,
        "map_url": activity.map_url,
        "website_url": activity.web_url,
        "start_date": activity.start_date,
        "end_date": activity.end_date,
        "is_active": activity.is_active,
    }


def _activity_location_value(activity: Activity):
    return func.ST_SetSRID(
        func.ST_MakePoint(activity.longitude, activity.latitude),
        4326,
    ).cast(activities.c.location.type)