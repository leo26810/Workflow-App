import threading
import time
from functools import wraps


def ttl_cache(ttl_seconds=300):
    def decorator(func):
        cache = {}
        lock = threading.Lock()

        @wraps(func)
        def wrapper(*args, **kwargs):
            key = (args, tuple(sorted(kwargs.items())))
            now = time.time()

            with lock:
                cached = cache.get(key)
                if cached and now - cached[0] < ttl_seconds:
                    return cached[1]
                if cached:
                    cache.pop(key, None)

            result = func(*args, **kwargs)
            with lock:
                cache[key] = (now, result)
            return result

        def cache_clear():
            with lock:
                cache.clear()
            if hasattr(func, 'cache_clear'):
                func.cache_clear()

        setattr(wrapper, 'cache_clear', cache_clear)
        return wrapper

    return decorator
