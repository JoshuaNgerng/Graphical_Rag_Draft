from sqlalchemy import select, delete
from sqlalchemy.orm import Session, selectinload
from app.core.logging import logger
from app.models.data_processing import (
    EntityExtraction, Stats, Chunk, Entities, Relationships, JobTask
)
from app.models.documents import Chunk as DocChunkInfo
from app.knowledge_graph.models.processing_chunk import (
    ChunkDataExtraction,
    RelationshipExtraction
)

def get_checkpoint_data(
        job_id: str, session: Session
) -> list[ChunkDataExtraction]:
    db_data = session.scalar(
        select(JobTask)
        .where(JobTask.job_id == job_id)
        .options(
            selectinload(JobTask.relationships),
            selectinload(JobTask.entities),
            selectinload(JobTask.chunks)
        )
    )
    if not db_data: return []
    res = []
    for chunk in db_data.chunks:
        chunk_info = DocChunkInfo.model_validate(chunk)
        entities = [
            EntityExtraction.model_validate(e)
            for e in db_data.entities
            if e.chunk_pk == chunk.id
        ]
        relationships = [
            RelationshipExtraction.model_validate(r)
            for r in db_data.relationships
            if r.chunk_pk == chunk.id
        ]
        res.append(ChunkDataExtraction(
            chunk_info=chunk_info,
            entities=entities, relationships=relationships
        ))
    return res

def insert_new_job_task(job_id: str, doc_id: str, session: Session):
    job_task = session.scalar(
        select(JobTask).where(JobTask.job_id == job_id)
    )
    if job_task: return job_task
    job_task = JobTask(job_id=job_id, doc_file_key=doc_id)
    session.add(job_task)
    session.commit()
    return job_task

def upsert_chunk(
        job_id: str, chunk: DocChunkInfo, session: Session,
        extracted: bool | None = None
):
    db_job_id = session.scalar(
        select(JobTask.id).where(JobTask.job_id == job_id)
    )
    if not db_job_id:
        return None
    try:
        doc_id = chunk.document_id
        c = session.scalar(
            select(Chunk).where(
                Chunk.doc_id == doc_id,
                Chunk.chunk_id == chunk.chunk_id,
            )
        )

        if c is None:
            c = Chunk.from_data(chunk)
            c.job_id = db_job_id
            c.extracted = bool(extracted)
            session.add(c)

        else:
            c.doc_id = doc_id
            c.text = c.text
            c.chunk_index = c.chunk_index
            c.page_start = c.page_start
            c.page_end = c.page_end
            c.job_id = db_job_id 
            c.extracted = (
                c.extracted if extracted is None else extracted
            )
        session.commit()
        return c
    except Exception as e:
        logger.warning(f"{chunk.chunk_id}, {chunk.chunk_index} can't save: {e}")
        session.rollback()

def save_checkpoint_data(
        job_id: str, data: ChunkDataExtraction, 
        session: Session
):
    db_data = session.scalar(
        select(JobTask)
        .where(JobTask.job_id == job_id)
    )
    if not db_data: return None
    chunk = session.scalar(
        select(Chunk)
        .where(Chunk.chunk_id == data.chunk_info.chunk_id)
    )
    if not chunk: return None
    chunk.extracted = data.extracted
    chunk_id = chunk.id
    session.execute(
        delete(Entities)
        .where(Entities.chunk_pk == chunk_id)
    )
    session.add_all([
        Entities(
            chunk_id=chunk_id, job_id=db_data.id,
            data=e
        ) 
        for e in data.entities
    ])
    session.execute(
        delete(Relationships)
        .where(Relationships.chunk_pk == chunk_id)
    )
    session.add_all([
        Relationships(
            chunk_id=chunk_id, job_id=db_data.id,
            data=r
        ) 
        for r in data.relationships
    ])
    session.commit()
