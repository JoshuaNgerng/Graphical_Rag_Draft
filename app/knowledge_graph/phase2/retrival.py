from app.models.entity_relationship import (
    EntityNode, EntityNormalize
)
from app.models.observations import EntityContext
from app.neo4j.driver import Neo4jDriver
from app.llm_service.ollama.embedding import Embedding
from typing import Self
from dataclasses import dataclass

@dataclass
class CandidateScoring:
    exact_match: float = 0.0
    semantic_match: float = 0.0
    vector_match: float = 0.0
    context_match: float = 0.0
    final_score: float = 0.0

    def finalize_score(self) -> Self:
        self.final_score = (
            self.exact_match + self.semantic_match + 
            self.vector_match + self.context_match
        ) / 4
        return self

class RetrievalCandidates:
    def __init__(
            self, driver: Neo4jDriver, embedding: Embedding
        ) -> None:
        self.driver = driver
        self.embedding = embedding
        
    def rank_all_likely_candidates(
        self,
        entity: EntityNormalize,
        context: str | list[float],
        candidate_limit: int = 30,
        final_limit: int = 10,
    ):
        candidates = self.retrieve_likely_candidates(
            entity,
            limit=candidate_limit,
        )

        ranked = self.rank_by_candidate_list_by_context(
            candidates,
            context,
        )

        ranked.sort(
            key=lambda x: x[2].final_score,
            reverse=True,
        )

        return ranked[:final_limit]

    def retrieve_likely_candidates(self,  entity: EntityNormalize, limit=10):
        name = entity.normalize_name
        entity_embedding = self._encode_entity(entity)
        exact_match = self.driver.search_exact_entity(name)
        semantic_similar = self.driver.search_entity_candidates(name)
        vector_similar = self.driver.search_entity_candidates_by_vector(
            list(entity_embedding)
        )
        buffer: dict[str, tuple[EntityNode, CandidateScoring]] = {}
        if exact_match:
            buffer[exact_match.id] = (exact_match, CandidateScoring(exact_match=1.0))
        for data in semantic_similar:
            id_ = data.data.id
            if not id_ in buffer:
                buffer[id_] = (data.data, CandidateScoring())
            buffer[id_][1].semantic_match = data.score
        for data in vector_similar:
            id_ = data.data.id
            if not id_ in buffer:
                buffer[id_] = (data.data, CandidateScoring())
            buffer[id_][1].vector_match = data.score
        res = [(v[0], v[1].finalize_score()) for v in buffer.values()]
        res.sort(key=lambda x: x[1].final_score, reverse=True)
        return res[:limit]

    def rank_by_candidate_list_by_context(
            self, entites: list[tuple[EntityNode, CandidateScoring]], 
            context: str | list[float]
        ) -> list[tuple[EntityNode, list[EntityContext], CandidateScoring]]:
        if isinstance(context, str):
            context_embedding = list(self.embedding.encode(context))
        else:
            context_embedding = context
        res : list[tuple[EntityNode, list[EntityContext], CandidateScoring]] = []
        for e in entites:
            entity, score = e
            entity_context = self.driver.get_entity_context(
                entity.id, context_embedding
            )
            if not entity_context:
                res.append((entity, [], score))
                continue
            score.context_match = entity_context[0].score
            res.append(
                (
                    entity, 
                    [e.data for e in entity_context[:10]], 
                    score.finalize_score()
                )
            )
        return res


    def _encode_entity(self, entity: EntityNormalize):
        text = f'name:{entity.name}, type:{entity.type}, description:{entity.description}'
        return self.embedding.encode(text)

