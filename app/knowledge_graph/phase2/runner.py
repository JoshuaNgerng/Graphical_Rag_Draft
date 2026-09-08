from typing import Sequence

from app.core.config import Config
from app.knowledge_graph.models.processing_chunk import (
    ChunksProcessing, EntityExtraction
)


from app.knowledge_graph.phase2.entity_repo import EntityRepo
from app.knowledge_graph.phase2.retrival import RetrievalCandidates
from app.knowledge_graph.phase2.entity_resolver import EntityResolver

from app.neo4j.driver import Neo4jDriver
from app.ollama.embedding import Embedding

def run_phase2(phase1: Sequence[ChunksProcessing], config: Config):
    res = []
    driver = Neo4jDriver(config)
    embded = Embedding(config)
    retrival = RetrievalCandidates(driver, embded)
    entity_repo = EntityRepo(driver, embded)
    resolver = EntityResolver(config)

    for processing_chunk in phase1:
        resolved_entites = []
        for d in processing_chunk.data:
            context = d.chunk_info.text
            for e in d.entities:
                _resolve_entity_pipeline(
                    e, context, 
                    retrival, resolver, entity_repo
                )
                if e.resolved_id and e.resolved:
                    resolved_entites.append(e.resolved)
        entity_repo.save_new_entity_bulk(resolved_entites)

    return res

def _resolve_entity_pipeline(
        entity_object: EntityExtraction,
        context: str,
        retrival: RetrievalCandidates,
        resolver: EntityResolver,
        repo: EntityRepo
):
    obs = entity_object.observation
    candidates = retrival.rank_all_likely_candidates(obs, context)
    buffer = [ ]
    entity_nodes = [ ]
    for node, entity_context, _ in candidates:
        buffer.append((node, entity_context))
        entity_nodes.append(node)
    decision = resolver.decide_entity(obs, context, buffer)
    new_entity = repo.resolve_entity_decision(entity_nodes, decision)
    entity_object.resolved = new_entity
    if new_entity: 
        resolved_id = new_entity.id
        entity_object.resolved_id = resolved_id
        entity_object.context = []
        for node, entity_context in buffer:
            if node.id == resolved_id:
                entity_object.context = entity_context
