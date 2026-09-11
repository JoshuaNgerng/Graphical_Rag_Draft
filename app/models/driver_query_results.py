from typing import Generic, TypeVar
from pydantic import BaseModel, Field
from app.models.pagination import PaginationInfo

# class SaveFailure(BaseModel):
#     id: str
#     reason: str

class SaveResult(BaseModel):
    total: int
    passed: int
    failed: int
    failed_ids: list[str] = Field(
        default_factory=list
    )

T = TypeVar("T", bound=BaseModel)

class DataResult(BaseModel, Generic[T]):
    score: float
    data: T

class PaginationResult(PaginationInfo, Generic[T]):
    data: list[T]
