from io import BytesIO

from app.core.config import get_config
from app.core.celery import create_celery_app
from app.core.state import get_state
from app.storage.LocalStorage import get_local_storage
from app.neo4j_graphrag.Neo4jIngestor import get_neo4j_ingestor

import pymupdf as fitz

celery_app = create_celery_app(get_config())

@celery_app.task
def ingest_pdf_doc(file_key: str):
    file_manaager = get_local_storage()
    file_bytes = file_manaager.download_file(file_key)
    doc = fitz.open(stream=BytesIO(file_bytes), filetype="pdf")
    try:
        state = get_state(get_config())
        ingestor = get_neo4j_ingestor(state)
        ingestor.ingest_doc(doc, file_key)
    finally:
        doc.close()
