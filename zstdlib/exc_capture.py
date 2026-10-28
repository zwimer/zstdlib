from contextlib import AbstractContextManager, contextmanager
from collections.abc import Iterator
from typing import Protocol

__all__ = ("ExcCapture", "ExcDelay")


type EXC_T = type[BaseException] | tuple[type[BaseException]]


class CaptureFType(Protocol):
    """The type of the capture function (used for type checking)"""

    def __call__(self, exc_t: EXC_T | None = None) -> AbstractContextManager[None]: ...


class ExcCapture:
    """A class that exposes a context manager which captures and suppresses any raised exception of a given type / tuple of types"""

    __slots__ = ("errors", "exc_t")

    def __init__(self, exc_t: EXC_T | None = None) -> None:
        """
        Args:
            msg: The exception group message
            exc_t: The exception type the capture function should capture, if None it must be passed to the capture function directly
        """
        self.exc_t: EXC_T | None = exc_t
        self.errors: list[BaseException] = []

    @contextmanager
    def capture(self, exc_t: EXC_T | None = None) -> Iterator[None]:
        """Capture and suppress any exception if type/tuple of types exc_t (self.exc_t if None)"""
        exc_t = self.exc_t if exc_t is None else exc_t
        if exc_t is None:
            raise ValueError("No exception type provided here nor during construction")
        try:
            yield
        except exc_t as e:
            self.errors.append(e)


class ExcDelay(ExcCapture):
    """A context manager subclass of ExcCapture that raises on exit if errors are captured"""

    __slots__ = ("_msg",)

    def __init__(
        self,
        msg: str,
        exc_t: type[BaseException] | None = None,
    ) -> None:
        """
        Args:
            exc_t: The exception type the capture function should capture, if None it must be passed to the capture function directly
            msg: The exception group message
        """
        super().__init__(exc_t)
        self._msg = msg

    def __enter__(self) -> CaptureFType:
        """Return the capture function to use"""
        return self.capture

    def __exit__(self, type_: type[BaseException] | None, *_: object) -> None:
        """Raise an ExceptionGroup (or BaseExceptionGroup depending on exc_t) if self.errors"""
        if type_ is None and self.errors:
            # Auto-converts to ExceptionGroup if all items are Exceptions
            raise BaseExceptionGroup(self._msg, self.errors)
