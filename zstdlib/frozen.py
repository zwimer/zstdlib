from collections.abc import Callable
from typing import TypeVar


class Freezable:
    """
    A base class for objects that can be frozen
    """

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)  # For MRO super classes
        if hasattr(self, "_frozen") or hasattr(self, "_can_thaw"):
            raise ValueError("Base class defines _frozen or _can_thaw")
        self._can_thaw: bool = True
        self._frozen: bool = False

    def freeze(self, *, permanent: bool = False):
        """
        Prevent further modifications to this object
        """
        if permanent:
            self._can_thaw = False
        self._frozen = True

    def thaw(self):
        """
        Allow modifications to this object
        """
        if not self._can_thaw:
            raise RuntimeError("Cannot thaw permanently frozen object")
        object.__setattr__(self, "_frozen", False)

    def __setattr__(self, key: str, value) -> None:
        if getattr(self, "_frozen", False):
            raise AttributeError("Cannot modify frozen object")
        super().__setattr__(key, value)

    def __delattr__(self, item: str) -> None:
        if getattr(self, "_frozen", False):
            raise AttributeError("Cannot modify frozen object")
        super().__delattr__(item)


_SELF = TypeVar("_SELF")


def frozen(arg: str | type[_SELF]):
    """
    A class decorator to permanently freeze a class after some method, __init__ by default
    If passed a string, will freeze after the method with that name
    """

    def shim_method(cls: type[_SELF], name, new) -> None:
        original = getattr(cls, name)
        new.__qualname__ = original.__qualname__
        new.__name__ = original.__name__
        new.__doc__ = original.__doc__
        setattr(cls, name, new)

    def mk_frozen(cls: type[_SELF], method: str) -> type:
        original_method: Callable = getattr(cls, method)

        def new_method(self: _SELF, *args, **kwargs):
            ret = original_method(self, *args, **kwargs)
            # pylint: disable=protected-access
            self._frozen = True  # type: ignore[attr-defined]
            return ret

        def __setattr__(self: _SELF, key: str, value) -> None:
            if getattr(self, "_frozen", False):
                raise AttributeError("Cannot modify frozen object")
            super(cls, self).__setattr__(key, value)  # type: ignore[misc]

        def __delattr__(self: _SELF, item: str) -> None:
            if getattr(self, "_frozen", False):
                raise AttributeError("Cannot modify frozen object")
            super(cls, self).__delattr__(item)  # type: ignore[misc]

        # Update cls with the new methods
        shim_method(cls, method, new_method)
        shim_method(cls, "__delattr__", __delattr__)
        shim_method(cls, "__setattr__", __setattr__)
        return cls

    if isinstance(arg, str):
        return lambda cls: mk_frozen(cls, arg)
    return mk_frozen(arg, "__init__")
