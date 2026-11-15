from typing import Any, ClassVar, Never, final, cast
from threading import Condition, Lock, get_ident
from collections.abc import Hashable
from abc import ABCMeta
import sys

__all__ = ("CircularConstructionError", "KeyedInstance", "KeyedInstanceProcessError")


class CircularConstructionError(RuntimeError):
    """Raised when keyed constructors form a circular dependency."""

    def __init__(self, type_: type) -> None:
        """type_ is the type that caused the circular dependency"""
        super().__init__(f"Circular construction dependency for {type_.__qualname__}")


class _Constructing:  # An int that is a unique type

    __slots__ = ("tid",)

    def __init__(self, tid: int) -> None:
        self.tid: int = tid


@final
class _KeyedInstanceMeta(ABCMeta):
    """Metaclass implementing thread-safe keyed instance construction"""

    type _KIInstanceKey = tuple[type[KeyedInstance], Hashable]
    _ki_instances: ClassVar[dict[_KIInstanceKey, KeyedInstance | _Constructing]] = {}
    _ki_waiting: ClassVar[dict[int, _KIInstanceKey]] = {}
    _ki_base_class: ClassVar[type[Any] | None] = None  # KeyedInstance, after construction
    _ki_condition: ClassVar[Condition] = Condition(Lock())

    def __new__(
        mcs: type[_KeyedInstanceMeta],
        name: str,
        bases: tuple[type[Any], ...],
        namespace: dict[str, Any],
        **kwargs: Any,
    ) -> type:
        """Create KeyedInstance or a direct descendant."""
        if mcs is not _KeyedInstanceMeta:
            raise TypeError("_KeyedInstanceMeta cannot be subclassed")
        # Ensure nothing is deriving KeyedInstance
        root = mcs._ki_base_class
        if root is not None and (
            not any(base is root for base in bases)
            or any(isinstance(base, _KeyedInstanceMeta) and base is not root for base in bases)
        ):
            raise TypeError(f"{name} must directly inherit from KeyedInstance")
        cls = super().__new__(mcs, name, bases, namespace, **kwargs)
        # Lock in KeyedInstance as the base class as needed
        if root is None:
            mcs._ki_base_class = cls
        return cls

    def __call__[T](cls: type[T], key: Hashable, *args: Any, **kwargs: Any) -> T:
        """Return the instance cached under (cls, key), constructing it if needed."""
        mcs = type(cls)
        assert mcs is _KeyedInstanceMeta and issubclass(cls, KeyedInstance)
        cache_key = (cast(type[KeyedInstance], cls), key)

        # Lock-free fast path
        instances = _KeyedInstanceMeta._ki_instances
        ret: KeyedInstance | _Constructing | None = instances.get(cache_key)
        if ret is not None and not isinstance(ret, _Constructing):
            return cast(T, ret)

        construction_permission: _Constructing | None = None
        waiting = _KeyedInstanceMeta._ki_waiting
        condition = _KeyedInstanceMeta._ki_condition
        tid: int = get_ident()
        try:
            while True:  # Keep trying until some thread constructs the object
                with condition:
                    ret = instances.get(cache_key)

                    # No thread is constructing this object, claim it
                    if ret is None:
                        instances[cache_key] = construction_permission = _Constructing(tid)
                        break

                    # The item has been constructed already, return it
                    if not isinstance(ret, _Constructing):
                        return cast(T, ret)

                    # Record the dependency and follow the wait-for chain.
                    try:
                        waiting[tid] = cache_key  # Record we are waiting to construct this; safe b/c tid
                        blocking: int = ret.tid  # Thread constructing what we want to return

                        # Trace blocking threads to ensure none are waiting on us
                        while blocking != tid:
                            dependency_key = waiting.get(blocking)
                            if dependency_key is None:
                                break
                            dependency = instances.get(dependency_key)
                            if not isinstance(dependency, _Constructing):
                                break
                            blocking = dependency.tid
                        else:
                            raise CircularConstructionError(cls)

                        # Wait for a thread to finish construction then recheck if we can start
                        condition.wait()
                    finally:
                        waiting.pop(tid, None)

            # Construct the object finally then store the result
            assert construction_permission is not None
            ret = super().__call__(key, *args, **kwargs)  # type: ignore[misc]  # cls is an mcs
            assert isinstance(ret, KeyedInstance)
            with condition:
                instances[cache_key] = ret
                condition.notify_all()
                construction_permission = None  # In case condition.__exit__ fails
            return cast(T, ret)

        except:
            # Release the key on failed construction
            if construction_permission is not None:
                with condition:
                    if instances.get(cache_key) is construction_permission:
                        del instances[cache_key]
                    condition.notify_all()
            raise


class KeyedInstance(metaclass=_KeyedInstanceMeta):
    """Base class for instances cached by (concrete class, first argument).

    Concrete subclasses must be final and directly inherit from this class.

    The first argument is the cache key. Subsequent arguments
    are used only during construction, not for cache identity.

    The first thread to claim a cache key performs construction. If
    construction fails, another waiting thread can attempt construction.

    If items being constructed require constructing each other, a CircularConstructionError is raised

    Do not mix this with fork (uses thread ids internally); multiprocessing spawn is ok
    """

    def __reduce_ex__(self, *_: object) -> Never:
        """Prevent usage in multiprocessing"""
        raise TypeError(f"{type(self).__qualname__} instances cannot be pickled")


# Disallow mixing multiprocessing with KeyedInstance usage


class KeyedInstanceProcessError(RuntimeError):
    """Raised when keyed instances are used with multiprocessing."""


def _check_fork(event: str, *_: Any) -> None:
    if event not in {"os.fork", "os.forkpty"}:
        return
    # pylint: disable=protected-access
    with _KeyedInstanceMeta._ki_condition:
        if _KeyedInstanceMeta._ki_instances or _KeyedInstanceMeta._ki_waiting:  # Only raise if used
            raise KeyedInstanceProcessError("Cannot fork after creating KeyedInstance instances")
    # pylint: enable=protected-access


sys.addaudithook(_check_fork)
