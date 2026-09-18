from typing import Any

from pydantic import BaseModel
from sqlalchemy.types import JSON, TypeDecorator


class PydanticJSON(TypeDecorator):
    '''
    An adapter between Pydantic and SQLAlchemy's JSON type
    '''
    impl = JSON
    cache_ok = True

    def __init__(self, model_type: type[BaseModel]):
        super().__init__()
        self.model_type = model_type

    def process_bind_param(
        self,
        value: BaseModel | None,
        dialect: Any,
    ):
        if value is None:
            return None

        if not isinstance(value, self.model_type):
            raise TypeError(
                f"Expected {self.model_type.__name__}, "
                f"got {type(value).__name__}"
            )

        return value.model_dump(mode="json")

    def process_result_value(
        self,
        value: Any,
        dialect: Any,
    ):
        if value is None:
            return None

        return self.model_type.model_validate(value)
