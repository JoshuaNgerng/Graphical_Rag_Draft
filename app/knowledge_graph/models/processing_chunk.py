# from pydantic import BaseModel, Field
from dataclasses import dataclass, field
from html import entities 

from app.models.documents import ChunkData
from app.models.entity_relationship import (
    RelationshipNode, EntityNode, RelationshipType 
)
from app.models.observations import (
    RelationshipObservation,
    EntityNormalizeObservation,
    EntityContext
)

@dataclass
class EntityExtraction:
    observation: EntityNormalizeObservation
    resolved: EntityNode | None = field(default=None)
    context: list[EntityContext] = field(default_factory=list)
    resolved_id: str | None = field(default=None)

@dataclass
class RelationshipExtraction:
    observation: RelationshipObservation
    source_entity: EntityNode | None = field(default=None)
    target_entity: EntityNode | None = field(default=None)
    resolved: RelationshipNode | None = field(default=None) 
    resolved_type: RelationshipType | None = field(default=None)
    resolve_id: str | None = field(default=None)
    create_new: bool = field(default=True)
    validation: bool = field(default=False)

@dataclass
class ChunkDataExtraction:
    chunk_info: ChunkData
    context_embedding: list[float] = field(default_factory=list)
    entities: list[EntityExtraction] = field(default_factory=list)
    relationships: list[RelationshipExtraction] = field(default_factory=list)
