from pydantic import BaseModel

from app.core.config import Config
from app.llm_service.llm_base import LLM_BASE, T

from google.genai import types
from google import genai

class Gemini_LLM(LLM_BASE):
    def __init__(self, config: Config) -> None:
        self.API_KEY = config.GEMINI_API_KEY
        self.TEMPERATURE = config.GEMINI_TEMPERATURE
        self.MODEL_NAME = config.GEMINI_MODEL_NAME
        self.client = genai.Client(api_key=self.API_KEY)

    def process(self, input: str, context: str, schema: type[T] = str) -> T:
        config = self.__get_config(schema, context)
        chat = self.client.chats.create(
            model=self.MODEL_NAME,
            config=config
        )
        response = chat.send_message(input)
        text = response.text
        if not text: return schema()
        if issubclass(schema, BaseModel):
            return schema.model_validate_json(text)
        return text # type: ignore

    def close(self):
        self.client.close()

    def __get_config(self, schema: type[T], context: str):
        return types.GenerateContentConfig(
            response_mime_type="application/json",
            response_schema=schema if issubclass(schema, BaseModel) else None,
            system_instruction=context,
            temperature=self.TEMPERATURE,
        )