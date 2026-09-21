from fastapi import APIRouter

router = APIRouter(prefix="/activities", tags=["activities"])

from . import search_activities
from . import process_activity
from . import ai_activity_assistance
