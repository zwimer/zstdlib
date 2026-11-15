from collections.abc import Callable
from threading import Lock

__all__ = ("Func", "Str")


class Func[**P]:
    """A lazily evaluated function"""

    __slots__ = ("_args", "_fn", "_kwargs", "_lock", "_result")

    def __init__(self, fn: Callable[P, str], *args: P.args, **kwargs: P.kwargs) -> None:
        """Store a function and its arguments, on __call__(self) return fn(*args, **kwargs)
        The result of the function invocation is cached and will be reused
        """
        self._result: str | None = None
        self._lock = Lock()
        self._fn = fn
        self._args = args
        self._kwargs = kwargs

    def __call__(self) -> str:
        """Evaluate the saved function"""
        if self._result is not None:
            return self._result
        with self._lock:
            self._result = self._fn(*self._args, **self._kwargs)
        return self._result


class Str[**P](Func[P]):
    """A lazily evaluated string"""

    def __str__(self) -> str:
        return self()
