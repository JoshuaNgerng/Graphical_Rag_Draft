from typing import Sequence

from app.knowledge_graph.models.processing_chunk import (
    ChunkDataExtraction, EntityExtraction, RelationshipExtraction
)

from app.knowledge_graph.context_manager import DataProcessingContext
from app.models.documents import Chunk

def run_phase1(
        data: Sequence[Chunk], ctx: DataProcessingContext
) -> list[ChunkDataExtraction]:
    res = []
    for d in data:
        extracted = ctx.extractor.extract(d.text)
        res.append(
            ChunkDataExtraction(
                chunk_info=d,
                context_embedding=list(ctx.embedding.encode(d.text)),
                entities=[
                    EntityExtraction(observation=e) 
                    for e in extracted.entities
                ],
                relationships=[
                    RelationshipExtraction(observation=r)
                    for r in extracted.relationships
                ]
            )
        )
    ctx.driver.save_chunks(list(data))
    return res