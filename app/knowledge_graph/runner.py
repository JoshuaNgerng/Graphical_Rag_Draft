from pymupdf import Document
from typing import Any, Callable, TypeVar
from itertools import islice

from sqlalchemy.orm import Session
from app.knowledge_graph.models.processing_chunk import ChunkDataExtraction
from app.models.data_processing import Chunk 
from app.models.documents import Chunk as DocChunk
from app.knowledge_graph.context_manager import DataProcessingContext
from app.knowledge_graph.pdf_chunker.chunker import PdfChunker
from app.knowledge_graph.phase1.runner import run_phase1
from app.knowledge_graph.phase2.runner import run_phase2
from app.knowledge_graph.phase3.runner import run_phase3
from app.knowledge_graph.checkpoint import (
    upsert_chunk, insert_new_job_task, 
    save_checkpoint_data, get_checkpoint_data
)
from app.core.logging import logger

def processing_pdf(
        doc: Document, 
        job_id: str, doc_id: str, ctx: DataProcessingContext
    ):
    with ctx.db.session() as session:
        insert_new_job_task(job_id, doc_id, session)
        chunks = extract_chunks(doc, job_id, doc_id, session)

    for d in iterator_chunks(chunks, 5):
        loop_processing_functions(
            job_id, d, ctx,
            [run_phase1_wrapper, run_phase2, run_phase3]
        )


def resume_failed_task(job_id: str, ctx: DataProcessingContext):
    with ctx.db.session() as session:
        saved_data = get_checkpoint_data(job_id, session)

    for d in iterator_chunks(saved_data, 5):
        loop_processing_functions(
            job_id, d, ctx,
            [check_extraction_status, run_phase2, run_phase3]
        )


def loop_processing_functions(
        job_id: str, initial_data: list[ChunkDataExtraction], ctx: DataProcessingContext,
        processing_funcs: list[Callable[[list[ChunkDataExtraction], DataProcessingContext], list[ChunkDataExtraction]]]
):
    try:
        data = initial_data
        for func in processing_funcs:
            data = func(data, ctx)
            save_checkpoint(job_id, data, ctx)
    except Exception as e:
        logger.error(f'Job task {job_id} failed: {e}')

def extract_chunks(
        doc: Document, 
        job_id: str, doc_id: str,
        session: Session 
):
    chunker = PdfChunker()
    buffer : list[ChunkDataExtraction] = []
    for chunks in chunker.bulk_chunk_doc(doc, doc_id):
        for c in chunks:
            check = upsert_chunk(job_id, c, session, False)
            if not check: continue
            buffer.append(
                ChunkDataExtraction(chunk_info=DocChunk.model_validate(c))
            )
    return buffer

def check_extraction_status(
        data: list[ChunkDataExtraction], ctx: DataProcessingContext
):
    extracted: list[ChunkDataExtraction] = []
    unresolved: list[Chunk] = []
    for d in data:
        if d.extracted:
            extracted.append(d)
        else:
            unresolved.append(Chunk.from_data(d))
    extracted_data = run_phase1(unresolved, ctx)
    extracted.extend(extracted_data)
    return extracted

def save_checkpoint(
        job_id: str, data: list[ChunkDataExtraction], ctx: DataProcessingContext
):
    with ctx.db.session() as session:
        for d in data:
            save_checkpoint_data(job_id, d, session)

def run_phase1_wrapper(
        data: list[ChunkDataExtraction], ctx: DataProcessingContext
):
    buffer = [d.chunk_info for d in data]
    return run_phase1(buffer, ctx)

T = TypeVar('T')

def iterator_chunks(chunks: list[T], size: int):
    while batch := list(islice(chunks, size)):
        yield batch

# refractor phases into class and init into a loop