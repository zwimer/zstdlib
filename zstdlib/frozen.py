from typing import Any, overload
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


@overload
def frozen[T](arg: str) -> Callable[[type[T]], type[T]]: ...
@overload
def frozen[T](arg: type[T]) -> type[T]: ...


def frozen[T](arg: str | type[T]) -> Callable[[type[T]], type[T]] | type[T]:
    """A class decorator to permanently freeze a class after some method, __init__ by default
    If passed a string, will freeze after the method with that name
    """

    def shim_method(cls: type, name: str, new: Callable) -> None:
        """Install shims for _FN_ATTRS; modifies new"""
        original = getattr(cls, name)
        for i in _FN_ATTRS:  # Copy attributes of old fn onto new fn
            if hasattr(original, i):
                setattr(new, i, getattr(original, i))
        setattr(cls, name, new)  # Install

    def mk_frozen(cls: type, method: str) -> type:
        original_method: Callable = getattr(cls, method)
        original_setattr: Callable = cls.__setattr__
        original_delattr: Callable = cls.__delattr__

        def new_method(self: Any, *args: Any, **kwargs: Any) -> Any:
            ret = original_method(self, *args, **kwargs)
            # pylint: disable=protected-access
            self._freezable_frozen_ = True  # type: ignore[attr-defined]
            return ret

        def __setattr__(self: Any, key: str, value: Any) -> Any:
            if getattr(self, "_freezable_frozen_", False):
                raise AttributeError("Cannot modify frozen object")
            return original_setattr(self, key, value)

        def __delattr__(self: Any, item: str) -> Any:
            if getattr(self, "_freezable_frozen_", False):
                raise AttributeError("Cannot modify frozen object")
            return original_delattr(self, item)

        # Update cls with the new methods
        shim_method(cls, method, new_method)
        shim_method(cls, "__delattr__", __delattr__)
        shim_method(cls, "__setattr__", __setattr__)
        return cls

    if isinstance(arg, str):
        return lambda cls: mk_frozen(cls, arg)
    return mk_frozen(arg, "__init__")
