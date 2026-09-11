import os
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
    OLLAMA_MODEL_NAME: str
    OLLAMA_TEMPERATURE: int
    OLLAMA_EMBEDDING_MODEL: str
    OLLAMA_LOG: bool =  Field(default=False)
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        # extra="ignore",
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

    @field_validator('OLLAMA_LOG')
    @classmethod
    def check_ollama_log(cls, v):
        if isinstance(v, bool):
            return v
        try:
            v = str(v)
        except:
            return False
        return v.lower() in ("true", "1", "t")

@lru_cache
def get_config():
    return Config() # type: ignore

# settings = Settings() # type: ignore
