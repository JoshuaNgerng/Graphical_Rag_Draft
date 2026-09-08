from typing import Sequence
from pydantic import BaseModel

from app.core.config import Config
from app.knowledge_graph.models.processing_chunk import (
    ChunksProcessing, ChunkDataProcess, ChunkData,
    EntityExtraction, RelationshipExtraction
)

from app.knowledge_graph.phase3.relationship_resolver import RelationshipResolver
from app.models.entity_relationship import RelationshipNode, EntityNode
from app.neo4j.driver import Neo4jDriver
from app.ollama.embedding import Embedding

class NodeConnection(BaseModel):
    relationship: RelationshipNode
    source: EntityNode
    target: EntityNode

def run_phase3(phase2: Sequence[ChunksProcessing], config: Config):
    resolver = RelationshipResolver(config)
    driver = Neo4jDriver(config)
    for process in phase2:
        for d in process.data:
            e = d.entities
            for r in d.relationships:
                connection = _check_relationship_entity_ref(r, e)
                if not connection: continue
                r.resolved = connection.relationship
                existing_relationships = driver.get_relationships_between_entities(
                    connection.source.id, connection.target.id
                )
                match_decision = resolver.resolve_relationship(
                    r.resolved, connection.source, connection.target, existing_relationships
                )
                if match_decision == "UNKNOWN":
                    continue
                if match_decision == "NEW":
                    r.resolved = match_decision.relationship_node
                


def _check_relationship_entity_ref(
    relationship: RelationshipExtraction, 
    entities: list[EntityExtraction]
) -> None | NodeConnection:
    observation = relationship.observation
    target = next(
        (
            e.resolved for e in entities 
            if e.observation.name == observation.target
            ), None
    )
    source = next(
        (
            e.resolved for e in entities 
            if e.observation.name == observation.source
            ), None
    )
    if target is None or source is None:
        return None
    type_ = observation.type
    id_ = f"{source.id}:{type_}:{target.id}"
    return NodeConnection(
        relationship=RelationshipNode(
            id=id_,
            type=type_,
            source_id=source.id,
            target_id=target.id
        ),
        source=source, target=target
    )

