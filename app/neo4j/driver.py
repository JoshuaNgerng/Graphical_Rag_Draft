from pydantic import BaseModel
from neo4j import GraphDatabase, EagerResult
from typing import TypeVar
from app.core.config import Config
from app.models.documents import Chunk
from app.models.entity_relationship import (
    EntityNode, RelationshipNode, RelationshipType,
    RelationshipCandidate
)
from app.models.observations import (
    EntityContext, Claim
)
from app.models.driver_query_results import (
    SaveResult, DataResult
)

T = TypeVar("T", bound=BaseModel)

class Neo4jDriver:

    def __init__(self, config: Config) -> None:

        self.driver = GraphDatabase.driver(
            config.DRIVER_URL,
            auth=(
                "neo4j",
                config.DRIVER_PASSWORD,
            ),
        )

        self.database_name = (
            config.DRIVER_DATABASE
        )

    def save_chunks(
            self, chunks: list[Chunk]
    ) -> SaveResult:

        result = self.driver.execute_query(
            """
            UNWIND $chunks AS chunk

            MERGE (d:Document {id: chunk.document_id})
            MERGE (c:Chunk {id: chunk.chunk_id})

            SET
                c.text = chunk.text,
                c.chunk_index = chunk.chunk_index,
                c.page_start = chunk.page_start,
                c.page_end = chunk.page_end,
                c.section = chunk.section,
                c.embedding = chunk.embedding

            MERGE (d)-[:CONTAINS]->(c)

            RETURN count(*) AS passed
            """,
            chunks=[c.model_dump() for c in chunks],
            database_=self.database_name,
        )

        passed = result.records[0]["passed"]

        return SaveResult(
            total=len(chunks),
            passed=passed,
            failed=len(chunks) - passed
        )


    def save_entities(
        self, entities: list[EntityNode]
    ) -> SaveResult:
        
        result = self.driver.execute_query(
            """
            UNWIND $claims AS claim

            OPTIONAL MATCH (chunk:Chunk {id: claim.chunk_id})
            OPTIONAL MATCH (subject:Entity {id: claim.subject_id})
            OPTIONAL MATCH (object:Entity {id: claim.object_id})
            OPTIONAL MATCH (
                subject)-[r:RELATES {id: claim.relationship_id}]->(object
            )

            WITH claim, chunk, subject, object, r

            FOREACH (_ IN CASE
                WHEN chunk IS NOT NULL
                AND subject IS NOT NULL
                AND object IS NOT NULL
                AND r IS NOT NULL
                THEN [1]
                ELSE []
            END |
                MERGE (c:Claim {id: claim.id})

                SET
                    c.predicate = claim.predicate,
                    c.relationship_id = claim.relationship_id,
                    c.evidence_text = claim.evidence_text,
                    c.confidence = claim.confidence

                MERGE (chunk)-[:SUPPORTS]->(c)
                MERGE (c)-[:SUBJECT]->(subject)
                MERGE (c)-[:OBJECT]->(object)
            )

            RETURN
                claim.id AS claim_id,
                CASE
                    WHEN chunk IS NULL THEN "CHUNK_NOT_FOUND"
                    WHEN subject IS NULL THEN "SUBJECT_NOT_FOUND"
                    WHEN object IS NULL THEN "OBJECT_NOT_FOUND"
                    WHEN r IS NULL THEN "RELATIONSHIP_NOT_FOUND"
                    ELSE "OK"
                END AS status
            """,
            entities=[e.model_dump() for e in entities],
            database_=self.database_name,
        )

        return self._build_save_result(
            total=len(entities),
            records=result.records,
            id_field="entity_id",
        )

    def save_relationship_types(
        self, relationship_types: list[RelationshipType],
        update_existing: bool = True
    ) -> SaveResult:
        
        result = self.driver.execute_query(
            """
            UNWIND $relationship_types AS rt

            OPTIONAL MATCH (existing:RelationshipType {id: rt.id})

            CALL {
                WITH rt, existing
                WHERE existing IS NULL

                CREATE (n:RelationshipType {
                    id: rt.id,
                    description: rt.description,
                    source_type: rt.source_type,
                    target_type: rt.target_type,
                    embedding: rt.embedding
                })

                RETURN n

                UNION ALL

                WITH rt, existing
                WHERE existing IS NOT NULL
                AND $update_existing = true

                SET
                    existing.description = rt.description,
                    existing.source_type = rt.source_type,
                    existing.target_type = rt.target_type,
                    existing.embedding = rt.embedding

                RETURN existing AS n
            }

            RETURN count(n) AS count
            """,
            relationship_types=[
                rt.model_dump()
                for rt in relationship_types
            ],
            update_existing=update_existing,
            database_=self.database_name,
        )

        count = result.records[0]["count"]

        return SaveResult(
            total=len(relationship_types),
            passed=count,
            failed=len(relationship_types) - count
        )

    def save_relationships(
        self, relationships: list[RelationshipNode]
    ) -> SaveResult:

        result = self.driver.execute_query(
            """
            UNWIND $relationships AS rel

            OPTIONAL MATCH (source:Entity {id: rel.source_id})
            OPTIONAL MATCH (target:Entity {id: rel.target_id})
            OPTIONAL MATCH (rt:RelationshipType {id: rel.relationship_type_id})

            WITH rel, source, target, rt

            FOREACH (_ IN CASE
                WHEN source IS NOT NULL
                AND target IS NOT NULL
                AND rt IS NOT NULL
                THEN [1]
                ELSE []
            END |
                MERGE (source)-[r:RELATES {id: rel.id}]->(target)
                SET r.type = rt.id
            )

            RETURN
                rel.id AS relationship_id,
                CASE
                    WHEN source IS NULL THEN "SOURCE_NOT_FOUND"
                    WHEN target IS NULL THEN "TARGET_NOT_FOUND"
                    WHEN rt IS NULL THEN "RELATIONSHIP_TYPE_NOT_FOUND"
                    ELSE "OK"
                END AS status
            """,
            relationships=[
                r.model_dump()
                for r in relationships
            ],
            database_=self.database_name,
        )

        return self._build_save_result(
            total=len(relationships),
            records=result.records,
            id_field="relationship_id",
        )

    def save_claims(
            self, claims: list[Claim]
    ) -> SaveResult:
        
        result = self.driver.execute_query(
            """
            UNWIND $claims AS claim

            OPTIONAL MATCH (chunk:Chunk {id: claim.chunk_id})
            OPTIONAL MATCH (subject:Entity {id: claim.subject_id})
            OPTIONAL MATCH (object:Entity {id: claim.object_id})
            OPTIONAL MATCH (subject)-[r:RELATES {id: claim.relationship_id}]->(object)

            WITH claim, chunk, subject, object, r,
                chunk IS NOT NULL
                AND subject IS NOT NULL
                AND object IS NOT NULL
                AND r IS NOT NULL AS valid

            WITH claim, chunk, subject, object, valid
            WHERE valid

            MERGE (c:Claim {id: claim.id})

            SET
                c.predicate = claim.predicate,
                c.relationship_id = claim.relationship_id,
                c.evidence_text = claim.evidence_text,
                c.confidence = claim.confidence

            MERGE (chunk)-[:SUPPORTS]->(c)
            MERGE (c)-[:SUBJECT]->(subject)
            MERGE (c)-[:OBJECT]->(object)

            RETURN count(*) AS passed
            """,
            claims=[c.model_dump() for c in claims],
            database_=self.database_name,
        )

        passed = result.records[0]["passed"]

        return SaveResult(
            total=len(claims),
            passed=passed,
            failed=len(claims) - passed
        )


    def get_entity_ids(
        self,
        names: set[str],
    ) -> dict[str, str]:
        
        result = self.driver.execute_query(
            """
            UNWIND $names AS name

            MATCH (e:Entity)
            WHERE toLower(e.name) = toLower(name)

            RETURN
                name,
                e.id AS entity_id
            """,
            names=list(names),
            database_=self.database_name,
        )

        return {
            row["name"]: row["entity_id"]
            for row in result.records
        }

    def search_exact_entity(
        self, 
        name: str
    ) -> EntityNode | None:

        result = self.driver.execute_query(
            """
            MATCH (e:Entity)
            WHERE e.normalize_name = $normalize_name
            RETURN e
            """,
            normalize_name=name,
            database_=self.database_name
        )
        print(result)
        if not result:
            return None
        return EntityNode.model_validate(result)

    def search_entity_candidates(
        self,
        name: str,
        limit: int = 10,
    ) -> list[DataResult[EntityNode]]:

        result = self.driver.execute_query(
            """
            CALL db.index.fulltext.queryNodes(
                'entity_name_fulltext',
                $query
            )
            YIELD node, score
            RETURN
                node.id AS entity_id,
                node.name AS name,
                node.normalize_name AS normalize_name,
                node.alias AS alias,
                node.canonical_type AS entity_type,
                node.description AS description,
                node.embedding AS embedding,
                score AS score
            ORDER BY score DESC
            LIMIT $limit
            """,
            query=name,
            limit=limit,
            database_=self.database_name,
        )

        return self._build_data_result(
            EntityNode, result
        )

    def search_entity_candidates_by_vector(
        self,
        embedding: list[float],
        limit: int = 10
    ) -> list[DataResult[EntityNode]]:

        result = self.driver.execute_query(
            """
            CALL db.index.vector.queryNodes(
                'entity_embedding_index',
                $limit,
                $embedding
            )
            YIELD node, score

            RETURN
                node.id AS entity_id,
                node.name AS name,
                node.normalize_name AS normalize_name,
                node.alias AS alias,
                node.canonical_type AS entity_type,
                node.description AS description,
                node.embedding AS embedding,
                score AS score

            ORDER BY score DESC
            """,
            embedding=embedding,
            limit=limit
        )

        return self._build_data_result(
            EntityNode, result
        )

    def get_entity_context(
        self,
        entity_id: str,
        context_embedding: list[float],
        top_k: int = 100,
        limit: int = 10,
    ) -> list[DataResult[EntityContext]]:

        result = self.driver.execute_query(
            """
            CALL db.index.vector.queryNodes(
                'chunk_embedding_index',
                $top_k,
                $context_embedding
            )
            YIELD node AS chunk, score

            MATCH (chunk)-[:SUPPORTS]->(claim:Claim)

            MATCH (claim)-[:SUBJECT|OBJECT]->(e:Entity {id: $entity_id})

            MATCH (claim)-[:SUBJECT]->(subject:Entity)
            MATCH (claim)-[:OBJECT]->(object:Entity)

            RETURN DISTINCT
                claim.id AS claim_id,
                subject.id AS subject_id,
                subject.name AS subject_name,
                claim.predicate AS predicate,
                object.id AS object_id,
                object.name AS object_name,
                claim.evidence_text AS evidence_text,
                claim.confidence AS confidence,
                chunk.id AS chunk_id,
                chunk.text AS chunk_text,
                score AS score

            ORDER BY score DESC
            LIMIT $limit
            """,
            context_embedding=context_embedding,
            top_k=top_k,
            entity_id=entity_id,
            limit=limit,
            database_=self.database_name,
        )

        return self._build_data_result(
            EntityContext, result
        )


    def get_relationships_between_entities(
        self, source_id: str, target_id: str,
        context_embedding: list[float],
        limit: int = 10,
    ) -> list[DataResult[RelationshipCandidate]]:

        result = self.driver.execute_query(
            """
            MATCH (source:Entity {id: $source_id})
                -[r:RELATES]->
                (target:Entity {id: $target_id})

            MATCH (rt:RelationshipType {id: r.type})

            WITH
                r,
                source,
                target,
                rt,
                vector.similarity.cosine(
                    rt.embedding,
                    $context_embedding
                ) AS semantic_score

            RETURN
                r.id AS relationship_id,
                rt.id AS relationship_type_id,

                source.id AS source_id,
                target.id AS target_id,

                rt.description AS description,
                rt.source_type AS source_type,
                rt.target_type AS target_type,

                semantic_score AS score

            ORDER BY semantic_score DESC
            LIMIT $limit
            """,
            source_id=source_id,
            target_id=target_id,
            context_embedding=context_embedding,
            limit=limit,
            database_=self.database_name,
        )

        return self._build_data_result(
            RelationshipCandidate, result
        )

    def get_relationships_between_entity_types(
            self, source_type: str, target_type: str,
            context_embedding: list[float],
            limit: int = 10
    ) -> list[DataResult[RelationshipCandidate]]: 

        result = self.driver.execute_query(
            """
            MATCH (rt:RelationshipType)
            WHERE rt.source_type = $source_type
            AND rt.target_type = $target_type

            WITH
                rt,
                vector.similarity.cosine(
                    rt.embedding,
                    $context_embedding
                ) AS semantic_score

            RETURN
                rt.id AS relationship_type_id,
                rt.description AS description,
                rt.source_type AS source_type,
                rt.target_type AS target_type,
                semantic_score AS score

            ORDER BY semantic_score DESC
            LIMIT $limit
            """,
            source_type=source_type,
            target_type=target_type,
            context_embedding=context_embedding,
            limit=limit
        )

        return self._build_data_result(
            RelationshipCandidate, result
        )

    def close(self):
        self.driver.close()

    def _build_save_result(
        self,
        total: int,
        records,
        id_field: str,
    ) -> SaveResult:
        failed_ids = [
            row[id_field]
            for row in records
            if row["status"] != "OK"
        ]

        return SaveResult(
            total=total,
            passed=len(records) - len(failed_ids),
            failed=len(failed_ids),
            failed_ids=failed_ids,
        )

    def _build_data_result(
            self,
            data_type: type[T],
            query_result: EagerResult
    ) -> list[DataResult[T]]:
        data = [
            DataResult(
                score=row["score"],
                data=data_type.model_validate(row),
            )
            for row in query_result.records
        ]
        data.sort(key=lambda x:x.score, reverse=True)
        return data

'''
save relationship type

UNWIND $relationship_types AS rt

MERGE (n:RelationshipType {id: rt.id})

ON CREATE SET
    n.description = rt.description,
    n.source_type = rt.source_type,
    n.target_type = rt.target_type,
    n.embedding = rt.embedding

WITH n, rt

WHERE $update_existing = true

SET
    n.description = rt.description,
    n.source_type = rt.source_type,
    n.target_type = rt.target_type,
    n.embedding = rt.embedding

RETURN count(n) AS count
'''

'''
useful functions to think about
# RelationshipType operations

get_relationship_type()
search_relationship_types()
save_relationship_type()
save_relationship_types()


# Relationship instance operations

get_entity_relationships()
get_relationship_between_entities()
save_relationship()
save_relationships()
'''

'''
draft for phase 2

def get_phase2_context(
    self,
    entities: list[EntityObservation],
    relationships: list[RelationshipObservation],
) -> Phase2Context:

    names = {
        entity.name
        for entity in entities
    }

    names.update(
        relationship.source
        for relationship in relationships
    )

    names.update(
        relationship.target
        for relationship in relationships
    )

    candidates = self.find_entity_candidates(
        names=list(names),
        limit_per_name=5,
    )

    entity_ids = [
        entity.entity_id
        for entity in candidates
    ]

    existing_relationships = (
        self.get_entity_relationships(
            entity_ids=entity_ids,
        )
    )

    return Phase2Context(
        new_entities=entities,
        new_relationships=relationships,
        existing_entities=candidates,
        existing_relationships=existing_relationships,
    )
'''