from typing import Sequence

from app.knowledge_graph.models.processing_chunk import (
    ChunkDataExtraction, EntityExtraction, RelationshipExtraction
)

from app.knowledge_graph.context_manager import DataProcessingContext
from app.models.documents import Chunk as DocChunk
from app.models.data_processing import Chunk

def run_phase1(
        data: Sequence[Chunk | DocChunk], ctx: DataProcessingContext
) -> list[ChunkDataExtraction]:
    res = []
    buffer = []
    for d in data:
        extracted = ctx.extractor.extract(d.text)
        c = d if isinstance(d, DocChunk) else DocChunk.model_validate(d)
        buffer.append(c)
        res.append(
            ChunkDataExtraction(
                chunk_info=c,
                extracted=True,
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
    ctx.driver.save_chunks(buffer)
    return res

# with ctx.db.session() as session: