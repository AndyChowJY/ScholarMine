"""Retry decorators for async and sync functions."""

import asyncio
import functools
import time
from typing import Callable, TypeVar

from scholar_mine.utils.logger import Logger

T = TypeVar("T")
log = Logger.get()


def retry_sync(max_retries: int = 3, base_delay: float = 1.0,
               backoff: float = 2.0, exceptions=(Exception,)):
    """Synchronous retry decorator with exponential backoff."""
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @functools.wraps(func)
        def wrapper(*args, **kwargs) -> T:
            last_exc = None
            for attempt in range(1, max_retries + 1):
                try:
                    return func(*args, **kwargs)
                except exceptions as e:
                    last_exc = e
                    if attempt == max_retries:
                        log.error(f"{func.__name__} failed after {max_retries} attempts: {e}")
                        raise
                    delay = base_delay * (backoff ** (attempt - 1))
                    log.warning(
                        f"{func.__name__} attempt {attempt}/{max_retries} failed: {e}. "
                        f"Retrying in {delay:.1f}s..."
                    )
                    time.sleep(delay)
            raise last_exc  # type: ignore[misc]
        return wrapper
    return decorator


def retry_async(max_retries: int = 3, base_delay: float = 1.0,
                backoff: float = 2.0, exceptions=(Exception,)):
    """Async retry decorator with exponential backoff."""
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @functools.wraps(func)
        async def wrapper(*args, **kwargs) -> T:
            last_exc = None
            for attempt in range(1, max_retries + 1):
                try:
                    return await func(*args, **kwargs)
                except exceptions as e:
                    last_exc = e
                    if attempt == max_retries:
                        log.error(f"{func.__name__} failed after {max_retries} attempts: {e}")
                        raise
                    delay = base_delay * (backoff ** (attempt - 1))
                    log.warning(
                        f"{func.__name__} attempt {attempt}/{max_retries} failed. "
                        f"Retrying in {delay:.1f}s..."
                    )
                    await asyncio.sleep(delay)
            raise last_exc  # type: ignore[misc]
        return wrapper
    return decorator