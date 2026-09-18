from enum import StrEnum, auto
from sqlalchemy import Boolean, ForeignKey, Integer, String, Enum
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.db_base import TableBase
from app.models.decisions import DecisionType, ChooseType
from app.knowledge_graph.models.processing_chunk import EntityExtraction, RelationshipExtraction
from app.models.pydantic_json import PydanticJSON

class Stats(StrEnum):
    START = auto()
    PHASE1 = auto()
    PHASE2 = auto()
    PHASE3 = auto()
    COMPLETE = auto()

class Chunk(TableBase):
    __tablename__ = "chunk"
    doc_id: Mapped[str] = mapped_column(String, unique=True, index=True)
    chunk_id: Mapped[str] = mapped_column(String, unique=True, index=True)
    text: Mapped[str] = mapped_column(String)
    chunk_index: Mapped[int] = mapped_column(Integer)
    page_start: Mapped[int] = mapped_column(Integer)
    page_end: Mapped[int] = mapped_column(Integer)
    extracted: Mapped[bool] = mapped_column(Boolean, default=False)
    job_id: Mapped[int] = mapped_column(Integer, ForeignKey("job_task.id", ondelete="CASCADE"))
    job_task: Mapped['JobTask'] = relationship('JobTask', foreign_keys=[job_id], back_populates='chunks')

class Entities(TableBase):
    __tablename__ = "entities"
    chunk_pk: Mapped[int] = mapped_column(Integer, ForeignKey("chunk.id", ondelete="CASCADE"))
    data: Mapped[EntityExtraction] = mapped_column(PydanticJSON(EntityExtraction))
    decision: Mapped[DecisionType | None] = mapped_column(Enum, default=None)
    job_id: Mapped[int] = mapped_column(Integer, ForeignKey("job_task.id", ondelete="CASCADE"))
    job_task: Mapped['JobTask'] = relationship('JobTask', foreign_keys=[job_id], back_populates='entities')

class Relationships(TableBase):
    __tablename__ = "relationships"
    chunk_pk: Mapped[int] = mapped_column(Integer, ForeignKey("chunk.id", ondelete="CASCADE"))
    data: Mapped[RelationshipExtraction] = mapped_column(PydanticJSON(RelationshipExtraction))
    choose: Mapped[ChooseType | None] = mapped_column(Enum, default=None)
    job_id: Mapped[int] = mapped_column(Integer, ForeignKey("job_task.id", ondelete="CASCADE"))
    job_task: Mapped['JobTask'] = relationship('JobTask', foreign_keys=[job_id], back_populates='relationships')

class JobTask(TableBase):
    __tablename__ = "job_task"
    job_id: Mapped[str] = mapped_column(String, unique=True, index=True)
    doc_file_key: Mapped[str] = mapped_column(String, unique=True, index=True)

    chunks: Mapped[list[Chunk]] = relationship(back_populates='job_task', cascade="all, delete-orphan")
    entities: Mapped[list[Entities]] = relationship('Entities',  cascade="all, delete-orphan")
    relationships: Mapped[list[Relationships]] = relationship('Relationships',  cascade="all, delete-orphan")

