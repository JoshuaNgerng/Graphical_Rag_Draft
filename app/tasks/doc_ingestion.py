from io import BytesIO

from app.core.config import get_config
from app.files.MinIOManager import MinIOManager
from app.knowledge_graph.context_manager import DataProcessingContext
from app.knowledge_graph.runner import processing_pdf, resume_failed_task

import pymupdf as fitz
import dramatiq

@dramatiq.actor(time_limit=24 * 60 * 60 * 1000)
def ingest_pdf_doc(job_id: str, file_key: str):
    config = get_config()
    storage = MinIOManager(config)
    file_bytes = storage.download_file(file_key)
    with fitz.open(stream=BytesIO(file_bytes), filetype="pdf") as doc:
        with DataProcessingContext(config) as ctx:
            processing_pdf(doc, job_id, file_key, ctx)

@dramatiq.actor(time_limit=24 * 60 * 60 * 1000)
def rerun_ingest_pdf_doc(job_id: str):
    config = get_config()
    with DataProcessingContext(config) as ctx:
        resume_failed_task(job_id, ctx)


'''
move to store info in postgres example
jobs
────────────────────────────────────
id                  job_123
file_key            uploads/a.pdf
broker_message_id   8c91...
status              processing
total_chunks        120
completed_chunks    73
failed_chunks       1
created_at          ...
completed_at        NULL

'''