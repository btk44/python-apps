from __future__ import annotations

from fastapi import FastAPI
from starlette.responses import JSONResponse
from apps.expenses.features.a_router import router as expenses_router
from apps.activities.features.a_router import router as activities_router

app = FastAPI()
app.include_router(expenses_router)
app.include_router(activities_router)

import logging

logger = logging.getLogger(__name__)

@app.exception_handler(Exception)
async def internal_exception_handler(request, exc):
    logger.exception("Unhandled exception")

    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error"},
    )