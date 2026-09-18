from pydantic import BaseModel, Field

from app.models.documents import Chunk 
from app.models.entity_relationship import (
    RelationshipNode, EntityNode, RelationshipType 
)
from app.models.observations import (
    RelationshipObservation,
    EntityNormalizeObservation,
    EntityContext
)
from app.models.decisions import DecisionType, ChooseType

class EntityExtraction(BaseModel):
    observation: EntityNormalizeObservation
    resolved: EntityNode | None = Field(default=None)
    context: list[EntityContext] = Field(default_factory=list)
    resolved_id: str | None = Field(default=None)
    decision: DecisionType | None = Field(default=None)

class RelationshipExtraction(BaseModel):
    observation: RelationshipObservation
    source_entity: EntityNode | None = Field(default=None)
    target_entity: EntityNode | None = Field(default=None)
    resolved: RelationshipNode | None = Field(default=None) 
    resolved_type: RelationshipType | None = Field(default=None)
    resolve_id: str | None = Field(default=None)
    create_new: bool = Field(default=True)
    validation: bool = Field(default=False)
    choose: ChooseType | None = Field(default=None)

class ChunkDataExtraction(BaseModel):
    chunk_info: Chunk
    extracted: bool = Field(default=False)
    context_embedding: list[float] = Field(default_factory=list)
    entities: list[EntityExtraction] = Field(default_factory=list)
    relationships: list[RelationshipExtraction] = Field(default_factory=list)
