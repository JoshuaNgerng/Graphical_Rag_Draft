from pydantic import BaseModel, Field 
from app.models.pagination import PaginationRequest

class EntityListingRequest(PaginationRequest):
    entity_type: str
    search: str | None = Field(default=None)

class EntityCandidateRequest(BaseModel):
    name: str
    type: str
    description: str | None = Field(default=None)
    context: str | None = Field(default=None)
    limit: int = Field(default=10, ge=1, le=50)