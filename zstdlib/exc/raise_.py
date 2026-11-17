from collections.abc import Callable
from typing import Never

from ..not_set import NotSetType, NotSet
from .pop_frames import PopFrames

__all__ = ("raise_",)


def raise_[**P, R: BaseException](
    e: BaseException,
    from_: Callable[P, R] | R | None | NotSetType = NotSet,
    /,
    *args: P.args,
    **kwargs: P.kwargs,
) -> Never:
    """Raise e from from_; if from_ isn't an exception, from_=from_(*args, **kwargs)"""
    if not isinstance(from_, BaseException | None | NotSetType):
        if not callable(from_):
            raise TypeError("from_ must be callable")
        from_ = from_(*args, **kwargs)
    with PopFrames(1):
        if from_ is NotSet:
            raise e
        assert isinstance(from_, BaseException | None)
        raise e from from_
