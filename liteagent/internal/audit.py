import functools
import functools
import inspect
import time
import traceback
from typing import Callable, Optional, Any, Dict

import structlog


def audit[T](
    log_exceptions: bool = True,
    log_timing: bool = True,
    logger: Optional[structlog.BoundLogger] = None,
    reraise: bool = True,
    extra_context: Optional[Dict[str, Any]] = None
):
    """
    A decorator that audits function calls by logging exceptions and timing information
    using structlog for structured logging.

    This decorator doesn't change the output of the wrapped function but provides
    monitoring capabilities with structured logs.

    Args:
        log_exceptions: Whether to log exceptions
        log_timing: Whether to log timing information
        logger: Custom structlog logger to use (creates one based on function name if None)
        reraise: Whether to reraise exceptions after logging them
        extra_context: Additional context to include in all log entries

    Returns:
        A decorator that wraps functions for auditing
    """

    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        nonlocal logger, extra_context

        if logger is None:
            logger = structlog.get_logger(f"{func.__module__}.{func.__qualname__}")

        if extra_context is None:
            extra_context = {}

        # Add function information to context
        context = {
            "function": func.__qualname__,
            "module": func.__module__,
            **extra_context
        }

        bound_logger = logger.bind(**context)

        @functools.wraps(func)
        async def async_wrapper(*args: Any, **kwargs: Any) -> T:
            start_time = time.time()
            try:
                result = await func(*args, **kwargs)
                if log_timing:
                    elapsed = time.time() - start_time
                    bound_logger.info("function_completed",
                                      elapsed_seconds=elapsed,
                                      success=True)
                return result
            except Exception as e:
                if log_exceptions:
                    elapsed = time.time() - start_time
                    bound_logger.error("function_exception",
                                       elapsed_seconds=elapsed,
                                       exc_info=True,
                                       exception_type=type(e).__name__,
                                       exception=str(e),
                                       traceback=traceback.format_exc())
                if reraise:
                    raise
                return None  # type: ignore

        @functools.wraps(func)
        def sync_wrapper(*args: Any, **kwargs: Any) -> T:
            start_time = time.time()
            try:
                result = func(*args, **kwargs)
                if log_timing:
                    elapsed = time.time() - start_time
                    bound_logger.info("function_completed",
                                      elapsed_seconds=elapsed,
                                      success=True)
                return result
            except Exception as e:
                if log_exceptions:
                    elapsed = time.time() - start_time
                    bound_logger.error("function_exception",
                                       elapsed_seconds=elapsed,
                                       exc_info=True,
                                       exception_type=type(e).__name__,
                                       exception=str(e),
                                       traceback=traceback.format_exc())
                if reraise:
                    raise
                return None  # type: ignore

        if inspect.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper

    return decorator
