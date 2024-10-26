# pylint: disable=missing-module-docstring,missing-class-docstring,missing-function-docstring,unused-variable
from threading import Thread, Lock
from time import sleep
import unittest

from zstdlib.singleton import SingletonType, Singleton


class TestSingletonType(unittest.TestCase):

    def test_valid(self) -> None:
        class ST1(metaclass=SingletonType):
            pass

        self.assertIs(ST1(), ST1())

        class ST2(metaclass=SingletonType):
            pass

        self.assertIsNot(ST1(), ST2())

    def test_subclass(self) -> None:
        class ST3(metaclass=SingletonType):
            pass

        with self.assertRaises(TypeError):

            class ST4(ST3):
                pass

    def test_multi_thread(self):
        """
        Ensure that SingletonType is thread safe and that constructing an object doesn't delay other threads
        Technically this is more of a heuristic, but it failing is extremely unlikely
        """

        class ST5(metaclass=SingletonType):
            def __init__(self):
                sleep(0.2)

        class ST6(metaclass=SingletonType):
            def __init__(self):
                sleep(0.8)

        lock = Lock()
        events = []
        results = []

        def t1() -> None:
            """
            Construct an ST6 immediately
            """
            with lock:
                pass
            events.append("START: ST6()")
            results.append(ST6())
            events.append("END: ST6()")

        def t2() -> None:
            """
            Construct an ST6 after the first ST6 has started construction but before it has finished
            """
            with lock:
                pass
            sleep(0.2)
            events.append("START: ST6()")
            results.append(ST6())
            events.append("END: ST6()")

        def t3() -> None:
            """
            Construct ST5's after both ST6s have started construction, finishing before either end
            """
            with lock:
                pass
            sleep(0.4)
            # Loop Enough times that ST6 wil be complete if it ST5 actually constructed each time
            for i in range(10):
                events.append("START: ST5()")
                results.append(ST5())
                events.append("END: ST5()")

        threads = (Thread(target=t1), Thread(target=t2), Thread(target=t3))
        with lock:
            for i in threads:
                i.start()
            # Give threads a moment to construct then let them go
            sleep(0.2)
        for i in threads:
            i.join()
        # Check results
        wanted = ["START: ST6()"] * 2 + ["START: ST5()", "END: ST5()"] * 10 + ["END: ST6()"] * 2
        self.assertEqual(events, wanted)
        # Check constructed objects
        self.assertEqual(len(results), 2 + 10)
        for i in range(9):
            self.assertIs(results[0], results[i + 1])
        self.assertIsNot(results[0], results[-1])
        self.assertIs(results[-1], results[-2])


class TestSingleton(unittest.TestCase):

    def test_valid(self):
        class S1(Singleton):
            pass

        self.assertIs(S1(), S1())

        class S2(Singleton):
            pass

        self.assertIsNot(S1(), S2())

    def test_subclass(self):
        class S3(Singleton):
            pass

        with self.assertRaises(TypeError):

            class S4(S3):
                pass


if __name__ == "__main__":
    unittest.main()
