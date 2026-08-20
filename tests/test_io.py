from typing import Any
import tempfile
import unittest

from zstdlib.io import ProtectedFile, BinaryIO, TextIO, io


class RamFile(tempfile.SpooledTemporaryFile):
    """A file-like object that stores its contents in memory."""

    rollover = NotImplemented  # Disallow rollover

    def __init__(self, *args: Any, mode: str = "w+", **kwargs: Any) -> None:
        super().__init__(10**9, *args, mode=mode, **kwargs)

    def load(self, x: str) -> None:
        self.write(x)
        self.flush()
        self.seek(self.tell() - len(x))


class TestIO(unittest.TestCase):

    def test_init(self) -> None:
        with RamFile(mode="wb+") as fb, RamFile() as fs:
            ts = TextIO(fs)
            tb = BinaryIO(fb)
            with self.assertRaises(TypeError):
                TextIO(fb)
            with self.assertRaises(TypeError):
                BinaryIO(fs)
            self.assertIs(ts, io(fs))
            self.assertIs(tb, io(fb))

    def test_protected_file(self) -> None:
        with RamFile() as f:
            p = ProtectedFile(f)
            self.assertIs(f, p.raw)
            self.assertIs(f.mode, p.mode)
            for i in ("read", "readline", "readlines", "readall", "seek"):
                with self.assertRaises(AttributeError):
                    getattr(p, i)

    def test_unread(self) -> None:
        with RamFile() as raw:
            f = io(raw)
            f.unread("hello")  # type: ignore[arg-type]  # STF types as bytes regardless of mode :/
            self.assertEqual("hello", f._buffer)

    def test_read(self) -> None:
        with RamFile() as raw:
            raw.load("foobaz")
            f = io(raw)
            # Test read of file
            self.assertEqual("fo", f.read(2))
            self.assertEqual("o", f.read(1))
            # Test read of buffer
            f.unread("bar")  # type: ignore[arg-type]  # STF types as bytes regardless of mode :/
            self.assertEqual("b", f.read(1))
            # Test read of file + buffer
            f.unread("foob")  # type: ignore[arg-type]  # STF types as bytes regardless of mode :/
            self.assertEqual("foobar", f.read(6))
            f.unread("foobar")  # type: ignore[arg-type]  # STF types as bytes regardless of mode :/
            self.assertEqual("foobarbaz", f.read())

    def test_peek(self) -> None:
        with RamFile() as raw:
            f = io(raw)
            f.unread("foo")  # type: ignore[arg-type]  # STF types as bytes regardless of mode :/
            # Test peek of buffer
            for i in range(3):
                self.assertEqual("fo", f.peek(2))
            self.assertEqual("foo", f.read())
            # Test peek of file
            raw.load("bar")
            for i in range(3):
                self.assertEqual("ba", f.peek(2))
            self.assertEqual("bar", f.read())
            # Test peek of both
            f.unread("baz")  # type: ignore[arg-type]  # STF types as bytes regardless of mode :/
            raw.load("qux")
            for i in range(3):
                for k in range(5):
                    self.assertEqual("bazqu"[:k], f.peek(k))
            self.assertEqual("bazqux", f.read())


if __name__ == "__main__":
    unittest.main()
