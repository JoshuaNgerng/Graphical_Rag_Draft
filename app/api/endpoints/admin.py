import datetime
from uuid import uuid7
from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.api import router
from app.core.dependencies import get_db
from app.models.db_base import Base
from app.postgres.session import Postgres

router = APIRouter()

@router.get('/db-init')
async def init_db_schema(db: Postgres = Depends(get_db)):
    if db.engine:
        Base.metadata.create_all(db.engine)