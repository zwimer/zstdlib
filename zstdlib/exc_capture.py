from contextlib import AbstractContextManager, contextmanager
from collections.abc import Iterator
from typing import Self

__all__ = ("ExcCapture", "ExcDelay")


type EXC_T = type[BaseException] | tuple[type[BaseException]]


class ExcCapture:
    """A class that exposes a context manager which captures and suppresses any raised exception of a given type / tuple of types"""

    __slots__ = ("errors", "exc_t", "previous")

    def __init__(self, exc_t: EXC_T | None = None) -> None:
        """
        Args:
            msg: The exception group message
            exc_t: The exception type the capture function should capture, if None it must be passed to the capture function directly
        """
        self.previous: BaseException | None = None  # The result of the last capture() invocation
        self.errors: list[BaseException] = []
        self.exc_t: EXC_T | None = exc_t

    @contextmanager
    def capture(self, exc_t: EXC_T | None = None) -> Iterator[None]:
        """
        Capture and suppress any exception if type/tuple of types exc_t (self.exc_t if None)
        This function sets self.previous on exit
        """
        exc_t = self.exc_t if exc_t is None else exc_t
        if exc_t is None:
            raise ValueError("No exception type provided here nor during construction")
        try:
            yield
            self.previous = None
        except exc_t as e:
            self.previous = e
            self.errors.append(e)

    def __call__(self, exc_t: EXC_T | None = None) -> AbstractContextManager[None]:
        """An alias for .capture"""
        return self.capture(exc_t)


class ExcDelay(ExcCapture):
    """A context manager subclass of ExcCapture that raises on exit if errors are captured"""

    __slots__ = ("_msg", "armed")

    def __init__(
        self,
        msg: str,
        exc_t: type[BaseException] | None = None,
        *,
        armed: bool = True,
    ) -> None:
        """
        Args:
            msg: The exception group message
            exc_t: The exception type the capture function should capture, if None it must be passed to the capture function directly
            armed: If False, do not raise on context exit if self.errors
        """
        if not isinstance(msg, str):
            raise TypeError(f"Invalid message type: {type(msg)}")
        self.armed: bool = armed
        self._msg: str = msg
        super().__init__(exc_t)

    def __enter__(self) -> Self:
        """Return the capture function to use"""
        return self

    def __exit__(self, type_: type[BaseException] | None, *_: object) -> None:
        """Raise an ExceptionGroup (or BaseExceptionGroup depending on exc_t) if self.errors"""
        if type_ is None and self.errors and self.armed:
            # Auto-converts to ExceptionGroup if all items are Exceptions
            raise BaseExceptionGroup(self._msg, self.errors)
