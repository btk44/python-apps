from __future__ import annotations

from collections.abc import AsyncGenerator
from datetime import datetime

from fastapi import Depends, HTTPException, status
from pydantic import BaseModel, ConfigDict, Field, model_validator
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncConnection

from apps.activities.domain.models.activity import Activity
from apps.activities.features.a_router import router
from apps.expenses.infrastructure.session import get_connection


# TO DO: revisit this file because it does not fit agreed standards 

class ActivityDto(BaseModel):
	model_config = ConfigDict(populate_by_name=True)

	id: int | None = None
	name: str = Field(min_length=1, max_length=255)
	description: str | None = None
	address: str | None = Field(default=None, max_length=500)
	country_code: str | None = Field(default=None, min_length=2, max_length=2, pattern=r"^[A-Z]{2}$")
	region: str | None = Field(default=None, max_length=100)
	city: str | None = Field(default=None, max_length=100)
	latitude: float = Field(ge=-90, le=90)
	longitude: float = Field(ge=-180, le=180)
	activity_type: str = Field(default="activity", pattern=r"^(place|activity|event)$")
	map_url: str | None = Field(default=None, max_length=500)
	web_url: str | None = Field(default=None, max_length=500)
	start_date: datetime | None = None
	end_date: datetime | None = None
	active: bool = True
	version: int = 1

	@model_validator(mode="after")
	def validate_dates(self) -> "ActivityDto":
		if self.start_date is not None and self.end_date is not None and self.end_date < self.start_date:
			raise ValueError("end_date must be greater than or equal to start_date")
		return self


class ActivityProcessCommand(BaseModel):
	model_config = ConfigDict(populate_by_name=True)

	activity: ActivityDto


async def get_db() -> AsyncGenerator[AsyncConnection, None]:
	async with get_connection() as conn:
		yield conn


INSERT_ACTIVITY = text(
	"""
	INSERT INTO activities (
		name, description, address, country_code, region, city, location,
		activity_type, google_maps_url, website_url, start_date, end_date, is_active
	) VALUES (
		:name, :description, :address, :country_code, :region, :city,
		ST_SetSRID(ST_MakePoint(:longitude, :latitude), 4326)::geography,
		:activity_type, :google_maps_url, :website_url, :start_date, :end_date, :is_active
	)
	RETURNING id, version, created_at, updated_at
	"""
)


def activity_dto_to_entity(dto: ActivityDto) -> Activity:
	return Activity(
		id=dto.id,
		name=dto.name,
		description=dto.description,
		address=dto.address,
		country_code=dto.country_code,
		region=dto.region,
		city=dto.city,
		latitude=dto.latitude,
		longitude=dto.longitude,
		activity_type=dto.activity_type,
		map_url=dto.map_url,
		web_url=dto.web_url,
		start_date=dto.start_date,
		end_date=dto.end_date,
		is_active=dto.active,
		version=dto.version,
	)


def activity_entity_to_dto(activity: Activity) -> ActivityDto:
	if activity.id is None:
		raise ValueError("persisted activity has no id")
	return ActivityDto(
		id=activity.id,
		name=activity.name,
		description=activity.description,
		address=activity.address,
		country_code=activity.country_code,
		region=activity.region,
		city=activity.city,
		latitude=activity.latitude,
		longitude=activity.longitude,
		activity_type=activity.activity_type,
		map_url=activity.map_url,
		web_url=activity.web_url,
		start_date=activity.start_date,
		end_date=activity.end_date,
		active=activity.is_active,
		version=activity.version,
	)


async def create_activity(conn: AsyncConnection, activity: Activity) -> Activity:
	result = await conn.execute(
		INSERT_ACTIVITY,
		{
			"name": activity.name,
			"description": activity.description,
			"address": activity.address,
			"country_code": activity.country_code,
			"region": activity.region,
			"city": activity.city,
			"latitude": activity.latitude,
			"longitude": activity.longitude,
			"activity_type": activity.activity_type,
			"google_maps_url": activity.map_url,
			"website_url": activity.web_url,
			"start_date": activity.start_date,
			"end_date": activity.end_date,
			"is_active": activity.is_active,
		},
	)
	row = result.one()
	return Activity(
		id=row.id,
		name=activity.name,
		description=activity.description,
		address=activity.address,
		country_code=activity.country_code,
		region=activity.region,
		city=activity.city,
		latitude=activity.latitude,
		longitude=activity.longitude,
		activity_type=activity.activity_type,
		map_url=activity.map_url,
		web_url=activity.web_url,
		start_date=activity.start_date,
		end_date=activity.end_date,
		is_active=activity.is_active,
		version=row.version,
		created_at=row.created_at,
		updated_at=row.updated_at,
	)


@router.post("/activity/process-single", response_model=ActivityDto, status_code=status.HTTP_201_CREATED)
async def process_activity(
	command: ActivityProcessCommand,
	conn: AsyncConnection = Depends(get_db),
) -> ActivityDto:
	try:
		activity = await create_activity(conn, activity_dto_to_entity(command.activity))
		await conn.commit()
		return activity_entity_to_dto(activity)
	except Exception as error:
		await conn.rollback()
		raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail={"status": str(error)}) from error