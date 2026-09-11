from pydantic import BaseModel
from typing import Generic, TypeVar

class PaginationRequest(BaseModel):
    page: int
    page_size: int


class PaginationInfo(PaginationRequest):
    total: int
    total_pages: int
