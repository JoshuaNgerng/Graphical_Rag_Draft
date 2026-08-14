from typing import Dict, Any, Optional
from functools import lru_cache
from celery import Celery

from app.core.config import Config, get_config
from app.core.logging import logger

# Global Celery app instance
celery_app: Optional[Celery] = None

def get_celery_config(config: Config) -> Dict[str, Any]:
    """
    Get Celery configuration options based on application config.
    
    Returns:
        Dictionary of Celery configuration options
    """
    
    # Build broker URL from Redis config
    broker_url = config.REDIS_URL
    
    # Set up result backend - also using Redis
    result_backend = config.REDIS_URL
    
    # Configure Celery
    config_celery = {
        "broker_url": broker_url,
        "result_backend": result_backend,
        "broker_connection_retry_on_startup": True,
        "task_serializer": "json",
        "accept_content": ["json"],
        "result_serializer": "json",
        "enable_utc": True,
        "task_track_started": True,
        "task_time_limit": 30 * 60,  # 30 minutes
        "worker_max_tasks_per_child": 1000,
        "task_default_queue": "celery",
        "worker_prefetch_multiplier": 2, # lower it so dont load too much memory in advance
    }
    
    # Add Redis password if configured
    if config.REDIS_PASSWORD:
        if "redis://" in broker_url:
            # If using Redis protocol, update the URLs with password
            password_part = f":{config.REDIS_PASSWORD}@"
            if "@" in broker_url:
                # Replace existing auth info
                config_celery["broker_url"] = broker_url.replace("@", password_part)
                config_celery["result_backend"] = result_backend.replace("@", password_part)
            else:
                # Add auth info after protocol and before host
                parts = broker_url.split("://")
                if len(parts) == 2:
                    config_celery["broker_url"] = f"{parts[0]}://{password_part}{parts[1]}"
                    config_celery["result_backend"] = f"{parts[0]}://{password_part}{parts[1]}"
    
    return config_celery


def create_celery_app(config: Config) -> Celery:
    """
    Create and configure the Celery application.
    Returns None on error 
    
    Returns:
        Configured Celery application instance or None
    """
    global celery_app

    if celery_app is not None: return celery_app
    
    try:
        config_celery = get_celery_config(config)
        if not config:
            raise RuntimeError("Config Celery App failed")
            
        # Create Celery app
        celery_instance = Celery(config.APP_NAME)
        
        # Update configuration
        celery_instance.conf.update(config_celery)
        
        # Auto-discover tasks
        celery_instance.autodiscover_tasks(
            ["app.tasks"], 
            related_name=None, # type: ignore
            force=True
        )
        
        celery_app = celery_instance
        
        logger.info("Celery application initialized successfully")

        return celery_instance

    except Exception as e:
        logger.error(f"Failed to initialize Celery: {str(e)}")
        raise e


def get_celery_app() -> Celery:
    """
    Get the Celery application instance.
    Raise RuntimeError if it doesn't exist yet.
    
    Returns:
        Celery application instance or None 
    """
    global celery_app

    if celery_app is None:
        raise RuntimeError("Cannot Init Celery")

    return celery_app 

create_celery_app(get_config())
