# pylint: disable=missing-module-docstring,missing-class-docstring,missing-function-docstring,unused-variable
from collections.abc import Callable
from threading import Thread, Lock
from datetime import datetime
from time import sleep
import unittest

from zstdlib.singleton import NoInstanceError, Singleton


class TestSingleton(unittest.TestCase):

    def test_valid(self) -> None:
        class ST1(Singleton):
            pass

        class ST2(Singleton):
            pass

        self.assertIs(ST1(), ST1())
        self.assertIsNot(ST1(), ST2())

    def test_subclass(self) -> None:
        class ST1(Singleton):  # Ok to subtype Singleton base class
            pass

        with self.assertRaises(TypeError):  # Not ok to subtype a subtype of Singleton

            class ST2(ST1):
                pass

        with self.assertRaises(TypeError):  # Not ok to define __init_subclass__ in Singleton

            class ST3(Singleton):
                def __init_subclass__(cls, **kwargs):
                    pass

    def test_instance(self):
        class ST(Singleton):
            def __init__(self, _):
                pass

        self.assertTrue(issubclass(NoInstanceError, TypeError))
        with self.assertRaises(NoInstanceError):
            _ = ST.instance()
        obj = ST(0)
        self.assertIs(ST.instance(), obj)

        with self.assertRaises(TypeError):
            ST.instance(4)

    def test_multi_thread(self):
        """
        Ensure that Singleton is thread safe and that constructing an object doesn't delay other threads
        Technically this is more of a heuristic, but failing is extremely unlikely if this is thread safe
        Verifies that classes can construct concurrently, thread-safely, and only one instance is created
        """

        # Shared state for threads
        start = [datetime.now()]
        lock = Lock()
        events = []
        results = []

        # Helper functions that can help define thread tests
        timestamp = lambda: (datetime.now() - start[0]).total_seconds()

        def mk_cls(cls: type, name: str) -> None:
            fmt = lambda x: f"{timestamp():.1f}: {name} {x} {cls.__name__}()"
            events.append(fmt("->"))
            results.append(cls())
            events.append(fmt("<-"))

        def simple(name: str, cls: type, delay: float) -> Callable:
            def _t() -> None:
                with lock:  # Ensure all threads can start simultaneously
                    pass
                sleep(delay)
                mk_cls(cls, name)

            return _t

        # Run all functions
        def run_all(*funcs: Callable) -> None:
            ts = [Thread(target=i) for i in funcs]
            events.clear()
            results.clear()
            with lock:
                for i in ts:
                    i.start()
                # Give threads a moment to construct then let them go
                sleep(0.2)
                start[0] = datetime.now()
            for i in ts:
                i.join()

        # Verify concurrent construction of ST1 and ST2
        class Fast(Singleton):
            def __init__(self):
                sleep(0.3)

        class Slow(Singleton):
            def __init__(self):
                sleep(0.8)

        run_all(simple("f1", Slow, 0), simple("f2", Fast, 0.2))
        want = [
            "0.0: f1 -> Slow()",
            "0.2: f2 -> Fast()",
            "0.5: f2 <- Fast()",
            "0.8: f1 <- Slow()",
        ]
        self.assertEqual(want, events)
        self.assertEqual(len(results), 2)
        self.assertIs(results[0], Fast())
        self.assertIs(results[1], Slow())
        del Slow, Fast  # Cleanup, for safety

        # Verify that multiple threads constructing the same class only construct one object
        class ST(Singleton):
            first = True

            def __init__(self):
                if self.first:
                    self.first = False
                    sleep(0.4)

        run_all(simple("f1", ST, 0), simple("f2", ST, 0.2))
        self.assertEqual(len(events), 4)
        self.assertEqual(events[:2], ["0.0: f1 -> ST()", "0.2: f2 -> ST()"])
        # When the first thread's init finishes, the second will stop blocking and finish
        self.assertEqual(len(results), 2)
        for i in results:
            self.assertIs(i, ST())
        del ST  # Cleanup, for safety


if __name__ == "__main__":
    unittest.main()
