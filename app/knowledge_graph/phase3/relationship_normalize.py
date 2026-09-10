from app.core.config import Config
from app.knowledge_graph.models.processing_chunk import (
    ChunksProcessing, ChunkDataProcess, ChunkData,
    EntityExtraction, RelationshipExtraction
)

from app.models.entity_relationship import RelationshipNode
# from app.neo4j.driver import Neo4jDriver
# from app.ollama.embedding import Embedding

class RelationshipNormalization:
    def __init__(self) -> None: pass

    def normalize(
            self, relationships: list[RelationshipExtraction], 
            entities: list[EntityExtraction]
        ):
        for r in relationships:
            r.resolved = self.resolve_entities(r, entities)


    def resolve_entities(
            self, relationship: RelationshipExtraction, 
            entities: list[EntityExtraction]
        ):
        observation = relationship.observation
        target_id = next(
            (
                e.resolved_id for e in entities 
                if e.observation.name == observation.target
             ), None
        )
        source_id = next(
            (
                e.resolved_id for e in entities 
                if e.observation.name == observation.source
             ), None
        )
        if target_id is None or source_id is None:
            return None
        type_ = observation.relationship_type_id
        id_ = f"{source_id}:{type_}:{target_id}"
        return RelationshipNode(
            id=id_,
            relationship_type_id=type_,
            source_id=source_id,
            target_id=target_id
        )

    def resolve_predicate_direction(
            self, relationship: RelationshipExtraction 
    ):
        pass
