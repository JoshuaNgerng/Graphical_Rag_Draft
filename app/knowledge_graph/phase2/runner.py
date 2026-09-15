from typing import Sequence

from app.core.config import Config
from app.knowledge_graph.models.processing_chunk import (
    ChunkDataExtraction, EntityExtraction
)

from app.knowledge_graph.context_manager import DataProcessingContext
from app.neo4j.driver import Neo4jDriver

def run_phase2(
        phase1: Sequence[ChunkDataExtraction],
        ctx: DataProcessingContext
):
    for data in phase1:
        resolved_entites = []
        for e in data.entities:
            _resolve_entity_pipeline(
                e, data.chunk_info.text, 
                data.context_embedding, 
                ctx
            )
            if e.resolved_id and e.resolved:
                resolved_entites.append(e.resolved)
        ctx.entity_repo.save_new_entity_bulk(resolved_entites)

    return phase1

def _resolve_entity_pipeline(
        entity_object: EntityExtraction,
        context: str,
        context_embedding: list[float],
        ctx: DataProcessingContext
):
    obs = entity_object.observation
    candidates = ctx.retrieval.rank_all_likely_candidates(obs, context_embedding)
    buffer = [ ]
    entity_nodes = [ ]
    for node, entity_context, _ in candidates:
        buffer.append((node, entity_context))
        entity_nodes.append(node)
    decision = ctx.entity_resolver.decide_entity(obs, context, buffer)
    new_entity = ctx.entity_repo.resolve_entity_decision(entity_nodes, decision)
    entity_object.resolved = new_entity
    if new_entity: 
        resolved_id = new_entity.id
        entity_object.resolved_id = resolved_id
        entity_object.context = []
        for node, entity_context in buffer:
            if node.id == resolved_id:
                entity_object.context = entity_context
