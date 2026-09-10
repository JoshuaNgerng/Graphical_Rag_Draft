from typing import Sequence

from app.knowledge_graph.models.processing_chunk import (
    ChunkDataExtraction, ChunkData,
    EntityExtraction, RelationshipExtraction
)

from app.knowledge_graph.phase1.extraction import RelationExtractor
from app.knowledge_graph.context_manager import DataProcessingContext

def run_phase1(
        data: Sequence[ChunkData], ctx: DataProcessingContext
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
    return res