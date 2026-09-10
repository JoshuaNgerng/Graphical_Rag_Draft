from io import BytesIO

from app.core.config import get_config
from app.core.celery import create_celery_app
from app.storage.LocalStorage import get_local_storage
from app.knowledge_graph.context_manager import DataProcessingContext
from app.knowledge_graph.runner import processing_pdf

import pymupdf as fitz

celery_app = create_celery_app(get_config())

@celery_app.task
def ingest_pdf_doc(file_key: str):
    config = get_config()
    file_manaager = get_local_storage()
    file_bytes = file_manaager.download_file(file_key)
    with fitz.open(stream=BytesIO(file_bytes), filetype="pdf") as doc:
        with DataProcessingContext(config) as ctx:
            processing_pdf(doc, ctx)            
