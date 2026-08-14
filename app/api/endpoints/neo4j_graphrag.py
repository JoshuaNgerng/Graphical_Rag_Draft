from fastapi import APIRouter, Depends, File, UploadFile
from neo4j import Driver
from app.dependencies import get_driver
from app.storage.LocalStorage import LocalStorage
from app.neo4j_graphrag.Neo4jQuery import Neo4jQuery
from app.task.doc_ingestion import ingest_pdf_doc
from app.schema.response.task import TaskInfo

router = APIRouter()

@router.post('/add_doc')
async def add_doc(file: UploadFile = File(...)):
    file_manager = LocalStorage()
    file_bytes = await file.read()
    file_key = file_manager.upload_file(file.filename, file_bytes)
    task =  ingest_pdf_doc.delay(file_key) # type: ignore celery is gay
    return TaskInfo(task_id=task.id)

@router.post('/query')
async def query_info(driver: Driver = Depends(get_driver)):
    query = Neo4jQuery(driver)