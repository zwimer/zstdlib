# pylint: disable=missing-module-docstring,missing-class-docstring,missing-function-docstring
from types import TracebackType
from typing import Never
import traceback
import unittest
import sys

from zstdlib.exc import PopFrames


def _tbl(o: BaseException | TracebackType | None) -> int:
    if isinstance(o, BaseException):
        return _tbl(o.__traceback__)
    return 0 if o is None else (1 + _tbl(o.tb_next))


def _do_exc(n: int, n2: int, *, active: bool = False, pop: bool = True) -> tuple[int, TracebackType | None]:
    def foo() -> Never:
        raise IndexError()

    def bar() -> Never:
        foo()

    def baz() -> Never:
        bar()

    try:
        if active or not pop:
            baz()
        with PopFrames(n, furthest_n=n2):
            baz()
    except IndexError as e:
        if active:
            PopFrames.active(n, furthest_n=n2, reraise=False)
        return _tbl(e), e.__traceback__


class TestPopFrames(unittest.TestCase):

    def test_sanity(self) -> None:
        try:
            raise IndexError()
        except IndexError:
            e = sys.exc_info()
            self.assertIsNot(e[2], None)
            assert e[1] is not None
            self.assertIs(e[1].__traceback__, e[2])
            e[1].__traceback__ = None
            e = sys.exc_info()
            self.assertIs(e[2], None)
            assert e[1] is not None
            self.assertIs(e[1].__traceback__, e[2])

    def test_usage(self) -> None:
        with self.assertRaises(TypeError):
            _ = PopFrames(1.0)  # type: ignore[arg-type]
        with self.assertRaises(ValueError):
            PopFrames(n=-1)
        with self.assertRaises(ValueError):
            PopFrames(furthest_n=-1)
        _ = PopFrames(0)

    def test_modify_and_cm(self) -> None:

        # nop
        with PopFrames(10):
            pass

        # Ensure correct amounts are cut off
        baseline = _do_exc(0, 0, pop=False)[0]
        self.assertEqual(baseline, 4)
        self.assertEqual(_do_exc(0, 0)[0], baseline)
        self.assertEqual(_do_exc(1, 0)[0], baseline - 1)
        self.assertEqual(_do_exc(0, 1)[0], baseline - 1)
        self.assertEqual(_do_exc(1, 1)[0], baseline - 2)
        self.assertEqual(_do_exc(2**30, 2**30)[0], 0)

        # Ensure correct directions are cut
        normal = "\n".join(traceback.format_tb(_do_exc(0, 0)[1]))
        tb_no_inner = "\n".join(traceback.format_tb(_do_exc(1, 0)[1]))
        self.assertNotEqual(normal, tb_no_inner)
        self.assertTrue(normal.startswith(tb_no_inner))
        tb_no_outer = "\n".join(traceback.format_tb(_do_exc(0, 1)[1]))
        self.assertTrue(normal.endswith(tb_no_outer))
        self.assertNotEqual(normal, tb_no_outer)

    def test_active(self) -> None:

        # not active
        with self.assertRaises(RuntimeError):
            PopFrames.active(0, reraise=False)
        # reraise
        with self.assertRaises(OSError):
            try:
                raise OSError()
            except OSError:
                PopFrames.active(0, reraise=True)
        # passthrough
        baseline = _do_exc(0, 0, pop=False)[0]
        self.assertEqual(baseline, 4)
        self.assertEqual(_do_exc(0, 0)[0], baseline)
        self.assertEqual(_do_exc(1, 1)[0], baseline - 2)


if __name__ == "__main__":
    unittest.main()
