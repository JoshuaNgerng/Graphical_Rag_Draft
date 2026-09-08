from pydantic import BaseModel, Field

class SaveFailure(BaseModel):
    id: str
    reason: str


class SaveResult(BaseModel):
    total: int
    passed: int
    failed: int
    failures: list[SaveFailure] = Field(
        default_factory=list
    )