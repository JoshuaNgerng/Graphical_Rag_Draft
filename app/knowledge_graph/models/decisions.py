from enum import StrEnum, auto
from pydantic import BaseModel, Field, field_validator

class EnumUpperStr(StrEnum):
    def __new__(cls, value: str):
        obj = str.__new__(cls, value)
        obj._value_ = value
        return obj

    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)

        for member_name, member in cls.__members__.items():
            member._value_ = member_name.upper()

class DecisionType(EnumUpperStr):
    MERGE = auto()
    CREATE = auto()
    UNKNOWN = auto()

class ChooseType(EnumUpperStr):
    ACCEPT = auto()
    REJECT = auto()
    UNKNOWN = auto()

class InferenceBase(BaseModel):
    confidence: float = Field(ge=0.0, le=1.0)
    reasoning: str

class Decision(InferenceBase):
    decision: DecisionType

class Choose(InferenceBase):
    choose: ChooseType
