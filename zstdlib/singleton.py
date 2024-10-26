from threading import Condition, RLock
from typing import Any


class SingletonType(type):
    """
    A thread-safe singleton metaclass
    """

    _seen: set[type] = set()  # Types that should not be constructed again
    _instances: dict[type, Any] = {}  # Fully constructed and initialized singleton types
    _lock = Condition()
    # For preventing subclassing of Singletons
    _types: list[type] = []
    _types_lock = RLock()

    def __new__(mcs, name, bases, attrs, **kwargs):
        """
        Intercept all class definitions to prevent subclassing singleton types except for Singleton
        """
        if "__init_subclass__" in attrs:
            raise TypeError("Singleton's should not be subclassed or implement __init_subclass__")

        def _init_subclass(cls):
            with mcs._types_lock:
                if any(issubclass(cls, i) for i in mcs._types if i is not Singleton):
                    err = "Do not derive from Singletons other than the base Singleton type"
                    raise TypeError(err)
                mcs._types.append(cls)

        attrs["__init_subclass__"] = _init_subclass
        ret = super().__new__(mcs, name, bases, attrs, **kwargs)
        with mcs._types_lock:
            mcs._types.append(ret)
        return ret

    def __call__(cls, *args, **kwargs):
        """
        Intercept all instantiations to ensure at most one instance exists
        """
        # If the object has been seen before, wait for it to be available then return it
        with cls._lock:
            if cls in cls._seen:
                cls._lock.wait_for(lambda: cls in cls._instances)
                return cls._instances[cls]
            cls._seen.add(cls)
        # The object has not been constructed before, create it outside any lock to avoid delays
        obj = super().__call__(*args, **kwargs)
        with cls._lock:
            cls._instances[cls] = obj
            cls._lock.notify_all()  # Notify other threads of the new object
            return obj


class Singleton(metaclass=SingletonType):
    """
    A thread-safe singleton base class
    """
