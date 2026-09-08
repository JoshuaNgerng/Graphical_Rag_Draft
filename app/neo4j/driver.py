from neo4j import GraphDatabase
from app.core.config import Config
from app.models.documents import Chunk
from app.models.entity_relationship import (
    EntityNode, RelationshipNode, RelationshipTypeNode
)
from app.models.observations import (
    EntityContext, Claim
)

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
        self,
        chunks: list[Chunk],
    ):

        self.driver.execute_query(
            """
            UNWIND $chunks AS chunk

            MERGE (d:Document {
                id: chunk.document_id
            })

            MERGE (c:Chunk {
                id: chunk.chunk_id
            })

            SET
                c.text = chunk.text,
                c.chunk_index = chunk.chunk_index,
                c.page_start = chunk.page_start,
                c.page_end = chunk.page_end,
                c.section = chunk.section,
                c.embedding = chunk.embedding

            MERGE (d)-[:CONTAINS]->(c)
            """,
            chunks=[c.model_dump() for c in chunks],
            database_=self.database_name,
        )

    def save_entities(
        self,
        entities: list[EntityNode],
    ):
        self.driver.execute_query(
            """
            UNWIND $entities AS entity

            MATCH (c:Chunk {id: entity.chunk_id})

            MERGE (e:Entity {id: entity.id})

            SET
                e.name = entity.name,
                e.normalize_name = entity.normalize_name,
                e.alias = entity.alias,
                e.canonical_type = entity.type,
                e.embedding = entity.embedding,
                e.description = entity.description

            MERGE (c)-[:MENTIONS]->(e)
            """,
            entities=[e.model_dump() for e in entities],
            database_=self.database_name,
        )

    def save_relationships(
        self,
        relationships: list[RelationshipNode],
    ):

        self.driver.execute_query(
            """
            UNWIND $relationships AS rel

            MATCH (source:Entity {id: rel.source_id})
            MATCH (target:Entity {id: rel.target_id})

            MERGE (source)-[r:RELATES {id: rel.id}]->(target)

            SET
                r.type = rel.type
            """,
            relationships=[r.model_dump() for r in relationships],
            database_=self.database_name,
        )

    def save_relationship_types(
        self,
        relationship_types: list[RelationshipTypeNode],
    ):
        self.driver.execute_query(
            """
            UNWIND $relationship_types AS rt

            MERGE (n:RelationshipType {id: rt.id})

            SET
                n.description = rt.description,
                n.source_type = rt.source_type,
                n.target_type = rt.target_type,
                n.embedding = rt.embedding
            """,
            relationship_types=[
                rt.model_dump()
                for rt in relationship_types
            ],
            database_=self.database_name,
        )

    def save_claims(
        self,
        claims: list[Claim],
    ):
        self.driver.execute_query(
            """
            UNWIND $claims AS claim

            MATCH (chunk:Chunk {id: claim.chunk_id})
            MATCH (subject:Entity {id: claim.subject_id})
            MATCH (object:Entity {id: claim.object_id})

            MATCH (subject)-[r:RELATES {id: claim.relationship_id}]->(object)
            
            MERGE (c:Claim {id: claim.id})

            SET
                c.predicate = claim.predicate,
                c.relationship_id = claim.relationship_id,
                c.evidence_text = claim.evidence_text,
                c.confidence = claim.confidence

            MERGE (chunk)-[:SUPPORTS]->(c)
            MERGE (c)-[:SUBJECT]->(subject)
            MERGE (c)-[:OBJECT]->(object)
            """,
            claims=[c.model_dump() for c in claims],
            database_=self.database_name,
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
    ) -> dict[float, EntityNode]:

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
                score AS fulltext_score
            ORDER BY score DESC
            LIMIT $limit
            """,
            query=name,
            limit=limit,
            database_=self.database_name,
        )

        return {
            row['fulltext_score']:
            EntityNode(
                id=row["entity_id"],
                name=row["name"],
                normalize_name=row['normalize_name'],
                alias=row['alias'],
                type=row["entity_type"],
                description=row["description"],
                embedding=row["embedding"]
            )
            for row in result.records
        }

    def search_entity_candidates_by_vector(
        self,
        embedding: list[float],
        limit: int = 10
    ) -> dict[float, EntityNode]:

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
                score AS semantic_score

            ORDER BY score DESC
            """,
            embedding=embedding,
            limit=limit
        )

        return {
            row['semantic_score']:
            EntityNode(
                id=row["entity_id"],
                name=row["name"],
                normalize_name=row['normalize_name'],
                alias=row['alias'],
                type=row["entity_type"],
                description=row["description"],
                embedding=row["embedding"]
            )
            for row in result.records
        }

    def get_entity_context(
        self,
        entity_id: str,
        context_embedding: list[float],
        top_k: int = 100,
        limit: int = 10
    ) -> dict[float, EntityContext]:

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
                claim.evidence_text AS evidence,
                claim.confidence AS confidence,
                chunk.id AS chunk_id,
                chunk.text AS chunk_text,
                score AS semantic_score

            ORDER BY semantic_score DESC
            LIMIT $limit
            """,
            context_embedding=context_embedding,
            top_k=top_k,
            entity_id=entity_id,
            limit=limit
        )
        return {
            r['semantic_score']:
            EntityContext.model_validate(r) 
            for r in result.records
        }

    def get_relationships_between_entities(
        self,
        source_id: str,
        target_id: str,
        limit = 50
    ) -> list[RelationshipNode]:

        result = self.driver.execute_query(
            """
            MATCH (source:Entity {id: $source_id})
            -[r:RELATES]-
            (target:Entity {id: $target_id})

            RETURN
                source.id AS source_id,
                target.id AS target_id,
                r.id AS id,
                r.type AS relationship_type,
                r.description AS description

            LIMIT $limit
            """,
            source_id=source_id,
            target_id=target_id,
            limit=limit,
            database_=self.database_name,
        )

        return [
            RelationshipNode.model_validate(row)
            for row in result.records
        ]

    def close(self):
        self.driver.close()

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