from datetime import datetime, timezone
from typing import Any
from unittest import result
from typing_extensions import Self

from sqlalchemy import DateTime, Integer, MetaData
from sqlalchemy.orm import mapped_column, Mapped, DeclarativeBase


convention = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}


metadata = MetaData(naming_convention=convention)

class Base(DeclarativeBase):
    metadata = MetaData(naming_convention=convention)

def utc_now() -> datetime:
    return datetime.now(timezone.utc)

class TableBase(Base):
    """Base class for all database tables with common columns."""
    __abstract__ = True
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True, autoincrement=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False
    )

    # Use this method to inspect data in logger debug or simple conversion to pydantic model
    def to_dict(self) -> dict[str, Any]:
        return {
            column.name: getattr(self, column.name)
            for column in self.__table__.columns
        }

    # use this method for conversion of internal api calls that use pydantic model to validate
    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Self:
        instance = cls()
        for column in cls.__table__.columns:
            if column.name in data:
                setattr(instance, column.name, data[column.name])

        return instance

    @classmethod
    def from_data(cls, data: Any) -> Self:
        instance = cls()
        for column in cls.__table__.columns:
            if hasattr(data, column.name):
                setattr(instance, column.name, getattr(data, column.name))

        return instance

