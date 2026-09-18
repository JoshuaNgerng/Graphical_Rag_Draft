import datetime
from uuid import uuid7
from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.api import router
from app.core.dependencies import get_db_session
from app.models.data_processing import JobTask
from app.schema.response.task import JobInfo
from app.tasks.doc_ingestion import rerun_ingest_pdf_doc

router = APIRouter()

@router.get('/')
async def get_job_list(session: Session = Depends(get_db_session)):
    job_ids = session.scalars(select(JobTask.job_id))
    return list(job_ids)

@router.get('/{job_id}')
async def get_job_status(job_id: str, session: Session = Depends(get_db_session)):
    job = session.scalar(
        select(JobTask).where(JobTask.job_id == job_id)
    )
    if not job:
        raise HTTPException(
            status_code=404, 
            detail=f'Job with id: {job_id} not found'
        )
    return f"Job {job_id} exist" # give useful stats later

@router.get('/{job_id}/rerun')
async def rerun_job_status(job_id: str):
    msg = rerun_ingest_pdf_doc.send(job_id)
    type_ = rerun_ingest_pdf_doc.fn.__name__
    return JobInfo(
        job_id=job_id, job_type=type_, 
        message=msg.asdict(), 
        date_queues=datetime.datetime.now()
    )