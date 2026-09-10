from enum import StrEnum, auto
from pydantic import BaseModel, Field, field_validator

class DecisionType(StrEnum):
    MERGE = auto().upper()
    CREATE = auto().upper()
    UNKNOWN = auto().upper()

class ChooseType(StrEnum):
    ACCEPT = auto().upper()
    REJECT = auto().upper()
    UNKNOWN = auto().upper()

class InferenceBase(BaseModel):
    confidence: float = Field(ge=0.0, le=1.0)
    reasoning: str

class Decision(InferenceBase):
    decision: DecisionType

class Choose(InferenceBase):
    choose: ChooseType
