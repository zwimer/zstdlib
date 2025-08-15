from typing import TypeVar, Self, Any, cast
from collections import defaultdict
from threading import RLock
from functools import cache


T = TypeVar("T")


class _None:
    """A unique NoneType"""


class NoInstanceError(TypeError):
    """A TypeError raised when trying to get a Singleton instance before constructing it"""


def _no_subclass(*_, **__):
    raise TypeError("Singleton subclasses may not be subclassed")


class _SingletonType(type):
    """
    A thread-safe singleton metaclass
    Singleton types may not be subclassed except for the base Singleton type
    """

    _disallow_init_subclass = False  # If True, disallow __init_subclass__ in __new__'s attrs
    _instances: dict[type, Any] = {}  # Fully constructed and initialized singleton types
    # Lock is preferred to RLock, but could deadlock if user write a constructor that invokes itself
    _cls_locks: dict[type, RLock] = defaultdict(RLock)
    _lock = RLock()

    def __new__(mcs, name, bases, attrs, **kwargs):
        """Define a new Singleton type"""
        ret = super().__new__(mcs, name, bases, attrs, **kwargs)
        if mcs._disallow_init_subclass and "__init_subclass__" in attrs:
            raise TypeError("Singleton subclasses may not define __init_subclass__")
        with mcs._lock:
            mcs._cls_locks[ret] = RLock()
        return ret

    def __call__(cls, *args, **kwargs):
        """Intercept all instantiations to ensure at most one instance exists"""
        with cls._lock:
            cls_lock = cls._cls_locks[cls]
        with cls_lock:
            if (ret := cls._instances.get(cls, _None)) is _None:
                cls._instances[cls] = (ret := super().__call__(*args, **kwargs))
        return ret

    @classmethod
    @cache
    def instance(mcs, t: type[T]) -> T:
        """Get the instance of cls"""
        if not isinstance(t, mcs):
            raise TypeError(f"{t} is not a Singleton type")
        with mcs._lock:
            cls_lock = mcs._cls_locks[t]
        with cls_lock:
            if (got := mcs._instances.get(t, _None)) is _None:
                raise NoInstanceError(f"No instance of {t} found")
        return got


class Singleton(metaclass=_SingletonType):
    """A thread-safe singleton base class"""

    @classmethod
    def instance(cls) -> Self:
        """Blocking get the instance of cls; raise if not constructed"""
        return cast(_SingletonType, type(cls)).instance(cls)

    def __init_subclass__(cls, *args, **kwargs):
        """Disallow subclassing"""
        cls.__init_subclass__ = _no_subclass


# Disallow __init_subclass__ in Singleton subclasses
_SingletonType._disallow_init_subclass = True  # pylint: disable=protected-access
