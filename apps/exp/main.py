from __future__ import annotations

from fastapi import FastAPI
from starlette.responses import JSONResponse
from apps.exp.features.a_router import router as expenses_router

app = FastAPI()
app.include_router(expenses_router)

import logging

logger = logging.getLogger(__name__)

@app.exception_handler(Exception)
async def internal_exception_handler(request, exc):
    logger.exception("Unhandled exception")

    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error"},
    )
