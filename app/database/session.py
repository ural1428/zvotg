from sqlalchemy.ext.asyncio import (
    create_async_engine,
    async_sessionmaker,
    AsyncSession,
)

from app.config import config


DATABASE_URL = (
    f"postgresql+asyncpg://"
    f"{config.db.user}:"
    f"{config.db.password}@"
    f"{config.db.host}:"
    f"{config.db.port}/"
    f"{config.db.name}"
)

engine = create_async_engine(
    DATABASE_URL,
    echo=False,
)

AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
)
