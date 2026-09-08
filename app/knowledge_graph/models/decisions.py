from enum import StrEnum, auto
from pydantic import BaseModel, Field, field_validator

class DecisionType(StrEnum):
    MERGE = auto().upper()
    CREATE = auto().upper()
    UNKNOWN = auto().upper()

class Decision(BaseModel):
    decision: DecisionType
    confidence: float = Field(ge=0.0, le=1.0)
    reasoning: str
