from fastapi import APIRouter

from app.api.endpoints.neo4j_graphrag import router as neo4j_router

api_router = APIRouter()
api_router.include_router(neo4j_router, prefix='/neo4j', tags=["Neo4j"])