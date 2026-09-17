from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from dotenv import load_dotenv
import os
from sqlalchemy.pool import NullPool

load_dotenv()

USER = os.getenv("user")
PASSWORD = os.getenv("password")
HOST = os.getenv("host")
PORT = os.getenv("port")
DBNAME = os.getenv("dbname")

# Note: asyncpg driver, not psycopg2
DATABASE_URL = (
    f"postgresql+asyncpg://{USER}:{PASSWORD}@{HOST}:{PORT}/{DBNAME}"
)

connect_args = {"ssl": "require"}

engine = create_async_engine(DATABASE_URL, connect_args=connect_args, poolclass=NullPool)

AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    autocommit=False,
    autoflush=False,
    expire_on_commit=False,
)

async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSessionLocal() as session:
        yield session

# For use outside FastAPI's Depends system
# async def some_background_task():
#     async with AsyncSessionLocal() as db:
#         result = await db.execute(select(Item))
#         return result.scalars().all()