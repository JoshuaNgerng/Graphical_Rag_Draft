# app/db/postgres.py

from collections.abc import Generator
from contextlib import contextmanager
from typing_extensions import Self

from sqlalchemy import URL, create_engine, text
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import QueuePool

from app.core.config import Config


class Postgres:
    def __init__(self) -> None:
        self.engine: Engine | None = None
        self.session_factory: sessionmaker[Session] | None = None

    def init(self, config: Config) -> Self:
        """Initialize the PostgreSQL engine and session factory."""
        if self.engine is not None:
            return self

        url = URL.create(
            drivername="postgresql+psycopg",
            username=config.POSTGRES_USER,
            password=config.POSTGRES_PASSWORD,
            host=config.POSTGRES_HOST,
            port=config.POSTGRES_PORT,
            database=config.POSTGRES_DB,
        )
        self.engine = create_engine(
            url,
            echo=config.POSTGRES_ECHO_LOG,
            poolclass=QueuePool,
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

        self.session_factory = sessionmaker(
            bind=self.engine,
            autoflush=False,
            expire_on_commit=False,
        )

        return self

    def close(self) -> None:
        """Dispose the connection pool."""
        if self.engine is not None:
            self.engine.dispose()
            self.engine = None
            self.session_factory = None

    @contextmanager
    def session(self) -> Generator[Session, None, None]:
        """Create a database session with automatic cleanup."""
        if self.session_factory is None:
            raise RuntimeError("Postgres has not been initialized")

        session = self.session_factory()

        try:
            yield session
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    def health_check(self) -> bool:
        """Check whether PostgreSQL is reachable."""
        if self.engine is None:
            raise RuntimeError("Postgres has not been initialized")

        try:
            with self.engine.connect() as connection:
                connection.execute(text("SELECT 1"))
            return True
        except Exception:
            return False


