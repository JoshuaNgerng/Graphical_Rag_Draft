from typing import AsyncGenerator
from contextlib import asynccontextmanager
from typing_extensions import Self
from sqlalchemy import URL, text
from sqlalchemy.ext.asyncio import (
    create_async_engine, async_sessionmaker, 
    AsyncSession, AsyncEngine
)
from sqlalchemy.pool import AsyncAdaptedQueuePool

from app.core.config import Config


class Postgres_Async:
    def __init__(self) -> None:
        self.engine: AsyncEngine | None = None
        self.session_factory: async_sessionmaker[AsyncSession] | None = None

    def init(self, config: Config) -> Self:
        """Initialize the PostgreSQL engine and session factory."""
        if self.engine is not None:
            return self

        url = URL.create(
            drivername="postgresql+asyncpg",
            username=config.POSTGRES_USER,
            password=config.POSTGRES_PASSWORD,
            host=config.POSTGRES_HOST,
            port=config.POSTGRES_PORT,
            database=config.POSTGRES_DB
        )
        self.engine = create_async_engine(
            url,
            echo=config.POSTGRES_ECHO_LOG,
            poolclass=AsyncAdaptedQueuePool,
            pool_size=config.POSTGRES_POOL_SIZE,
            max_overflow=config.POSTGRES_MAX_OVERFLOW,
            pool_timeout=config.POSTGRES_POOL_TIMEOUT,
            pool_recycle=config.POSTGRES_POOL_RECYCLE,
            pool_pre_ping=config.POSTGRES_POOL_PRE_PING,
            connect_args={
                "connect_timeout": config.POSTGRES_CONNECT_TIMEOUT,
                "options": f"-c statement_timeout={config.POSTGRES_COMMAND_TIMEOUT * 1000}",
            },
        )

        self.async_session_factory = async_sessionmaker(
            self.engine,
            expire_on_commit=False,
            autoflush=False,
        )

        return self

    async def close(self) -> None:
        """Dispose the connection pool."""
        if self.engine is not None:
            await self.engine.dispose()
            self.engine = None
            self.session_factory = None

    @asynccontextmanager
    async def session(self) -> AsyncGenerator[AsyncSession, None]:
        """Create a database session with automatic cleanup."""
        if self.session_factory is None:
            raise RuntimeError("Postgres has not been initialized")

        session = self.async_session_factory()

        try:
            yield session
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()

    async def health_check(self) -> bool:
        """Check whether PostgreSQL is reachable."""
        if self.engine is None:
            raise RuntimeError("Postgres has not been initialized")

        try:
            async with self.engine.connect() as connection:
                await connection.execute(text("SELECT 1"))
            return True
        except Exception:
            return False


