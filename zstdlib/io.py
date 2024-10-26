from io import (
    IOBase,
    TextIOBase as _PyRawTextIOBase,
    RawIOBase as _PyRawIOBase,
    BufferedIOBase as _PyBufferedIOBase,
)
from threading import RLock
from itertools import chain
from typing import Self
import weakref


__all__ = ("TextIO", "BinaryIO", "io")

type _BinaryBase = _PyRawIOBase | _PyBufferedIOBase
type _TextBase = _PyRawTextIOBase


class ProtectedFile:
    """
    A wrapper around an IO object that prevents access to certain attributes
    If absolutely necessary, users can access the raw object directly via .raw
    """

    PROTECTED_PREFIXES = ("read", "seek", "getbuffer", "getvalue", "detach")
    __slots__ = ("raw",)

    def __init__(self, raw: IOBase) -> None:
        """
        :param raw: The raw IO object to wrap, users can access it directly if they must
        """
        self.raw: IOBase = raw

    def __getattr__(self, item):
        """
        Prevent access to certain attributes
        """
        if any(item.startswith(i) for i in self.PROTECTED_PREFIXES):
            raise AttributeError(f"Attribute {item} is protected")
        return getattr(self.raw, item)

    def __hash__(self) -> int:
        return hash(self.raw)


# See bug: https://github.com/pylint-dev/pylint/issues/9335
# pylint: disable=undefined-variable
class _IOWrapperBase[T: (str, bytes)]:
    """
    A base class for IO objects that adds additional functionality such as readuntil, unread, and peek
    These classes are singletons with respect to their input object
    Note: This class takes ownership of the input object, do not use it elsewhere
    """

    __slots__ = ("lock", "f", "_buffer", "_eof")
    _instances: weakref.WeakKeyDictionary[IOBase, Self] = weakref.WeakKeyDictionary()
    _wr_lock = RLock()

    def __new__(cls, f: IOBase, binary: bool) -> Self:
        """
        Create a new instance of cls for raw, or return an existing instance if one exists
        """
        with cls._wr_lock:
            if (ret := cls._instances.get(f, None)) is None:
                cls._instances[f] = (ret := super().__new__(cls))
        return ret

    def __init__(self, f: IOBase, *, binary: bool) -> None:
        """
        Initialize the IO object with a raw IO object
        Note: This class takes ownership of the input object, do not use it elsewhere
        :param f: The raw IO object to wrap
        :param binary: If True, the IO object will read/write bytes, otherwise it will read/write strings
        """
        self._buffer: T = (bytes if binary else str)()  # type: ignore
        self.f = ProtectedFile(f)
        self.lock = RLock()

    def read(self, size: int = -1) -> T:
        """
        Read up to size characters from self.raw or until EOF
        If size is unspecified or -1, read until EOF
        """
        if size == 0:
            return self._buffer[:0]
        with self.lock:
            ret = self._read_buffer(size)
            if len(ret) == size:
                return ret
            ret += self._read(-1 if size == -1 else (size - len(ret)))
        return ret

    def readline(self) -> T:
        """
        Read a line from self.raw or until EOF
        Newline is included in the return value
        """
        with self.lock:
            nl: T = "\n" if isinstance(self._buffer, str) else b"\n"
            ret = self._read_buffer(self._buffer.find(nl)) + self._read_buffer(1)
            if ret.endswith(nl):
                return ret
            return ret + self.f.raw.readline()  # type: ignore

    def readlines(self) -> list[T]:
        """
        Read all lines from self.raw until EOF
        """
        with self.lock:
            ret: list[T] = []
            while add := self.readline():
                ret.append(add)
            return ret

    def peek(self, size: int = -1) -> T:
        """
        Read size characters from self.raw or until EOF, without consuming the data
        """
        with self.lock:
            self.unread(ret := self.read(size))
        return ret

    def unread(self, data: T) -> None:
        """
        Unread data back to the internal buffer
        """
        with self.lock:
            self._buffer = data + self._buffer

    def readuntil(self, until: T, *, eof_ok: bool = True) -> T:
        """
        Read until until is found in f. If eof_ok is False, raise EOFError if until is not found before EOF.
        :param until: The str/bytes to read until
        :param inclusive: If True, the returned value will end with until
        :param eof_ok: if False, raise EOFError if until is not found before EOF
        :return: The data read from self.raw, up to and including until
        """
        if isinstance(until, str) ^ isinstance(self._buffer, str):
            raise TypeError("until: expected same type as buffer")
        if len(until) == 0:
            raise ValueError("until may not be empty")
        with self.lock:
            if until in self._buffer:
                return self._read_buffer(self._buffer.find(until) + len(until))
            buffer = [self._read_buffer()]
            # Use bytearray to avoid multiple concatenations
            # Read until until is found, avoid small read() syscall's because they are slow
            while (n := self._remainder(buffer, until)) and (add := self._read(n)):
                buffer.append(add)
            ret = buffer[0][:0].join(buffer)
            if not ret.endswith(until) and not eof_ok:
                raise EOFError("until: not found before EOF")
            return ret

    #
    # Helper functions
    #

    def _read(self, size) -> T:
        ret: T = self.f.raw.read(size)  # type: ignore
        return ret if ret else self._buffer[:0]  # Some .read's can return None

    def _read_buffer(self, size: int = -1) -> T:
        if size == -1:
            size = len(self._buffer)
        ret: T = self._buffer[:size]
        self._buffer = self._buffer[size:]
        return ret

    @staticmethod
    def _remainder(data: list[T], suffix: T) -> int:
        assert suffix, "suffix: expected non-empty str or bytes"
        rev = chain.from_iterable(reversed(i) for i in reversed(data))
        for index, (i, k) in enumerate(zip(rev, reversed(suffix))):
            if i != k:
                return len(suffix) - index
        return 0

    #
    # Protection
    #

    def __hash__(self) -> int:
        return hash((self.__class__, self.f))

    __deepcopy__ = None  # type: ignore
    __copy__ = None  # type: ignore


def _mode(f: IOBase, binary: bool | None) -> bool:
    mode = getattr(f, "mode", "")
    binary = binary or "b" in mode or isinstance(f, (_PyRawIOBase, _PyBufferedIOBase))
    text = (binary is False) or (mode and "b" not in mode) or isinstance(f, _PyRawTextIOBase)
    if not text and not binary:
        raise TypeError("Cannot determine if IO object is text or binary")
    if text and binary:
        raise TypeError("IO object is both text and binary")
    return text


class TextIO(_IOWrapperBase[str]):
    """
    A wrapper around TextIO objects that add additional functionality such as readuntil, unread, and peek
    """

    def __new__(cls, f: IOBase):
        if not _mode(f, binary=False):
            raise TypeError("raw should be a non-binary IO object")
        return super().__new__(cls, f, binary=False)

    def __init__(self, f: IOBase):
        super().__init__(f, binary=False)


class BinaryIO(_IOWrapperBase[bytes]):
    """
    A wrapper around BinaryIO objects that add additional functionality such as readuntil, unread, and peek
    """

    def __new__(cls, f: IOBase):
        if _mode(f, binary=True):
            raise TypeError("raw should be a binary IO object")
        return super().__new__(cls, f, binary=True)

    def __init__(self, f: IOBase):
        super().__init__(f, binary=False)


def io(raw: IOBase, binary: bool | None = None) -> TextIO | BinaryIO:
    """
    Convert an IO object to a TextIO or BinaryIO object
        For raw to be valid, one of the three must be true:
        1. raw is an io.TextIOBase, io.RawIOBase, or io.BufferedIOBase object
        2. raw has a .mode string attribute
        3. binary must be set
    If the three detection methods disagree on if raw is binary, a TypeError is raised
    """
    return TextIO(raw) if _mode(raw, binary) else BinaryIO(raw)
