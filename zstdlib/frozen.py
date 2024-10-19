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


def frozen(arg: str | type):
    """
    A class decorator to permanently freeze a class after some method, __init__ by default
    If passed a string, will freeze after the method with that name
    """

    def shim_method(cls: type, name, new) -> None:
        original = getattr(cls, name)
        for i in _FN_ATTRS:
            if hasattr(original, i):
                setattr(new, i, getattr(original, i))
        setattr(cls, name, new)

    def mk_frozen(cls: type, method: str) -> type:
        original_method: Callable = getattr(cls, method)
        original_setattr: Callable = cls.__setattr__
        original_delattr: Callable = cls.__delattr__

        def new_method(self, *args, **kwargs):
            ret = original_method(self, *args, **kwargs)
            # pylint: disable=protected-access
            self._frozen = True  # type: ignore[attr-defined]
            return ret

        def __setattr__(self, key: str, value):
            if getattr(self, "_frozen", False):
                raise AttributeError("Cannot modify frozen object")
            return original_setattr(self, key, value)

        def __delattr__(self, item: str):
            if getattr(self, "_frozen", False):
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
