from typing import Protocol, Any, overload
from collections.abc import Callable

_FN_ATTRS = (
    "__annotations__",
    "__type_params__",
    "__qualname__",
    "__module__",
    "__name__",
    "__doc__",
    "__defaults__",
    "__kwdefaults__",
)


class Freezable:
    """A base class for objects that can be frozen"""

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        # Avoid name mangling b/c we use object.__setattr__ etc. on these
        # Instead use unlikely to collide names for member variables
        super().__init__(*args, **kwargs)  # For MRO super classes
        if hasattr(self, "_freezable_frozen_") or hasattr(self, "_freezable_can_thaw_"):
            raise ValueError("Base class defines _freezable_frozen_ or _freezable_can_thaw_")
        self._freezable_can_thaw_: bool = True
        self._freezable_frozen_: bool = False

    # Public

    @property
    def frozen(self) -> bool:
        """Check if this object is frozen"""
        return self._freezable_frozen_

    @property
    def thawable(self) -> bool:
        """Check if this object can be thawed or is unfrozen"""
        return self._freezable_can_thaw_

    def freeze(self, *, permanent: bool = False) -> None:
        """Prevent further modifications to this object
        This function can be called on an already frozen object
        """
        if permanent:
            object.__setattr__(self, "_freezable_can_thaw_", False)
        object.__setattr__(self, "_freezable_frozen_", True)

    def thaw(self) -> None:
        """Allow modifications to this object"""
        if not self._freezable_can_thaw_:
            raise RuntimeError("Cannot thaw permanently frozen object")
        object.__setattr__(self, "_freezable_frozen_", False)

    def __setattr__(self, key: str, value: Any) -> None:
        if getattr(self, "_freezable_frozen_", False):
            raise AttributeError("Cannot modify frozen object")
        super().__setattr__(key, value)

    def __delattr__(self, item: str) -> None:
        if getattr(self, "_freezable_frozen_", False):  # B/c invoked before __init__ defines _frozen
            raise AttributeError("Cannot modify frozen object")
        super().__delattr__(item)


class _ClassDecorator(Protocol):
    def __call__[T](self, cls: type[T], /) -> type[T]: ...


@overload
def frozen(arg: str, /) -> _ClassDecorator: ...


@overload
def frozen[T](arg: type[T], /) -> type[T]: ...


def frozen(arg: str | type[Any], /) -> _ClassDecorator | type[Any]:
    """
    A class decorator to permanently freeze a class after some method, __init__ by default
    If passed a string, return a decorator that will freeze after the method with that name
    """
    ff_key: str = "_freezable_frozen_"

    def shim_method[T](cls: type[T], name: str, new: Callable[..., Any]) -> None:
        """Install shims for _FN_ATTRS; modifies new"""
        original = getattr(cls, name)
        for i in _FN_ATTRS:  # Copy attributes of old fn onto new fn
            if hasattr(original, i):
                setattr(new, i, getattr(original, i))
        setattr(cls, name, new)  # Install

    def mk_frozen[T](cls: type[T], method: str) -> type[T]:
        original_method: Callable[..., Any] = getattr(cls, method)
        original_setattr: Callable[[T, str, Any], None] = cls.__setattr__
        original_delattr: Callable[[T, str], None] = cls.__delattr__

        def new_method(self: T, *args: Any, **kwargs: Any) -> Any:
            ret = original_method(self, *args, **kwargs)
            setattr(self, ff_key, True)
            return ret

        def __setattr__(self: T, key: str, value: Any) -> None:
            if getattr(self, ff_key, False):
                raise AttributeError("Cannot modify frozen object")
            return original_setattr(self, key, value)

        def __delattr__(self: T, item: str) -> None:
            if getattr(self, ff_key, False):
                raise AttributeError("Cannot modify frozen object")
            return original_delattr(self, item)

        # Update cls with the new methods
        shim_method(cls, method, new_method)
        shim_method(cls, "__delattr__", __delattr__)
        shim_method(cls, "__setattr__", __setattr__)
        return cls

    if isinstance(arg, str):

        def decorator[T](cls: type[T]) -> type[T]:
            return mk_frozen(cls, arg)

        return decorator
    return mk_frozen(arg, "__init__")
