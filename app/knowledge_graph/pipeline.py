from pymupdf import Document

from app.models.documents import ChunkData
from app.knowledge_graph.phase1.extraction import RelationExtractor
from app.knowledge_graph.phase1.data import Phase1Summary
from app.knowledge_graph.pdf_chunker.chunker import chunk_doc

class Pipeline:
    def __init__(self, extractor: RelationExtractor) -> None:
        self.extractor = extractor

    def process_document(self, doc: Document):
        phase1 = []
        for chunk in chunk_doc(doc):
            observation = self.extractor.extract(chunk.text)
            phase1.append(
                Phase1Summary(
                    chunk=ChunkData.model_validate(chunk), 
                    observations=observation
                )
            )
            