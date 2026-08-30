# pylint: disable=missing-module-docstring,missing-class-docstring,missing-function-docstring
import unittest

from zstdlib.lazy import Str


def _append(buf: list[str], *, obj: str) -> str:
    buf.append(obj)
    return str(len(buf))


class TestLazy(unittest.TestCase):

    def test_func(self) -> None:
        buf: list[str] = []
        obj = "apples"
        x = Str(_append, buf, obj=obj)
        self.assertEqual(buf, [])
        # Invoke Lazy Func
        one = x()
        self.assertEqual(one, "1")
        self.assertEqual(buf, [obj])
        # Verify result was cached
        also_one = x()
        self.assertEqual(also_one, "1")
        self.assertEqual(buf, [obj])

    def test_str(self) -> None:
        buf: list[str] = []
        obj = "apples"
        x = Str(_append, buf, obj=obj)
        self.assertEqual(buf, [])
        # Invoke Lazy Str
        one = str(x)
        self.assertEqual(one, "1")
        self.assertEqual(buf, [obj])


if __name__ == "__main__":
    unittest.main()
