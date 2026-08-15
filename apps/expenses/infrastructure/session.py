"""Async engine + connection lifecycle.

Core (not ORM) is used deliberately: no Session, no identity map — the
repository layer runs explicit `select`/`insert`/`update` statements over
a plain `AsyncConnection` and maps rows to/from domain entities itself.
"""
from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from sqlalchemy.ext.asyncio import AsyncConnection, AsyncEngine, create_async_engine
from ..constants import DATABASE_USER, DATABASE_PASSWORD, DATABASE_HOST, DATABASE_NAME


DATABASE_URL = f"postgresql+asyncpg://{DATABASE_USER}:{DATABASE_PASSWORD}@{DATABASE_HOST}/{DATABASE_NAME}" 

engine: AsyncEngine = create_async_engine(
    DATABASE_URL,
    pool_size=10,
    max_overflow=5,
    pool_pre_ping=True,
    echo=False,
)


@asynccontextmanager
async def get_connection() -> AsyncIterator[AsyncConnection]:
    async with engine.connect() as conn:
        yield conn