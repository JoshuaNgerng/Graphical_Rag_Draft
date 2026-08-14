from enum import StrEnum, auto
from pydantic import BaseModel, Field

class EntityType(StrEnum):
    POLICY = auto()
    ORGANIZATION = auto()
    COUNTRY = auto()
    ENVIRONMENTAL_ISSUE = auto()
    POLLUTANT = auto()
    TARGET = auto()


class RelationshipType(StrEnum):
    ADDRESSES = auto()
    APPLIES_TO = auto()
    REGULATES = auto()
    ISSUED_BY = auto()
    SETS_TARGET = auto()

class Entity(BaseModel):
    name: str
    type: EntityType


class Relationship(BaseModel):
    source: str
    source_type: EntityType
    target: str
    target_type: EntityType
    type: RelationshipType
    evidence_text: str
    confidence: float

class GraphExtraction(BaseModel):
    entities: list[Entity] = Field(default_factory=list)
    relationships: list[Relationship] = Field(default_factory=list)