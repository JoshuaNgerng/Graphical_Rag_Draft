import datetime
from uuid import uuid7
from fastapi import APIRouter, Depends, File, UploadFile
from app.core.dependencies import get_storage
from app.tasks.doc_ingestion import ingest_pdf_doc
from app.schema.response.task import JobInfo

router = APIRouter()

@router.post('/')
async def add_doc(
    file: UploadFile = File(...),
    storage = Depends(get_storage)
) -> JobInfo:
    file_bytes = await file.read()
    file_key = storage.upload_file(file.filename, file_bytes)
    job_id = str(uuid7())
    message = ingest_pdf_doc.send(job_id, file_key) 
    type_ = ingest_pdf_doc.fn.__name__
    return JobInfo(
        job_id=job_id, job_type=type_,
        message=message.asdict(),
        date_queues=datetime.datetime.now()
    )