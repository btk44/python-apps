import os
from datetime import datetime

from dotenv import load_dotenv
from fastapi import HTTPException, status
from openai import APIConnectionError, APIError, APIStatusError, AsyncAzureOpenAI
from pydantic import BaseModel, ConfigDict, Field, model_validator

from apps.activities.features.a_router import router

load_dotenv()


class ActivityDto(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    name: str = Field(min_length=1, max_length=255)
    description: str | None = None
    address: str | None = None
    country_code: str | None = Field(default=None, alias="countryCode")
    region: str | None = None
    city: str | None = None
    activity_type: str = Field(default="place", alias="activityType")
    latitude: float | None = Field(default=None, ge=-90, le=90)
    longitude: float | None = Field(default=None, ge=-180, le=180)
    map_url: str | None = Field(default=None, alias="mapUrl")
    web_url: str | None = Field(default=None, alias="webUrl")
    start_date: datetime | None = Field(default=None, alias="startDate")
    end_date: datetime | None = Field(default=None, alias="endDate")

    @model_validator(mode="after")
    def validate_activity(self) -> "ActivityDto":
        if self.activity_type not in {"place", "activity", "event"}:
            raise ValueError("activity_type must be place, activity, or event")
        if self.start_date is not None and self.end_date is not None and self.end_date < self.start_date:
            raise ValueError("end_date must be greater than or equal to start_date")
        return self


class ActivityProcessCommand(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    activity: ActivityDto


def _activity_json_schema() -> dict:
    schema = ActivityDto.model_json_schema(by_alias=True)
    schema["additionalProperties"] = False
    schema["required"] = list(schema["properties"])
    for property_schema in schema["properties"].values():
        property_schema.pop("default", None)
    return schema


async def make_direct_agent_search(activity: ActivityDto) -> ActivityDto:
    client = AsyncAzureOpenAI(
        azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT"),
        api_key=os.getenv("AZURE_API_KEY"),
        api_version=os.getenv("AZURE_API_VERSION"),
    )

    try:
        response = await client.responses.create(
            model=os.getenv("AZURE_FOUNDRY_MODEL"),
            tools=[{"type": "web_search"}],
            input=[
                {
                    "role": "system",
                    "content": (
                        "Use web information to enrich the activity. Do not invent facts. "
                        "Return only the requested JSON object. Use Polish for field contents, "
                        "but preserve original event names in their original language."
                    ),
                },
                {
                    "role": "user",
                    "content": (
                        "Find the most likely real-world match, correct incorrect fields, and "
                        "complete missing fields. Return null for values you cannot verify.\n\n"
                        f"User data:\n{activity.model_dump_json(by_alias=True, exclude_none=True)}"
                    ),
                },
            ],
            text={
                "format": {
                    "type": "json_schema",
                    "name": "activity",
                    "strict": True,
                    "schema": _activity_json_schema(),
                }
            },
        )
    except APIStatusError as error:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY,
                            detail={"message": "Azure OpenAI rejected the request", "provider": str(error)}) from error
    except APIConnectionError as error:
        raise HTTPException(status_code=status.HTTP_504_GATEWAY_TIMEOUT,  detail="Could not reach Azure OpenAI") from error
    except APIError as error:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail="Azure OpenAI returned an error") from error

    try:
        return ActivityDto.model_validate_json(response.output_text)
    except (TypeError, ValueError) as error:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail="Azure OpenAI returned invalid activity data") from error


@router.post("/ai-activity-assistance", response_model=ActivityDto, status_code=status.HTTP_200_OK)
async def ai_activity_assistance(command: ActivityProcessCommand) -> ActivityDto:
    return await make_direct_agent_search(command.activity)
