from typing import Callable, Generator, Protocol
from pathlib import Path
import uuid

from pymupdf import Document
from neo4j import GraphDatabase
from sentence_transformers import SentenceTransformer
from torch import chunk

from draft_neo4j.EntityNRelationship import *
from draft_neo4j.RelationshipExtractorOllama import RelationshipExtractorOllama
from draft_neo4j.Neo4jSchema import Neo4jSchema
from draft_neo4j.PDFParser import ChunkData

PdfChunker = Callable[[Document], Generator[ChunkData, None, None]]

class Neo4jIngestor:
    class Buffer:
        CHUNK_BUFFER_SIZE = 50
        def __init__(self) -> None:
            self.chunk = []
            self.entity = []
            self.relationship = []

        def clear(self): 
            self.chunk.clear()
            self.entity.clear()
            self.relationship.clear()

        def ready(self):
            return (
                len(self.chunk) >= self.CHUNK_BUFFER_SIZE
            )


    def __init__(self, config, chunker: PdfChunker) -> None:
        self.driver = GraphDatabase.driver(
            config.db_url,
            auth=("neo4j", config.db_password)
        )
        self.database = config.database
        self.embedding_model = SentenceTransformer(config.model_name)
        self.chunker = chunker
        self.extractor = RelationshipExtractorOllama()
        self.driver.verify_connectivity()
        Neo4jSchema.ensure(self.driver)

    def ingest_doc(self, doc: Document, filename: str):
        buffer = self.Buffer()
        document_id = self.__make_document_id(filename)
        for chunk in self.chunker(doc):
            chunk_id = self.__make_chunk_id(document_id, chunk.chunk_index)
            embedding = self.embedding_model.encode(
                chunk.text,
                normalize_embeddings=True
            ).tolist()
            buffer.chunk.append(self.__prepare_chunk(
                document_id, chunk_id, embedding, chunk
            ))
            extraction = self.extractor.extract(chunk.text)
            buffer.entity.extend(
                self.__prepare_entity(chunk_id, extraction)
            )
            buffer.relationship.extend(
                self.__prepare_relationship(chunk_id, extraction)
            )
            if buffer.ready():
                self._save_chunks(buffer.chunk)
                self._save_entities(buffer.entity)
                self._save_relationships(buffer.relationship)
                buffer.clear()
        if buffer.chunk:
            self._save_chunks(buffer.chunk)
        if buffer.entity:
            self._save_entities(buffer.entity)
        if buffer.relationship:
            self._save_relationships(buffer.relationship)

    def _save_chunks(self, rows: list[dict]):
        self.driver.execute_query(
            """
            UNWIND $chunks AS chunk

            MERGE (d:Document {id: chunk.document_id})

            MERGE (c:Chunk {id: chunk.chunk_id})
            SET c.text = chunk.text,
                c.chunk_index = chunk.chunk_index,
                c.page_start = chunk.page_start,
                c.page_end = chunk.page_end,
                c.section = chunk.section,
                c.embedding = chunk.embedding

            MERGE (d)-[:CONTAINS]->(c)
            """,
            chunks=rows,
            database_=self.database
        )

    def _save_entities(self, entities: list[dict]):
        self.driver.execute_query(
            """
            UNWIND $entities AS entity

            MATCH (c:Chunk {id: entity.chunk_id})

            CALL apoc.merge.node(
                [entity.type],
                {id: entity.entity_id},
                {name: entity.name},
                {}
            ) YIELD node AS e

            MERGE (c)-[:MENTIONS]->(e)
            """,
            entities=entities,
            database_=self.database
        )
        '''
        entity doesn't exist
            ↓
        create entity + name

        entity already exists
            ↓
        don't change name
        '''

    def _save_relationships(
        self,
        relationships: list[dict],
    ):
        self.driver.execute_query(
            """
            UNWIND $relationships AS rel

            MATCH (source {id: rel.source_id})
            MATCH (target {id: rel.target_id})

            CALL apoc.merge.relationship(
                source,
                rel.type,
                {},
                {
                    source_chunk_id: rel.chunk_id,
                    evidence: rel.evidence,
                    confidence: rel.confidence
                },
                target,
                {}
            ) YIELD rel AS relationship

            RETURN count(relationship) AS count
            """,
            relationships=relationships,
            database_=self.database
        )

    def __prepare_chunk(
            self, document_id: str, chunk_id: str, 
            embedding: list, chunk_data: ChunkData
    ):
        return {
            "document_id": document_id,
            "chunk_id": chunk_id,
            "text": chunk_data.text,
            "chunk_index": chunk_data.chunk_index,
            "page_start": chunk_data.page_start,
            "page_end": chunk_data.page_end,
            "section": chunk_data.section,
            "embedding": embedding
        }

    def __prepare_entity(
            self, chunk_id: str, relationship_data: GraphExtraction
    ):
        return [
        {
            "chunk_id": chunk_id,
            "entity_id": self.__make_entity_id(
                entity.type,
                entity.name,
            ),
            "name": entity.name,
            "type": entity.type,
        }
        for entity in relationship_data.entities
        ]

    def __prepare_relationship(
            self, chunk_id: str, relationship_data: GraphExtraction
    ):
        return [
            {
                "chunk_id": chunk_id,
                "source_id": self.__make_entity_id(
                    rel.source_type,
                    rel.source,
                ),
                "target_id": self.__make_entity_id(
                    rel.target_type,
                    rel.target,
                ),
                "source_type": rel.source_type,
                "target_type": rel.target_type,
                "type": rel.type,
                "evidence": rel.evidence_text,
                "confidence": rel.confidence,
            }
            for rel in relationship_data.relationships
        ]

    def __make_entity_id(self, entity_type: str, name: str) -> str:
        return f"{entity_type}:{name.strip().lower()}"

    def __make_chunk_id(self, document_id: str, chunk_index: int):
        return f"{document_id}:{chunk_index}"

    def __make_document_id(self, filename: str):
        name = Path(filename).stem
        return f"{name}_{uuid.uuid4()}"

'''
apoc.merge.node(
    labels,
    identProps,
    onCreateProps,
    onMatchProps
)

CALL apoc.merge.relationship(
    startNode,
    relationshipType,
    identProps,
    onCreateProps,
    endNode,
    onMatchProps
)
YIELD rel

apoc.merge.relationship(
    WHO ─────────────── starts the relationship,
    WHAT ────────────── relationship type,
    HOW TO IDENTIFY ── this relationship,
    ON CREATE ──────── properties to set when new,
    WHO ─────────────── ends the relationship,
    ON MATCH ────────── properties to set when already exists
)

CALL apoc.merge.relationship(
    source,
    rel.type,
    {},
    {
        source_chunk_id: rel.chunk_id,
        evidence: rel.evidence,
        confidence: rel.confidence
    },
    target,
    {}
) YIELD rel AS relationship
For each extracted relationship, find the source and target entities. 
If that relationship doesn't exist, create it and attach the evidence/confidence. 
If it already exists, leave it alone.
'''

'''

query_embedding = model.encode(
    "How does Neo4j store graph data?"
).tolist()

records, _, _ = driver.execute_query(
    """
    CALL db.index.vector.queryNodes(
        'chunk_embedding_index',
        5,
        $embedding
    )
    YIELD node, score

    RETURN node.id AS chunk_id,
           node.text AS text,
           score
    ORDER BY score DESC
    """,
    embedding=query_embedding,
)

'''