import os
from re import S
from typing import Optional
from pydantic import field_validator
from pydantic_settings import BaseSettings
from sympy.abc import s
from wrapt import lru_cache

class Config(BaseSettings):
    """Application settings."""
    
    # Application info
    APP_NAME: str = "Neo4j GraphRAG App"
    API_PREFIX: str = "/api"
    DEBUG: bool = os.getenv("DEBUG", "False").lower() in ("true", "1", "t")
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")

    # Celery and Redis
    REDIS_URL: str
    REDIS_PASSWORD: str
    REDIS_POOL_SIZE: str
    REDIS_TIMEOUT: str
    REDIS_DB: str
    REDIS_PORT: str
    REDIS_HOST: str
    
    
    # Neo4j settings
    DRIVER_URL: str
    DRIVER_PASSWORD: str
    DRIVER_DATABASE: str

    # Embedding Model
    EMBEDDING_MODEL_NAME: str

    # Ollama
    OLLAMA_MODEL_NAME: str
    OLLAMA_TEMPERATURE: int

    class Config:
        env_file = ".env"
        case_sensitive = True

    @field_validator('LOG_LEVEL')
    @classmethod
    def validate_log_level(cls, v):
        v = str(v).upper()
        if v not in { 
            "TRACE", "DEBUG", "INFO", "SUCCESS", 
            "WARNING", "ERROR", "CRITICAL" 
        }: return "INFO"
        return v

@lru_cache
def get_config():
    return Config() # type: ignore

# settings = Settings() # type: ignore
