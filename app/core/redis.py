import traceback
from typing import Any, Optional, Union, TypeVar
import orjson
import redis.asyncio as redis
from redis.asyncio import Redis, ConnectionPool
from pydantic import BaseModel

from app.core.config import get_config 
from app.core.logging import logger

# Type for any Redis value
T = TypeVar('T')

# Global Redis connection pool
redis_pool: Optional[ConnectionPool] = None


async def get_redis_pool() -> Optional[ConnectionPool]:
    """
    Get or create a Redis connection pool.
    Error return None
    """
    global redis_pool
    config = get_config()

    if redis_pool is None:
        try:
            redis_kwargs = {
                "decode_responses": True,
                "encoding": "utf-8",
                "max_connections": config.REDIS_POOL_SIZE,
                "socket_timeout": config.REDIS_TIMEOUT,
                "socket_connect_timeout": config.REDIS_TIMEOUT,
            }
            
            if config.REDIS_PASSWORD:
                redis_kwargs["password"] = config.REDIS_PASSWORD
                
            redis_pool = ConnectionPool.from_url(
                config.REDIS_URL,
                **redis_kwargs
            )
            logger.info("Redis connection pool created")
        except Exception as e:
            logger.error(f"Failed to create Redis connection pool: {str(e)}")
            return None
            
    return redis_pool


async def get_redis() -> Optional[Redis]:
    """
    Get a Redis client from the connection pool.
    Error return None
    """
        
    pool = await get_redis_pool()
    if pool is None:
        return None
        
    try:
        return redis.Redis(connection_pool=pool)
    except Exception as e:
        logger.error(f"Failed to get Redis client: {str(e)}")
        return None


async def close_redis_pool() -> None:
    """Close the Redis connection pool if it exists."""
    global redis_pool
    
    if redis_pool is not None:
        try:
            await redis_pool.disconnect()
            redis_pool = None
            logger.info("Redis connection pool closed")
        except Exception as e:
            logger.error(f"Error closing Redis connection pool: {str(e)}")


async def set_key(key: str, value: Any, expire_seconds: Optional[int] = None) -> bool:
    """
    Set a key in Redis with optional expiration.
    Returns True if successful, False otherwise.
    """
    redis_client = await get_redis()
    if redis_client is None:
        return False
        
    try:
        # Serialize complex objects
        serialized_value = value
        if isinstance(value, (dict, list, BaseModel)):
            try:
                if isinstance(value, BaseModel):
                    serialized_value = value.model_dump()
                
                # Special handling for dicts/lists that might contain non-serializable objects
                serialized_value = orjson.dumps(serialized_value).decode('utf-8')
            except TypeError as e:
                logger.warning(f"Could not serialize value for key {key}: {str(e)}")
                # Fallback to string representation if serialization fails
                serialized_value = str(value)
        
        # Set the key
        await redis_client.set(key, serialized_value)
        
        # Set expiration if provided
        if expire_seconds is not None:
            await redis_client.expire(key, expire_seconds)
            
        return True
    except Exception as e:
        logger.error(f"Error setting Redis key {key}: {str(e)}")
        return False
    finally:
        if redis_client:
            await redis_client.close()


async def get_key(key: str, default: Optional[T] = None) -> Union[str, bytes, T, None]:
    """
    Get a key from Redis.
    Returns the value if successful, default or None otherwise .
    """
    redis_client = await get_redis()
    if redis_client is None:
        return default
        
    try:
        value = await redis_client.get(key)
        if value is None:
            return default
        
        # Try to parse as JSON if it looks like a dict or list
        if (value.startswith('{') and value.endswith('}')) or (value.startswith('[') and value.endswith(']')): #type: ignore
            try:
                return orjson.loads(value)
            except orjson.JSONDecodeError:
                pass
                
        return value
    except Exception as e:
        logger.error(f"Error getting Redis key {key}: {str(e)}")
        return default
    finally:
        if redis_client:
            await redis_client.close()


async def delete_key(key: str) -> bool:
    """
    Delete a key from Redis.
    Returns True if successful, False otherwise .
    """
    redis_client = await get_redis()
    if redis_client is None:
        return False
        
    try:
        return bool(await redis_client.delete(key))
    except Exception as e:
        logger.error(f"Error deleting Redis key {key}: {str(e)}")
        return False
    finally:
        if redis_client:
            await redis_client.close()


async def has_key(key: str) -> bool:
    """
    Check if a key exists in Redis.
    Returns True if the key exists, False otherwise .
    """
    redis_client = await get_redis()
    if redis_client is None:
        return False
        
    try:
        return bool(await redis_client.exists(key))
    except Exception as e:
        logger.error(f"Error checking Redis key {key}: {str(e)}")
        return False
    finally:
        if redis_client:
            await redis_client.close()
            

async def set_key_ttl(key: str, expire_seconds: int) -> bool:
    """
    Set expiration time (in seconds) for a key.
    Returns True if successful, False otherwise .
    """
    redis_client = await get_redis()
    if redis_client is None:
        return False
        
    try:
        return bool(await redis_client.expire(key, expire_seconds))
    except Exception as e:
        logger.error(f"Error setting TTL for Redis key {key}: {str(e)}")
        return False
    finally:
        if redis_client:
            await redis_client.close()

            
async def increment_key(key: str, amount: int = 1) -> Optional[int]:
    """
    Increment a key in Redis.
    Returns the new value if successful, None otherwise .
    """
    redis_client = await get_redis()
    if redis_client is None:
        return None
        
    try:
        return await redis_client.incr(key, amount)
    except Exception as e:
        logger.error(f"Error incrementing Redis key {key}: {str(e)}")
        return None
    finally:
        if redis_client:
            await redis_client.close()


async def get_ttl(key: str) -> Optional[int]:
    """
    Get the time-to-live for a key in Redis.
    Returns the TTL in seconds if successful, -1 if the key exists but has no expiry,
    -2 if the key doesn't exist, and None if an error occurs.
    """
    redis_client = await get_redis()
    if redis_client is None:
        return None
        
    try:
        return await redis_client.ttl(key)
    except Exception as e:
        logger.error(f"Error getting TTL for Redis key {key}: {str(e)}")
        return None
    finally:
        if redis_client:
            await redis_client.close() 


async def check_redis_connection() -> bool:
    """
    Check if Redis connection can be established.
    Returns True if connection successful, False otherwise.
    """

    redis_client = None 
    try:
        redis_client = await get_redis()
        if redis_client is None:
            logger.error("Failed to get Redis client for connection check")
            return False
            
        # Try a simple PING command to verify connection
        result = await redis_client.ping()
        if result:
            logger.info("Redis connection check succeeded: Redis server is reachable")
            return True
        else:
            logger.error("Redis connection check failed: No response from Redis server")
            return False
    except Exception as e:
        logger.error(f"Redis connection check failed: {str(e)}")
        logger.debug(traceback.format_exc())
        return False
    finally:
        if redis_client:
            await redis_client.close()