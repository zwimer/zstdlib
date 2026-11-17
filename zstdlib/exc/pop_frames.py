from types import TracebackType
from typing import Self
import sys

__all__ = ("PopFrames",)


class PopFrames:
    """
    A context manager used to pop traceback frames from an exception;
    Note that python traceback frames are added as each call exception propgation unwinds the call stack
    Thus you can only pop frames between the frame PopFrames lives in and where the exceptions was raised
    MRO superclasses are not supported
    """

    __slots__ = ("_furthest_n", "_n")

    def __init__(self, n: int = 0, *, furthest_n: int = 0) -> None:
        self._validate(n, furthest_n)
        self._furthest_n: int = furthest_n
        self._n = n

    def __enter__(self) -> Self:
        return self

    def __exit__(
        self, _: type[BaseException] | None, exc: BaseException | None, _2: TracebackType | None
    ) -> None:
        if isinstance(exc, BaseException):
            self.modify(exc, self._n, furthest_n=self._furthest_n)
        elif exc is not None:
            raise TypeError("exc is not a BaseException | None")

    @classmethod
    def modify(cls, exc: BaseException, n: int, furthest_n: int = 0) -> None:
        """Modify the traceback frames of exc; removes the n most recently entered frames
        If foo calls bar calls baz which raises, n=2 removes (baz, raise)
        from the traceback and furthest_n=1 removes foo from the traceback

        Args:
            exc: The exception to modify
            n: The number of frames to remove, referse to the most recently entered frames
            furthest_n: The number of frames to remove, referse to the least recently entered frames
        """
        cls._validate(n, furthest_n)
        if not isinstance(exc, BaseException):
            raise TypeError("exc is not a BaseException")
        if n == furthest_n == 0:
            return
        # Record the old traceback
        frames: list[TracebackType] = []
        tb = exc.__traceback__
        while tb is not None:
            frames.append(tb)
            tb = tb.tb_next
        # Install the new traceback
        new: TracebackType | None = None
        for f in reversed(frames[furthest_n if furthest_n else None : -n if n else None]):
            new = TracebackType(new, f.tb_frame, f.tb_lasti, f.tb_lineno)
        exc.__traceback__ = new

    @classmethod
    def active(cls, n: int = 0, *, reraise: bool, furthest_n: int = 0) -> None:
        """Remove traceback frames from an active exception, will reraise unless False"""
        e = sys.exc_info()
        if e[0] is None:
            raise RuntimeError("No active exception")
        cls.modify(e[1], n, furthest_n=furthest_n)
        if reraise:
            raise  # noqa: PLE0704  # pylint: disable=misplaced-bare-raise

    # Private helpers

    @staticmethod
    def _validate(n: int, furthest_n: int) -> None:
        if not isinstance(n, int) or not isinstance(furthest_n, int):
            raise TypeError("Number of frames to pop must be type int")
        if n < 0 or furthest_n < 0:
            raise ValueError("May not pop a negative number of frames")
