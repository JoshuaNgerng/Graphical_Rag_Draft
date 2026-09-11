import datetime
from fastapi import APIRouter, Depends
from app.core.dependencies import get_driver
from app.neo4j.driver import Neo4jDriver
from app.models.pagination import PaginationRequest
from app.schema.response.entity import EntityListingResponse

router = APIRouter()

@router.get('/')
def get_entities(
    type: str,
    search: str | None = None,
    page: int = 1,
    page_size: int = 25,
    driver: Neo4jDriver = Depends(get_driver)
):
    pagenation = PaginationRequest(
        page=page, page_size=page_size
    )
    result = driver.get_entities_listing(type, pagenation, search=search)
    return EntityListingResponse.model_validate(result)

@router.get('/candidates')
def search_entity_detail(driver: Neo4jDriver = Depends(get_driver)):
    pass

@router.get('/{entity_id}')
def get_entity_detail(driver: Neo4jDriver = Depends(get_driver)):
    pass

@router.get('/{entity_id}/relationships')
def get_entity_relationships(driver: Neo4jDriver = Depends(get_driver)):
    pass

@router.get('/{entity_id}/graph')
def graph_entity_detail(driver: Neo4jDriver = Depends(get_driver)):
    pass

@router.get('/{entity_id}/context')
def get_entity_context(driver: Neo4jDriver = Depends(get_driver)):
    pass
