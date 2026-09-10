from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import get_config
from app.core.logging import setup_logging, logger
from app.core.dependencies import lifespan
from app.api.router import api_router 
# from app.middleware import LoggingMiddleware, ErrorHandlerMiddleware, DocsSecurityMiddleware

config = get_config()

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
