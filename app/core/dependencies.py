from contextlib import asynccontextmanager
from fastapi import FastAPI, Request

from app.core.config import Config, get_config
from app.core.config import get_config
from app.core.logging import logger
from app.neo4j.driver import Neo4jDriver
from app.neo4j.schema import Neo4jSchema
from app.ollama.embedding import Embedding
from app.storage.MinIOStorage import MinIOStorage
import app.tasks.broker # import to run setup function

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Lifespan context manager for FastAPI application.
    Handles startup and shutdown events.
    """
    config = get_config()

    # Startup operations
    logger.info(f"Starting up {config.APP_NAME}")
    logger.info(f"DEBUG: config:{config.model_dump_json(indent=2)}")
 
    driver = Neo4jDriver(config)

    logger.info("Standardizing Schema for Neo4j Driver")
    Neo4jSchema.ensure(driver=driver.driver)
    logger.info("Finish Neo4j Schema")

    app.state.driver = driver
    app.state.embedding = Embedding(config)
    app.state.storage = MinIOStorage(config)

    logger.info("Application initialization completed successfully")
    
    yield
    
    # Shutdown operations

    app.state.driver.close()
    app.state.embedding.close()
        
    logger.info(f"Shutting down {config.APP_NAME}")

def get_driver(request: Request) -> Neo4jDriver:
    return request.app.state.driver

def get_embedding(request: Request) -> Embedding:
    return request.app.state.embedding

def get_storage(request: Request) -> MinIOStorage:
    return request.app.state.storage

def get_state(request: Request):
    return request.app.state