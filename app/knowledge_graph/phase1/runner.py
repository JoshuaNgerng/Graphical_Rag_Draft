from typing import Sequence

from app.core.config import Config
from app.knowledge_graph.models.processing_chunk import (
    ChunksProcessing, ChunkDataProcess, ChunkData,
    EntityExtraction, RelationshipExtraction
)

from app.knowledge_graph.phase1.extraction import RelationExtractor

def run_phase1(data: Sequence[ChunkData], config: Config):
    r = RelationExtractor(config)
    res = []
    for d in data:
        extracted = r.extract(d.text)
        buffer = ChunkDataProcess(
            chunk_info=d,
            entities=[EntityExtraction(observation=e) for e in extracted.entities],
            relationships=[RelationshipExtraction(observation=r) for r in extracted.relationships]
        )
        res.append(buffer)
    return ChunksProcessing(data=res)