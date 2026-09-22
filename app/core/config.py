import os
from typing import Any
from pydantic import field_validator, Field
from pydantic_settings import BaseSettings, SettingsConfigDict
from functools import lru_cache

class Config(BaseSettings):
    """Application settings."""
    
    # Application info
    APP_NAME: str = "Neo4j GraphRAG App"
    API_PREFIX: str = "/api"
    DEBUG: bool = os.getenv("DEBUG", "False").lower() in ("true", "1", "t")
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")

    # storage (if local)
    STORAGE_ROOT_DIR: str | None = Field(default=None)

    # minio
    MINIO_ENDPOINT: str
    MINIO_BUCKET: str
    MINIO_REGION: str = "us-east-1"
    MINIO_ROOT_USER: str
    MINIO_ROOT_PASSWORD: str

    # Dramatiq and RabbitMQ
    RABBITMQ_HOST: str = Field(default="localhost")
    RABBITMQ_PORT: int = Field(default=5672)
    
    # Neo4j settings
    DRIVER_URL: str
    DRIVER_PASSWORD: str
    DRIVER_DATABASE: str

    # Ollama
    OLLAMA_URL: str
    OLLAMA_EMBEDDING_MODEL: str
    OLLAMA_MODEL_NAME: str | None = Field(default=None)
    OLLAMA_TEMPERATURE: int = Field(default=0)
    OLLAMA_LOG: bool =  Field(default=False)
    OLLAMA_CONTEXT_WINDOW: int = Field(default=4096)

    GEMINI_API_KEY: str | None = Field(default=None)
    GEMINI_MODEL_NAME: str | None = Field(default=None)
    GEMINI_TEMPERATURE: int = Field(default=0)
    GEMINI_CONTEXT_WINDOW: int = Field(default=4096)
    GEMINI_LOG: bool = Field(default=False)

    POSTGRES_USER: str
    POSTGRES_PASSWORD: str
    POSTGRES_DB: str
    POSTGRES_HOST: str
    POSTGRES_PORT: int
    POSTGRES_ECHO_LOG: bool = Field(default=False)
    POSTGRES_POOL_SIZE: int = Field(default=5)
    POSTGRES_MAX_OVERFLOW: int = Field(default=10)
    POSTGRES_POOL_TIMEOUT: int = Field(default=30)
    POSTGRES_POOL_RECYCLE: int = Field(default=1800)
    POSTGRES_POOL_PRE_PING: bool = Field(default=True)
    POSTGRES_CONNECT_TIMEOUT: int = Field(default=10)
    POSTGRES_COMMAND_TIMEOUT: int = Field(default=30)

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    @field_validator('LOG_LEVEL')
    @classmethod
    def validate_log_level(cls, v):
        v = str(v).upper()
        if v not in { 
            "TRACE", "DEBUG", "INFO", "SUCCESS", 
            "WARNING", "ERROR", "CRITICAL" 
        }: return "INFO"
        return v

    @field_validator('GEMINI_LOG')
    @classmethod
    def check_log(cls, v):
        _validate_bool(v)

    @field_validator('POSTGRES_ECHO_LOG')
    @classmethod
    def check_echo_log(cls, v):
        _validate_bool(v)

    @field_validator('POSTGRES_POOL_PRE_PING')
    @classmethod
    def check_pool_pre_ping(cls, v):
        _validate_bool(v)


@lru_cache
def get_config():
    return Config() # type: ignore

def _validate_bool(v: Any) -> bool:
    if isinstance(v, bool):
        return v
    try:
        v = str(v)
    except:
        return False
    return v.lower() in ("true", "1", "t")


# settings = Settings() # type: ignore
