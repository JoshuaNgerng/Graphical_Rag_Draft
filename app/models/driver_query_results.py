from typing import Generic, TypeVar
from pydantic import BaseModel, Field

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

    def gather_data(self):
        return [d for d in self.data]