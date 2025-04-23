import asyncio
import functools
import inspect


def depends_on(modules: dict, message: str = None):
    def decorator(fn):
        def evaluate():
            missing = []

            for module, package in modules.items():
                try:
                    __import__(module)
                except ImportError:
                    missing.append(package)

            if missing:
                ImportError(
                    message or f"""
                        It appears that the packages {', '.join(missing)} are not installed.
                        In order to use this feature, please install them with: `pip install {' '.join(missing)}`
                    """.strip()
                )

        @functools.wraps(fn)
        async def async_wrapper(*args, **kwargs):
            await asyncio.to_thread(evaluate)
            return await fn(*args, **kwargs)

        @functools.wraps(fn)
        def sync_wrapper(*args, **kwargs):
            evaluate()
            return fn(*args, **kwargs)

        return async_wrapper if inspect.iscoroutinefunction(fn) else sync_wrapper

    return decorator
