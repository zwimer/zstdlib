# pylint: disable=missing-module-docstring,missing-class-docstring,missing-function-docstring
from types import TracebackType
import traceback
import unittest

from zstdlib.exc import raise_


def _tbl(o: BaseException | TracebackType | None) -> int:
    if isinstance(o, BaseException):
        return _tbl(o.__traceback__)
    return 0 if o is None else (1 + _tbl(o.tb_next))


class TestRaise(unittest.TestCase):

    def test_sanity(self) -> None:

        raise_me = OSError("test")
        self.assertFalse(raise_me.__suppress_context__)
        self.assertIs(raise_me.__context__, None)
        self.assertIs(raise_me.__cause__, None)

        # no from
        try:
            raise raise_me
        except type(raise_me) as e:
            self.assertIs(e, raise_me)
            self.assertIs(raise_me.__cause__, None)
            self.assertIs(raise_me.__context__, None)
            self.assertFalse(raise_me.__suppress_context__)

        # from None
        try:
            try:
                raise IndexError()
            except IndexError:
                raise raise_me
        except type(raise_me):
            self.assertFalse(raise_me.__suppress_context__)
            self.assertIsNot(raise_me.__context__, None)
            self.assertIs(raise_me.__cause__, None)

        # from e
        raise_me = OSError("test")
        cause = IndexError()
        try:
            try:
                raise cause
            except IndexError as e:
                raise raise_me from e
        except type(raise_me):
            self.assertIs(raise_me.__cause__, cause)
            self.assertIsNot(raise_me.__context__, None)
            self.assertTrue(raise_me.__suppress_context__)

    def test_raise_no_from(self) -> None:

        tb_lengths: set[int] = set()
        for itr in range(2):
            raise_me = OSError("test")
            try:
                if itr:
                    raise_(raise_me)
                else:
                    raise raise_me
            except type(raise_me) as e:
                self.assertIs(e, raise_me)
                self.assertIs(raise_me.__cause__, None)
                self.assertIs(raise_me.__context__, None)
                self.assertFalse(raise_me.__suppress_context__)
                tb_lengths.add(_tbl(e))
        self.assertEqual(len(tb_lengths), 1)

    def test_raise_from_none(self) -> None:

        tb_lengths: set[int] = set()
        for itr in range(2):
            raise_me = OSError("test")
            try:
                if itr:
                    raise_(raise_me, None)
                else:
                    raise raise_me from None
            except type(raise_me) as e:
                self.assertIs(e, raise_me)
                self.assertIs(raise_me.__cause__, None)
                self.assertIs(raise_me.__context__, None)
                self.assertTrue(raise_me.__suppress_context__)
                tb_lengths.add(_tbl(e))
        self.assertEqual(len(tb_lengths), 1)

    def test_raise_from_e(self) -> None:

        tb_lengths: set[int] = set()
        for itr in range(2):
            raise_me = OSError("test")
            from_ = IndexError("test2")
            try:
                try:
                    raise from_
                except type(from_) as e:
                    if itr:
                        raise_(raise_me, e)
                    else:
                        raise raise_me from e
            except type(raise_me) as e:
                self.assertIs(e, raise_me)
                self.assertIs(raise_me.__cause__, from_)
                self.assertIs(raise_me.__context__, from_)
                self.assertTrue(raise_me.__suppress_context__)
                tb_lengths.add(_tbl(e))
        self.assertEqual(len(tb_lengths), 1)

    def test_tb(self) -> None:

        # Verify the traceback shows the initial raise at raise_
        line = "raise_(IndexError())  # this comment is required"
        try:
            raise_(IndexError())  # this comment is required
        except IndexError as e:
            tb = e.__traceback__
        self.assertTrue(line in traceback.format_tb(tb)[-1])


if __name__ == "__main__":
    unittest.main()
