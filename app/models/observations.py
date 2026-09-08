from pydantic import BaseModel, Field, ConfigDict
from app.models.entity_relationship import (
    Entity, EntityNormalize, Relationship
)
from app.models.documents import Node

class Observation(BaseModel):
    evidence_text: str
    confidence: float

class Claim(Observation):
    chunk_id: str
    subject_id: str
    object_id: str
    relationship_id: str
    predicate: str

class ClaimNode(Node, Claim):
    pass

class EntityContext(Claim):
    claim_id: str
    subject_name: str
    object_name: str
    chunk_id: str
    chunk_text: str

class EntityObservation(Entity, Observation):
    model_config = ConfigDict(from_attributes=True)

class EntityNormalizeObservation(EntityNormalize, Observation):
    model_config = ConfigDict(from_attributes=True)

class RelationshipObservation(Relationship, Observation):
    source: str
    target: str

    model_config = ConfigDict(from_attributes=True)

class GraphObservation(BaseModel):
    entities: list[EntityObservation] = Field(default_factory=list)
    relationships: list[RelationshipObservation] = Field(default_factory=list)

    model_config = ConfigDict(from_attributes=True)

class GraphObservationNormalize(BaseModel):
    entities: list[EntityNormalizeObservation] = Field(default_factory=list)
    relationships: list[RelationshipObservation] = Field(default_factory=list)

    model_config = ConfigDict(from_attributes=True)