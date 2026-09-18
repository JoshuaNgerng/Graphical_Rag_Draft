from typing import Sequence
from pydantic import BaseModel, Field

from app.models.decisions import ChooseType, DecisionType
from app.knowledge_graph.models.processing_chunk import (
    ChunkDataExtraction,
    EntityExtraction, RelationshipExtraction
)
from app.knowledge_graph.context_manager import DataProcessingContext
from app.models.entity_relationship import (
    RelationshipNode, EntityNode, RelationshipType, gen_claim
)

def run_phase3(phase2: Sequence[ChunkDataExtraction], ctx: DataProcessingContext):
    res = []
    for data in phase2:
        resolved_type = []
        resolved_nodes = []
        for r in data.relationships:
            if r.choose is not None:
                continue
            _check_relationship_entity_ref(r, data.entities)
            if r.resolved is None: continue
            _resolve_relationship(r, data.context_embedding, ctx)
            decision = ctx.relationship_validator.validate(
                relationship.source_entity, relationship.target_entity,  # type: ignore
                relationship.resolved_type, context                      # type: ignore
            )
            r.choose = decision.choose
            r.validation = decision.choose == ChooseType.ACCEPT
            if not r.validation: continue
            if r.resolved_type:
                resolved_type.append(r.resolved_type)
            if r.resolved:
                resolved_nodes.append(r.resolved)
            r.observation.confidence = decision.confidence
        claims = [
            gen_claim(data.chunk_info, r.resolved, r.observation)
            for r in data.relationships
            if r.resolved and r.validation
        ]
        ctx.driver.save_relationship_types(resolved_type, update_existing=False)
        ctx.driver.save_relationships(resolved_nodes)
        ctx.driver.save_claims(claims)
        res.append(data)
    return res

            

def _check_relationship_entity_ref(
    relationship: RelationshipExtraction, 
    entities: list[EntityExtraction]
):
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
        return
    type_ = observation.relationship_type_id
    id_ = f"{source.id}:{type_}:{target.id}"
    relationship.target_entity = target
    relationship.source_entity = source
    relationship.resolved = RelationshipNode(
        id=id_,
        relationship_type_id=type_,
        source_id=source.id,
        target_id=target.id
    )

def _resolve_relationship(
        relationship: RelationshipExtraction,
        context: list[float],
        ctx: DataProcessingContext
    ):
    if (
        not (
            relationship.resolved and
            relationship.source_entity and
            relationship.target_entity
        )
    ): return
    existing = ctx.driver.get_relationships_between_entities(
        relationship.source_entity.id, 
        relationship.target_entity.id, context
    )
    if (
        len(existing) < 10 or
        max(c.score for c in existing) < 0.75
    ):
        more_candidate = ctx.driver.get_relationships_between_entity_types(
            relationship.source_entity.type, 
            relationship.target_entity.type, context
        )
        for e in existing:
            idx = -1
            for i, c in enumerate(more_candidate):
                if e.data.relationship_type_id == c.data.relationship_type_id:
                    idx = i
                    break
            if idx > 0:
                new_c = more_candidate.pop()
                e.score = (0.75 * e.score + 0.25 * new_c.score)
            else:
                e.score = 0.75 * e.score
        if more_candidate:
            buffer = []
            for c in more_candidate:
                c.score = c.score * 0.25
                buffer.append(c)
            existing.extend(buffer)
        existing.sort(key=lambda x:x.score, reverse=True)

    buffer = [c.data for c in existing]
    match_decision = ctx.relationship_resolver.resolve_relationship(
        relationship.resolved, relationship.source_entity,
        relationship.target_entity, buffer
    ) 
    if match_decision.decision == DecisionType.UNKNOWN:
        relationship.resolved = None
        return
    candidate = match_decision.relationship_candidate
    relationship.resolved = RelationshipNode.model_validate(candidate)
    relationship.resolved_type = RelationshipType.model_validate(candidate)
    relationship.create_new = match_decision.decision == DecisionType.CREATE

'''
1. Existing source→target relationships
       ↓
2. Rank them by context/predicate similarity
       ↓
3. If insufficient/low quality:
       ↓
4. source_type→target_type RelationshipType search
       ↓
5. Rank those
       ↓
6. Deduplicate by relationship_type_id
       ↓
7. Combine/rank candidates
       ↓
8. Send top ~5–10 candidates to LLM
       ↓
9. LLM decides MATCH / NEW / UNKNOWN
'''