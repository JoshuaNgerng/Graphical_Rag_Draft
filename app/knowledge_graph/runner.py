from pymupdf import Document
from app.knowledge_graph.context_manager import DataProcessingContext
from app.knowledge_graph.pdf_chunker.chunker import PdfChunker
from app.knowledge_graph.phase1.runner import run_phase1
from app.knowledge_graph.phase2.runner import run_phase2
from app.knowledge_graph.phase3.runner import run_phase3

def processing_pdf(doc: Document, ctx: DataProcessingContext):
    chunker = PdfChunker()
    for chunks in chunker.bulk_chunk_doc(doc):
        phase1 = run_phase1(chunks, ctx)
        phase2 = run_phase2(phase1, ctx)
        run_phase3(phase2, ctx)

# refractor phases into class and init into a loop