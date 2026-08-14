from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from neo4j import GraphDatabase
from sentence_transformers import SentenceTransformer

from app.core.config import get_config
from app.core.logging import setup_logging, logger
from app.core.state import get_state
from app.core.celery import create_celery_app
from app.core.redis import close_redis_pool, get_redis_pool, check_redis_connection
from app.api.router import api_router 
from app.neo4j_graphrag.RelationshipExtractorOllama import RelationshipExtractorOllama
from app.neo4j_graphrag.Neo4jSchema import Neo4jSchema
# from app.middleware import LoggingMiddleware, ErrorHandlerMiddleware, DocsSecurityMiddleware

config = get_config()

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Lifespan context manager for FastAPI application.
    Handles startup and shutdown events.
    """
    config = get_config()
    app.state.c
    state =  get_state(config)

    # Startup operations
    logger.info(f"Starting up {config.APP_NAME}")
 
    # Startup Neo4j Driver
    state.transfer(app.state)

    logger.info("Standardizing Schema for Neo4j Driver")
    Neo4jSchema.ensure(driver=app.state.driver)

    # Start Redis pool
    redis_pool = await get_redis_pool()
    if redis_pool:
        logger.info("Redis connection pool initialized")
        
        # Check if Redis server is actually reachable
        redis_ok = await check_redis_connection()
        if not redis_ok:
            logger.warning(
                "Redis is enabled but server is not reachable. "
                "Please check Redis server status and connection settings. "
                "Application will continue running but Redis features will not work."
            )
    else:
        logger.warning("Failed to initialize Redis connection pool")
    app.state.redis_pool = redis_pool

    # Start Celery
    celery_app = create_celery_app(config)
    if celery_app:
        logger.info("Celery application initialized successfully")
    else:
        logger.warning("Failed to initialize Celery application")
        # error
    app.state.celery_app = celery_app

    logger.info("Application initialization completed successfully")
    
    yield
    
    # Shutdown operations

    app.state.driver.close()
    await close_redis_pool()
    
        
    logger.info(f"Shutting down {config.APP_NAME}")


def create_application() -> FastAPI:
    """Create and configure the FastAPI application."""
    # Initialize logging
    app_logger = setup_logging()
    
    app = FastAPI(
        title=config.APP_NAME,
        openapi_url=f"{config.API_PREFIX}/openapi.json",
        docs_url=f"{config.API_PREFIX}/docs",
        redoc_url=f"{config.API_PREFIX}/redoc",
        lifespan=lifespan,
    )
    
    # Add middlewares - order matters!
    
    # # Error handler should be first to catch all exceptions
    # app.add_middleware(ErrorHandlerMiddleware)
    
    # # Protect documentation with authentication
    # app.add_middleware(DocsSecurityMiddleware)
    
    # # Logging middleware
    # app.add_middleware(LoggingMiddleware)
    
    # CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],  # Modify in production to specific origins
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Include API router
    app.include_router(api_router, prefix=config.API_PREFIX)

    @app.get("/health")
    async def health_check():
        """Health check endpoint."""
        app_logger.info("Health check endpoint called")
        return {"status": "healthy"}

    return app


app = create_application()

# Log application startup
logger.info(f"{config.APP_NAME} initialized and ready")
