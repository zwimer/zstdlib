from typing import Concatenate, overload
from collections.abc import Callable
from functools import wraps

__all__ = ("hybridmethod",)


type _HybridFunc[T, R, **P] = Callable[Concatenate[T | None, type[T], P], R]


class hybridmethod[T, R, **P]:  # Name aligns with @staticmethod and such
    """
    A member function decorator that combines an instances bound function and @classmethod
    If a member function uses @hybridmethod then it may use the signature:
        @hybridmethod
        def f(self: Foo | None, cls: type[Foo], ...)
    This could be used to implement functions such as:
        def history(self: Foo | None, cls: type[Foo], *, id: int | None = None): ...
            ...
        A.history(id=a.id)
        A.history(id=0)
        a.history()
    Note that using Self is the type signature is invalid, just as it is with @classmethod
    """

    __slots__ = ("_fn",)

    def __init__(self, fn: _HybridFunc[T, R, P]) -> None:
        self._fn: _HybridFunc[T, R, P] = fn

    @overload
    def __get__(self, instance: T, owner: type[T] | None = None, /) -> Callable[P, R]: ...

    @overload
    def __get__(self, instance: None, owner: type[T], /) -> Callable[P, R]: ...

    def __get__(self, instance: T | None, owner: type[T] | None = None, /) -> Callable[P, R]:
        if owner is None:
            if instance is None:
                raise TypeError("instance and owner should not both be None")
            owner = type(instance)

        # functools.partial doesn't preserve typing as we need it to :/
        @wraps(self._fn)
        def ret(*args: P.args, **kwargs: P.kwargs) -> R:
            return self._fn(instance, owner, *args, **kwargs)

        return ret
