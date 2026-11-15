from typing import ClassVar, Never, Any, cast
from collections import defaultdict
from threading import RLock
from functools import cache

__all__ = ("NoInstanceError", "Singleton")


class NoInstanceError(TypeError):
    """A TypeError raised when trying to get a Singleton instance before constructing it"""


def _no_subclass(*_: Any, **__: Any) -> Never:
    raise TypeError("Singleton subclasses may not be subclassed")


class _SingletonType(type):
    """A thread-safe singleton metaclass
    Singleton types may not be subclassed except for the base Singleton type
    """

    _disallow_init_subclass = False  # If True, disallow __init_subclass__ in __new__'s attrs
    # Fully constructed and initialized singleton types
    _instances: ClassVar[dict[type[Singleton], Singleton]] = {}
    # Lock is preferred to RLock, but could deadlock if user write a constructor that invokes itself
    _cls_locks: ClassVar[dict[_SingletonType, RLock]] = defaultdict(RLock)
    _lock = RLock()

    def __new__(
        mcs: type[_SingletonType], name: str, bases: tuple[type, ...], attrs: dict[str, Any], **kwargs: Any
    ) -> _SingletonType:
        """Define a new Singleton type"""
        if mcs._disallow_init_subclass and "__init_subclass__" in attrs:
            raise TypeError("Singleton subclasses may not define __init_subclass__")
        mcs._disallow_init_subclass = True
        ret = super().__new__(mcs, name, bases, attrs, **kwargs)
        with mcs._lock:
            mcs._cls_locks[ret] = RLock()
        return ret

    def __call__(cls, *args: Any, **kwargs: Any) -> Singleton:
        """Intercept all instantiations to ensure at most one instance exists"""
        assert issubclass(cls, Singleton), "Must derive from Singleton"
        with cls._lock:
            cls_lock = cls._cls_locks[cls]
        with cls_lock:
            if (ret := cls._instances.get(cls, None)) is None:
                ret = cls._instances[cls] = super().__call__(*args, **kwargs)
        return ret

    @cache
    def instance[T: Singleton](cls: type[T]) -> T:
        """Get the instance of cls"""
        # pylint: disable=protected-access
        mcs = cast(_SingletonType, type(cls))  # mypy can't figure this out :/
        with mcs._lock:
            cls_lock = mcs._cls_locks[cls]
        with cls_lock:
            if (got := mcs._instances.get(cls, None)) is None:
                raise NoInstanceError(f"No instance of {cls.__qualname__} found")
        # pylint: enable=protected-access
        return cast(T, got)


class Singleton(metaclass=_SingletonType):
    """A thread-safe singleton base class"""

    def __init_subclass__(cls, *args: Any, **kwargs: Any) -> None:
        """Disallow subclassing"""
        cls.__init_subclass__ = _no_subclass  # type: ignore[method-assign]
