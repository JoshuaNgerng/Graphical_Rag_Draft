from fastapi import APIRouter

from app.api.endpoints.doc_ingestion import router as doc_router
from app.api.endpoints.entities import router as entity_router
from app.api.endpoints.job_task import router as job_router
from app.api.endpoints.admin import router as admin_router

api_router = APIRouter()
api_router.include_router(admin_router, prefix='/admin', tags=["Admin"])
api_router.include_router(doc_router, prefix='/doc', tags=["Document"])
api_router.include_router(entity_router, prefix='/entities', tags=["Entities"])
api_router.include_router(job_router, prefix='/jobs', tags=["JobTasks"])
