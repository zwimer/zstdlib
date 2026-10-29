# pylint: disable=missing-module-docstring,missing-class-docstring,missing-function-docstring
import unittest

from zstdlib import ExcCapture, ExcDelay


class TestLazy(unittest.TestCase):

    def test_capture(self) -> None:
        # Capture nothing
        rt = ExcCapture(RuntimeError)
        with rt.capture():
            pass
        self.assertEqual(len(rt.errors), 0)
        # Capture only Runtime
        with rt.capture():
            raise RuntimeError()
        self.assertEqual(len(rt.errors), 1)
        with self.assertRaises(ValueError), rt.capture():
            raise ValueError()
        self.assertEqual(len(rt.errors), 1)
        # previous
        with rt.capture():
            pass
        self.assertIs(rt.previous, None)
        test_err = RuntimeError("test")
        with rt.capture():
            raise test_err
        self.assertEqual(rt.previous, test_err)
        # capture's exc_t
        rt = ExcCapture(RuntimeError)
        with self.assertRaises(RuntimeError), rt.capture(ValueError):
            raise RuntimeError()
        self.assertEqual(len(rt.errors), 0)
        with rt.capture(ValueError):
            raise ValueError()
        self.assertEqual(len(rt.errors), 1)
        del rt
        # exc_t = None
        non = ExcCapture()
        with self.assertRaises(RuntimeError), non.capture(ValueError):
            raise RuntimeError()
        self.assertEqual(len(non.errors), 0)
        with self.assertRaises(ValueError), non.capture():
            pass
        self.assertEqual(len(non.errors), 0)
        with non.capture(RuntimeError):
            raise RuntimeError()
        self.assertEqual(len(non.errors), 1)

    def test_delay(self) -> None:
        # No raise
        with ExcDelay("msg", RuntimeError) as capture, capture():
            pass
        # Raise
        ed = ExcDelay("msg", RuntimeError)
        try:
            with ed as capture:
                with capture():
                    raise RuntimeError()
                with capture():
                    raise RuntimeError()
            self.assertTrue(False)
        except BaseExceptionGroup as grp:
            self.assertIsInstance(grp, ExceptionGroup)  # Test auto-conversion
            self.assertEqual(len(grp.exceptions), 2)
            self.assertEqual(len(ed.errors), 2)
        # No block error
        with self.assertRaises(ValueError), ExcDelay("msg", RuntimeError) as capture, capture():
            raise ValueError()
        with self.assertRaises(ValueError), ExcDelay("msg", RuntimeError) as capture:
            with capture():
                raise RuntimeError()
            raise ValueError()
        # msg
        _ = ExcDelay("")
        with self.assertRaises(TypeError):
            ExcDelay(RuntimeError)  # type: ignore[arg-type]
        # armed
        with ExcDelay("", RuntimeError, armed=False) as capture, capture():
            raise RuntimeError()
        with ExcDelay("", RuntimeError, armed=True) as capture, capture():
            capture.armed = False
            raise RuntimeError()
        with self.assertRaises(ExceptionGroup), ExcDelay("", RuntimeError, armed=True) as capture, capture():
            raise RuntimeError()


if __name__ == "__main__":
    unittest.main()
