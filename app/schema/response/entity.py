from pydantic import BaseModel, Field 
from app.models.driver_query_results import PaginationResult
from app.models.entity_relationship import EntityRepr

class EntityListingResponse(PaginationResult[EntityRepr]):
    pass