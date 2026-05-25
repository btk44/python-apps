from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from ..constants import DATABASE_USER, DATABASE_PASSWORD, DATABASE_HOST, DATABASE_NAME


DATABASE_URL = f"postgresql+asyncpg://{DATABASE_USER}:{DATABASE_PASSWORD}@{DATABASE_HOST}/{DATABASE_NAME}"  # set your URL

engine = create_async_engine(DATABASE_URL, echo=False)
SessionLocal = async_sessionmaker(
    bind=engine, 
    class_=AsyncSession, 
    expire_on_commit=False
)