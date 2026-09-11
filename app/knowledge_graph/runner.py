from pymupdf import Document
from app.knowledge_graph.context_manager import DataProcessingContext
from app.knowledge_graph.pdf_chunker.chunker import PdfChunker
from app.knowledge_graph.phase1.runner import run_phase1
from app.knowledge_graph.phase2.runner import run_phase2
from app.knowledge_graph.phase3.runner import run_phase3
from app.core.logging import logger

def processing_pdf(
        doc: Document, doc_id: str, ctx: DataProcessingContext
    ):
    chunker = PdfChunker()
    logger.info(f'STARTING processing documnet: {doc_id}')
    for chunks in chunker.bulk_chunk_doc(doc, doc_id):
        logger.info(f'STARTING PROCESS NEW CHUNKS')
        phase1 = run_phase1(chunks, ctx)
        logger.info(f'DONE PHASE 1')
        phase2 = run_phase2(phase1, ctx)
        logger.info(f'DONE PHASE 2')
        run_phase3(phase2, ctx)
        logger.info(f'DONE PHASE 3')

# refractor phases into class and init into a loop