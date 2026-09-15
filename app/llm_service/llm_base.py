from typing import Protocol, TypeVar

from pydantic import BaseModel

from app.core.config import Config
from app.core.logging import logger

T = TypeVar("T", bound=BaseModel | str)

class LLM_BASE(Protocol):
    def __init__(self, config: Config) -> None: ...
    def process(
        self, input: str, context: str, 
        schema: type[T] = str
    ) -> T: ...
