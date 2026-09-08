from pydantic import BaseModel, Field

from app.models.documents import ChunkData
from app.models.entity_relationship import (
    RelationshipNode, EntityNode 
)
from app.models.observations import (
    RelationshipObservation,
    EntityNormalizeObservation,
    EntityContext
)

class RelationshipExtraction(BaseModel):
    observation: RelationshipObservation
    resolved: RelationshipNode | None = None
    validation: bool = Field(default=False)

class EntityExtraction(BaseModel):
    observation: EntityNormalizeObservation
    resolved: EntityNode | None = None
    context: list[EntityContext] = Field(
        default_factory=list
    )
    resolved_id: str | None = None

class ChunkDataProcess(BaseModel):
    chunk_info: ChunkData
    entities: list[EntityExtraction] = Field(
        default_factory=list
    )
    relationships: list[RelationshipExtraction] = Field(
        default_factory=list
    )

class ChunksProcessing(BaseModel):
    data: list[ChunkDataProcess]