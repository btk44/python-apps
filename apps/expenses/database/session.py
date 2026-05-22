from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker

DATABASE_URL = "postgresql+asyncpg://postgres:PASSWORD@SERVER_ADDRESS/DATABASENAME"  # set your URL

engine = create_async_engine(DATABASE_URL, echo=False)
SessionLocal = async_sessionmaker(
    bind=engine, 
    class_=AsyncSession, 
    expire_on_commit=False
)