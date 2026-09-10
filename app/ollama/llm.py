from ollama import Client

from typing import TypeVar

from pydantic import BaseModel

from app.core.config import Config

T = TypeVar("T", bound=BaseModel | str)

class LLM:
    def __init__(self, config: Config) -> None:
        self.model = config.OLLAMA_MODEL_NAME
        self.options = {
            "temperature": config.OLLAMA_TEMPERATURE #0
        }
        self.client = Client(config.OLLAMA_URL) 

    def process(
            self, input: str, context: str, 
            schema: type[T] = str
        ) -> T:
        format = schema.model_json_schema() if issubclass(schema, BaseModel) else None
        response = self.client.chat(
            model=self.model, 
            messages=[
                {
                    "role": "system",
                    "content": context
                },
                {
                    "role": "user",
                    "content": input,
                }
            ],
            format=format,
            options=self.options
        )
        data = response.message.content
        if data is None:
            return schema()
        if issubclass(schema, BaseModel):
            return schema.model_validate_json(data)
        return data # type: ignore

    def close(self):
        self.client.close()