# pylint: disable=missing-module-docstring,missing-class-docstring,missing-function-docstring
import unittest
import logging

from zstdlib.log import trace

from .base import LeftBase


# mypy: disable_error_code="attr-defined"
class TestTrace(LeftBase, unittest.TestCase):

    def test_trace(self) -> None:
        """
        Avoid splitting up into multiple functions since trace.install() affects global state
        Keeping this as one function ensures that the tests are run in order
        """
        # Test bad installs
        with self.assertRaises(ValueError):
            trace.install(value=-1)
        with self.assertRaises(ValueError):
            trace.install(value=logging.DEBUG + 1)
        logging.TRACE = None
        with self.assertRaises(AttributeError):
            trace.install()
        del logging.TRACE
        logging.trace = None
        with self.assertRaises(AttributeError):
            trace.install()
        del logging.trace
        logging.getLoggerClass().trace = None
        with self.assertRaises(AttributeError):
            trace.install()
        del logging.getLoggerClass().trace
        trace._State.start = True  # pylint: disable=protected-access
        with self.assertRaises(RuntimeError):
            trace.install()
        trace._State.start = False  # pylint: disable=protected-access
        # Good install
        trace.install(value=5)
        # Attribute check
        self.assertTrue(hasattr(logging, "TRACE"))
        self.assertTrue(hasattr(logging, "trace"))
        self.assertTrue(hasattr(logging.getLogger(), "trace"))
        self.assertEqual(logging.TRACE, 5)
        self.assertEqual(logging.getLevelName(logging.TRACE), "TRACE")  # type: ignore[call-overload]
        # Root check
        with self.hijack("") as log:
            old = log.getEffectiveLevel()
            # pylint: disable=not-callable
            logging.trace("test1")  # type: ignore[misc]
            log.setLevel(logging.DEBUG)
            # pylint: disable=not-callable
            logging.trace("test2")  # type: ignore[misc]
            log.setLevel(old)
        self.assertEqual(self.messages[log], ["test1"])
        # Logger check
        with self.hijack("TestTrace.t1") as log:
            old = log.getEffectiveLevel()
            # pylint: disable=not-callable
            log.trace("test3")
            log.setLevel(logging.DEBUG)
            # pylint: disable=not-callable
            log.trace("test4")
            log.setLevel(old)
        self.assertEqual(self.messages[log], ["test3"])
        # Test re-installation
        with self.assertRaises(RuntimeError):
            trace.install(value=5)
        trace.install(value=5, force=True)


if __name__ == "__main__":
    unittest.main()
