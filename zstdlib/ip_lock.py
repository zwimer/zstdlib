from typing import ClassVar, Final, Self, Any, override, final
from abc import ABC, abstractmethod
from contextlib import suppress
from threading import RLock, Lock
from pathlib import Path
from stat import S_ISREG

from fasteners import InterProcessLock

from .keyed_instance import KeyedInstance
from .util import normpath

__all__ = ("AbstractIPLock", "GlobalIPLock", "IPLock", "LockHung", "LockPathInUse", "NotAcquired", "RIPLock")


class NotAcquired(RuntimeError):
    """Raised by AbstractIPLock.release if a lock is not acquired"""


class LockHung(RuntimeError):
    """Raised when a non-reentrant lock attempts to reenter with blocking=True and no timeout"""


class AbstractIPLock(ABC):
    """An abstract interprocess lock that uses a Path for IPC synchronization"""

    # Abstract Methods

    @property
    @abstractmethod
    def path(self) -> Path:
        """The path this lock is synchronized across processes with"""

    @property
    @abstractmethod
    def acquired(self) -> bool:
        """Whether the lock has been acquired or not"""

    @abstractmethod
    def _acquire(self, blocking: bool, timeout_per: float | None) -> bool:
        """Acquire the lock, assumes blocking if timeout_per and args are valid"""

    @abstractmethod
    def release(self) -> None:
        """Release the lock, raises NotAcquired if not self.acquired"""

    # Concrete methods

    def acquire(self, blocking: bool = True, *, timeout_per: int | float | None = None) -> bool:
        """
        Acquire the lock, return False only if (timeout or not blocking) and acquisition fails
        Note that timeout is per-lock acquisition, there may be multiple locks internally
        Timeout is not allowed if blocking is False
        """
        if isinstance(timeout_per, int):
            timeout_per = float(timeout_per)
        if not isinstance(timeout_per, float | None):
            raise TypeError("timeout_per must be of type: int | float | None")
        if timeout_per is not None and timeout_per < 0:
            raise ValueError("Non-negative timeout is required")
        if timeout_per and not blocking:
            raise ValueError("Timeout requires blocking=True")
        return self._acquire(blocking, timeout_per)

    def __enter__(self) -> Self:
        """Acquire the lock"""
        self.acquire(True)
        return self

    def __exit__(self, *_: object) -> None:
        """Release the lock"""
        self.release()


@final
class GlobalIPLock(KeyedInstance, AbstractIPLock):
    """
    A thread-safe reentrant process lock keyed by a normalized resolved absolute file path to a regular file
    Basically a thread-safe wrapper around InterProcessLock that adds reference counting
    Warning: The passed file should be a regular file with no symlinks or hardlinks to it; this is not checked
    Warning: All locks of the same path are the same instance. Locking is per-process, not per-thread
    Warning: This lock uses the given path to syncronize inter-process locking, do not edit underlying file
    InterProcessLock may free the lock on exit if still held
    """

    __slots__ = ("_ip_lock", "_path", "_rc", "_t_lock")

    def __init__(self, path: Path) -> None:
        """
        Construct a GlobalIPLock from a normalized resolved absolute path to an unlinked regular file
        Consider calling .new(path) instead, as this normalizes and checks path safety on every invocation
        Because instances are keyed by path, path must be a normalized absolute pathlib.Path
        """
        if not isinstance(path, Path):
            raise TypeError("path should be a Path; consider using .new()")
        if path != (path := self.normalize(path)):
            raise ValueError("GlobalIPLock paths must be normalized; consider using .new()")
        self._ip_lock: Final[InterProcessLock] = InterProcessLock(path)
        self._path: Path = path  # b/c their path is in bytes
        self._t_lock = RLock()
        self._rc: int = 0
        # Try to create the underlying file, this isn't actually necessary at the moment
        # but useful to prevent other users / programs from messing with the file path
        with suppress(OSError):
            self._path.touch(exist_ok=True)

    @classmethod
    def new(cls, path: str | Path) -> Self:
        """Construct the AbstractIPLock by normalizing the given path; also checks path for safety"""
        path = cls.normalize(path)
        return cls(path)

    @staticmethod
    def normalize(path: str | Path, check: bool = True) -> Path:
        """
        Normalize and resolve a path to one that GlobalIPLock might accept
        If check: Also checks path for non-regular files / file with hardlinks to it
        """
        if isinstance(path, str):
            path = Path(path)
        if not isinstance(path, Path):
            raise TypeError("path must be a str | pathlib.Path")
        if check and path.is_symlink():
            raise FileExistsError(f"File is a symlink: {path}")
        path = normpath(path.resolve()).absolute()
        if check:
            try:
                info = path.lstat()
                if not S_ISREG(info.st_mode) or info.st_nlink != 1:
                    raise FileExistsError(f"The lock file exists but is not a regular file: {path}")
            except FileNotFoundError:
                pass
        return path

    # Overrides

    @property
    @override
    def path(self) -> Path:
        """The path the lock is synchronized on"""
        return self._path

    @property
    @override
    def acquired(self) -> bool:
        """Return true if acquired"""
        return bool(self._rc)

    @override
    def _acquire(self, blocking: bool, timeout_per: float | None) -> bool:
        ret: bool = True
        with self._t_lock:
            assert bool(self._rc) == self._ip_lock.acquired
            if not self._rc or not self._ip_lock.acquire(blocking=False):
                ret = self._ip_lock.acquire(timeout=timeout_per) if blocking else False
            self._rc += 1
        return ret

    @override
    def release(self) -> None:
        """Release the lock"""
        if not self.acquired:
            raise NotAcquired(f"{self.__class__.__name__}: {self.path}")
        with self._t_lock:
            assert bool(self._rc) == self._ip_lock.acquired
            if self._rc <= 1:
                self._ip_lock.release()
            self._rc -= 1
            assert bool(self._rc) == self._ip_lock.acquired


class LockPathInUse(LookupError):
    """
    Raised when a user attempts to create an IPLock lock for a given
    GlobalIPLock that already exists with a different reentrancy setting
    """


class _IPLock(AbstractIPLock):
    """
    This lock can only be acquired if no other IPLock's hold a GlobalIPLock on path
    Acquiring this lock first internally acquires the lock GlobalIPLock(path)
    It then competes with all other IPLocks to acquire a lock keyed on path
    Warning: This lock only syncronizes on against other IPLocks on path, not other GlobalIPLock(path)'s
    If another object has a GlobalIPLock(path) IPLock will *not* block during acquire() until they release
    Warning: As this uses GlobalIPLock(path), do not manually release GlobalIPLock(path) without
    acquiring first or remove path, doing so may break the inter-process synchronization
    """

    __slots__ = ("_gipl", "_instance_lock", "_instance_reentrant", "_rc", "_sync_lock")
    _cls_reentrant: ClassVar[bool]  # For subclass to set
    _data: ClassVar[Final[dict[Path, tuple[bool, Lock]]]] = {}
    _data_lock: ClassVar[Final[Lock]] = Lock()

    def __init__(self, gipl: GlobalIPLock | Path | str, *args: Any, **kwargs: Any) -> None:
        """
        Construct an inter process lock syncronized by gipl (or GlobalIPLock.new(gipl) if str | Path)
        If a lock of a different reentrancy setting already exists for this gipl, raise LockPathInUse
        """
        super().__init__(*args, **kwargs)  # For MRO superclasses
        if isinstance(gipl, Path | str):
            gipl = GlobalIPLock.new(gipl)
        if not isinstance(gipl, GlobalIPLock):
            raise TypeError("gipl must be a GlobalIPLock or an argument to GlobalIPLock.new")
        self._gipl: Final[GlobalIPLock] = gipl
        with self._data_lock:
            got: tuple[bool, Lock] | None = self._data.get(gipl.path)
            if got is None:
                got = (self._cls_reentrant, Lock())
                self._data[gipl.path] = got
        if got[0] != self._cls_reentrant:
            raise LockPathInUse(f"Want reentrant={self._cls_reentrant} but existing lock is the opposite")
        self._instance_reentrant: Final[bool] = got[0]
        self._sync_lock: Final[Lock] = got[1]
        self._instance_lock: Final[Lock] = Lock()  # Allow multiple threads to use this instance at once
        self._rc: int = 0

    @property
    @override
    def path(self) -> Path:
        """The path the lock is synchronized on"""
        return self._gipl.path

    @property
    @override
    def acquired(self) -> bool:
        """Return true if locked"""
        return bool(self._rc)  # Might return False during .release() after rc -=1, before .release()

    @override
    def _acquire(self, blocking: bool, timeout_per: float | None) -> bool:
        ret = False
        if not self._gipl.acquire(blocking, timeout_per=timeout_per):
            return ret
        try:
            with self._instance_lock:
                acquired = self.acquired
                if acquired and not self._instance_reentrant:
                    if timeout_per is None:
                        raise LockHung(f"{self.__class__.__name__}: {self.path}")
                    return ret
                timeout = -1 if timeout_per is None else timeout_per
                if acquired or self._sync_lock.acquire(blocking, timeout=timeout):
                    self._rc += 1
                    ret = True
        finally:
            if not ret:
                self._gipl.release()
        return ret

    @override
    def release(self) -> None:
        """Release the lock"""
        with self._instance_lock:
            if not self.acquired:
                raise NotAcquired(f"{self.__class__.__name__}: {self.path}")
            self._rc -= 1
            if self._rc == 0:
                try:
                    self._sync_lock.release()
                except RuntimeError as e:
                    if e.args[0] == "cannot release un-acquired lock":  # This should not happen
                        raise RuntimeError("Representation invariant broken") from e
                    raise
        try:
            self._gipl.release()
        except NotAcquired as e:
            raise OSError("The GlobalIPLock lock was already unlocked by something else") from e


class IPLock(_IPLock):
    """A non-reentrant python lock that is synchronized across processes via a normalized path"""

    _cls_reentrant = False


class RIPLock(_IPLock):
    """A reentrant python lock that is synchronized across processes via a normalized path"""

    _cls_reentrant = True


assert (
    isinstance(_IPLock.__doc__, str) and isinstance(IPLock.__doc__, str) and isinstance(RIPLock.__doc__, str)
)
IPLock.__doc__ = IPLock.__doc__ + _IPLock.__doc__
RIPLock.__doc__ = RIPLock.__doc__ + _IPLock.__doc__
