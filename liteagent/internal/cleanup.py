import atexit
import asyncio
import signal
import sys
from datetime import datetime
from typing import List, Any, TYPE_CHECKING

if TYPE_CHECKING:
    pass
else:
    # Forward declaration just for type hints
    Provider = Any

_registered_providers: List[Any] = []
_cleanup_running = False

def register_provider(func_or_provider=None):
    """
    Decorator that registers providers for automatic cleanup at program exit.
    
    Can be used in three ways:
    
    1. As a function decorator for provider factory functions:
    @register_provider
    def create_provider(...) -> Provider:
        return Provider(...)
    
    2. As a class decorator:
    @register_provider
    class MyProvider(Provider):
        ...
    
    3. As a function to register an instance:
    my_provider = Provider()
    register_provider(my_provider)
    """

    start = datetime.now()

    def _register_instance(provider):
        if provider not in _registered_providers:
            # print(f"Registering provider for cleanup: {provider.name if hasattr(provider, 'name') else provider}")
            _registered_providers.append(provider)
        return provider
    
    if func_or_provider is not None and hasattr(func_or_provider, 'destroy'):
        return _register_instance(func_or_provider)
    
    if func_or_provider is not None and isinstance(func_or_provider, type):
        original_init = func_or_provider.__init__
        
        def patched_init(self, *args, **kwargs):
            original_init(self, *args, **kwargs)
            _register_instance(self)
            
        func_or_provider.__init__ = patched_init
        return func_or_provider
    
    if func_or_provider is not None and callable(func_or_provider):
        def wrapper(*args, **kwargs):
            provider = func_or_provider(*args, **kwargs)
            return _register_instance(provider)
        
        # Preserve function metadata
        wrapper.__name__ = func_or_provider.__name__
        wrapper.__doc__ = func_or_provider.__doc__
        wrapper.__annotations__ = func_or_provider.__annotations__
        wrapper.__module__ = func_or_provider.__module__

        return wrapper
    
    def decorator(func):
        if isinstance(func, type):  # Class decorator
            original_init = func.__init__
            
            def patched_init(self, *args, **kwargs):
                original_init(self, *args, **kwargs)
                _register_instance(self)
                
            func.__init__ = patched_init
            return func
        else:  # Function decorator
            def wrapper(*args, **kwargs):
                provider = func(*args, **kwargs)
                return _register_instance(provider)
            
            # Preserve function metadata
            wrapper.__name__ = func.__name__
            wrapper.__doc__ = func.__doc__
            wrapper.__annotations__ = func.__annotations__
            wrapper.__module__ = func.__module__
            
            return wrapper

    return decorator

def unregister_provider(provider) -> None:
    if provider in _registered_providers:
        _registered_providers.remove(provider)

async def _async_cleanup() -> None:
    global _cleanup_running
    
    if _cleanup_running:
        return
    
    _cleanup_running = True
    
    if not _registered_providers:
        return
        
    await asyncio.gather(
        *[provider.destroy() for provider in _registered_providers]
    )
    
    _registered_providers.clear()

def _run_async_cleanup():
    if not _registered_providers:
        return
        
    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        providers = list(_registered_providers)
        for provider in providers:
            try:
                loop.run_until_complete(provider.destroy())
            except Exception as e:
                pass

        _registered_providers.clear()
        
        loop.close()
    except Exception as e:
        pass

def _cleanup_handler() -> None:
    _run_async_cleanup()

atexit.register(_cleanup_handler)

for sig in (signal.SIGINT, signal.SIGTERM):
    signal.signal(sig, lambda signal, frame: sys.exit(0))
