# pylint: disable=missing-module-docstring,missing-class-docstring,missing-function-docstring
from collections.abc import Callable, Iterator
from dataclasses import dataclass, field
from threading import Thread, get_ident
from contextlib import contextmanager
import multiprocessing as mp
from typing import Any
import traceback
import unittest
import pickle  # nosec B403
import time
import sys
import os

from zstdlib.keyed_instance import KeyedInstanceProcessError
from zstdlib import CircularConstructionError, KeyedInstance


class Nop:
    def __init__(self, key: int, *_: object) -> None:
        self.key = key


# For test cases involving forking


def nop() -> None:
    pass


@contextmanager
def try_do(name: str, q: mp.Queue[str]) -> Iterator[None]:
    try:
        yield
    except KeyedInstanceProcessError:
        q.put("KIPE")
    except Exception as e:  # noqa: BLE001
        traceback.print_exc()
        q.put(f"{e.__class__.__name__}: {e.args[0]}")
    else:
        q.put(name)


def subprocess_fn(q: mp.Queue[str]) -> None:
    def test4() -> None:
        with try_do("os.fork", q):
            if not os.fork():  # Child dies
                sys.exit(0)
        for i in ("fork", "spawn"):
            with try_do(f"mp.{i}", q):
                p = mp.get_context(i).Process(target=nop)  # type: ignore[attr-defined]
                p.start()
                p.join(1)
                if p.is_alive():
                    p.kill()
                    raise RuntimeError("Process had to be killed")

    # Multiprocessing is allowed right now, these should work
    test4()

    # Define a subclass
    class Foo(KeyedInstance, Nop):
        pass

    # No instances yet, still ok
    test4()
    _ = Foo(1)

    # This should fail, except spawn
    test4()


# Main test cases


class TestKeyedInstance(unittest.TestCase):

    def test_subclass(self) -> None:

        class Foo(KeyedInstance, Nop):
            pass

        class Sup:
            pass

        with self.assertRaises(TypeError):

            class Bar1(Sup, Foo):
                pass

        with self.assertRaises(TypeError):

            class Bar2(Foo, Sup):
                pass

    def test_key(self) -> None:

        class Foo(KeyedInstance, Nop):
            pass

        class Bar(KeyedInstance, Nop):
            pass

        a1_1 = Foo(1)
        a1_2 = Foo(1)
        a1_3 = Foo(1, 6)
        a2_1 = Foo(2)
        b1_1 = Bar(1)
        b1_2 = Bar(1)

        self.assertIs(a1_1, a1_2)
        self.assertIs(a1_1, a1_3)
        self.assertIs(b1_1, b1_2)
        self.assertIsNot(a1_1, a2_1)
        self.assertIsNot(a1_1, b1_1)

    def test_circular(self) -> None:

        class ToZero(KeyedInstance):
            def __init__(self, x: int) -> None:
                assert 0 <= x < 10
                if x > 0:
                    _ = type(self)(x - 1)

        _ = ToZero(6)

        class Crazy(KeyedInstance):
            def __init__(self, b: bool) -> None:
                self.same = type(self)(b)  # Father is self, circle

        with self.assertRaises(CircularConstructionError):
            _ = Crazy(True)

        class Crazy2(KeyedInstance):
            def __init__(self, b: bool) -> None:
                self.inverse = type(self)(not b)  # Grandfather is self

        with self.assertRaises(CircularConstructionError):
            _ = Crazy2(True)

    def test_multiproc(self) -> None:

        class Foo(KeyedInstance, Nop):
            pass

        foo1 = Foo(1)
        with self.assertRaises(TypeError):
            _ = pickle.dumps(foo1)

        # Run tests
        q: mp.Queue[str] = mp.Queue()
        p = mp.get_context("spawn").Process(target=subprocess_fn, args=(q,))
        p.start()
        p.join(10)  # This should be rather instant, this is generous
        alive = p.is_alive()
        time.sleep(0.1)  # Let everything flush to the queue, just in case
        q.put("Alive" if alive else "Dead")
        if alive:
            p.kill()
        q.put(str(p.exitcode))
        fin = "queue done, shutdown"
        q.put(fin)  # Better than relying on Empty b/c queue pipe / caches aren't instant
        time.sleep(0.1)  # Let everything flush to the queue, just in case

        # Check results
        results: list[str] = []
        while not results or results[-1] != fin:
            results.append(q.get(timeout=3))  # Should be done nearly instantly
        expected: list[str] = ["os.fork", "mp.fork", "mp.spawn"] * 2
        expected += ["KIPE", "KIPE", "mp.spawn", "Dead", "0", fin]
        self.assertEqual(results, expected)

    def test_interthread(self) -> None:

        scale: int = 4  # Higher runs faster, lower is more accurate
        actions: list[Action] = []
        type RV_T = C1 | C2 | Exception

        @dataclass(frozen=True)
        class Action:
            msg: str
            tid: int = field(default_factory=lambda: get_ident())
            ts: float = field(default_factory=lambda: time.monotonic())

            @staticmethod
            def strs(x: list[Action]) -> list[str]:
                start = x[0].ts
                tids = list({i.tid for i in x})
                return [f"{round(scale*(i.ts-start))} | Thread-{tids.index(i.tid)+1} | {i.msg}" for i in x]

        def save_results(fn: Callable[[], C1 | C2], ret: list[RV_T]) -> None:
            try:
                ret.append(fn())
            except Exception as e:  # noqa: BLE001
                ret.append(e)

        def dispatch_functions(*fns: Callable[[], RV_T]) -> list[RV_T]:
            assert fns
            rv: list[list[RV_T]] = [[] for i in fns]
            ts = [Thread(target=lambda y=i, z=k: save_results(y, z), daemon=True) for i, k in zip(fns, rv)]
            for t in ts:
                t.start()
                time.sleep(2 / scale / len(fns))
            end = time.monotonic() + 10  # Generous timeout
            for t in ts:
                t.join(max(0, end - time.monotonic()))
            if any(i.is_alive() for i in ts):
                raise RuntimeError("Threads did not die")
            if any(len(i) != 1 for i in rv):
                raise ValueError("dispatch_functions failed")
            return [i[0] for i in rv]

        class _Body:
            def _init(self, other: type[C1 | C2], key: int, *nxt: int) -> Any:
                name = f"{self.__class__.__name__}({key}), next={list(nxt)}"
                actions.append(Action(f"{name} - start"))
                time.sleep(2 / scale)
                second = f"{other.__name__}({nxt[0]})" if nxt else "None"
                try:
                    actions.append(Action(f"{name} - requesting {second}"))
                    if nxt:
                        _ = other(*nxt)
                except:
                    actions.append(Action(f"{name} - err: {second}"))
                    raise
                actions.append(Action(f"{name} - done"))

        class C1(KeyedInstance, _Body):
            def __init__(self, key: int, *nxt: int) -> None:
                self._init(C2, key, *nxt)

        class C2(KeyedInstance, _Body):
            def __init__(self, key: int, *nxt: int) -> None:
                self._init(C1, key, *nxt)

        # Test circular dependency between threads
        fail1, fail2 = dispatch_functions(lambda: C1(0, 0, 0), lambda: C2(0, 0))
        expected: list[str] = [
            "0 | Thread-1 | C1(0), next=[0, 0] - start",
            "1 | Thread-2 | C2(0), next=[0] - start",
            "2 | Thread-1 | C1(0), next=[0, 0] - requesting C2(0)",  # Blocked by Thread-2
            "3 | Thread-2 | C2(0), next=[0] - requesting C1(0)",  # C2(0):T2 -> C1(0):T1 -> C2(0):T2, err
            "3 | Thread-2 | C2(0), next=[0] - err: C1(0)",  # T2 dies, releases C2(0)
            "3 | Thread-1 | C2(0), next=[0] - start",  # C1(0):T1 -> C2(0):T2 , ok
            "5 | Thread-1 | C2(0), next=[0] - requesting C1(0)",  # C1(0):T1 -> C2(0):T2 -> C1(0):T1, err
            "5 | Thread-1 | C2(0), next=[0] - err: C1(0)",  # T1 dies, releases C1(0)
            "5 | Thread-1 | C1(0), next=[0, 0] - err: C2(0)",  # release C2(0)
        ]
        self.assertEqual(Action.strs(actions), expected)
        self.assertIsInstance(fail1, CircularConstructionError)
        self.assertIsInstance(fail2, CircularConstructionError)
        self.assertIsNot(fail1, fail2)

        # Test simultaneous construction
        actions.clear()
        res = dispatch_functions(*[lambda i2=i: (C1, C2)[i2 % 2](i2 * 10, i2 * 10 + 1) for i in range(1, 4)])
        expected = [
            "0 | Thread-1 | C2(10), next=[11] - start",
            "1 | Thread-2 | C1(20), next=[21] - start",
            "1 | Thread-3 | C2(30), next=[31] - start",
            "2 | Thread-1 | C2(10), next=[11] - requesting C1(11)",
            "2 | Thread-1 | C1(11), next=[] - start",
            "3 | Thread-2 | C1(20), next=[21] - requesting C2(21)",
            "3 | Thread-2 | C2(21), next=[] - start",
            "3 | Thread-3 | C2(30), next=[31] - requesting C1(31)",
            "3 | Thread-3 | C1(31), next=[] - start",
            "4 | Thread-1 | C1(11), next=[] - requesting None",
            "4 | Thread-1 | C1(11), next=[] - done",
            "4 | Thread-1 | C2(10), next=[11] - done",
            "5 | Thread-2 | C2(21), next=[] - requesting None",
            "5 | Thread-2 | C2(21), next=[] - done",
            "5 | Thread-2 | C1(20), next=[21] - done",
            "5 | Thread-3 | C1(31), next=[] - requesting None",
            "5 | Thread-3 | C1(31), next=[] - done",
            "5 | Thread-3 | C2(30), next=[31] - done",
        ]
        self.assertEqual(Action.strs(actions), expected)
        for itr, i in enumerate(res):
            self.assertIsInstance(i, (C2, C1)[itr % 2])

        # Test dependent construction time
        actions.clear()
        rv1, rv2 = dispatch_functions(lambda: C1(0, 0), lambda: C2(0, 10, 20))
        expected = [
            "0 | Thread-1 | C1(0), next=[0] - start",
            "1 | Thread-2 | C2(0), next=[10, 20] - start",
            "2 | Thread-1 | C1(0), next=[0] - requesting C2(0)",  # Wait until C2(0):T2 is one
            "3 | Thread-2 | C2(0), next=[10, 20] - requesting C1(10)",
            "3 | Thread-2 | C1(10), next=[20] - start",
            "5 | Thread-2 | C1(10), next=[20] - requesting C2(20)",
            "5 | Thread-2 | C2(20), next=[] - start",
            "7 | Thread-2 | C2(20), next=[] - requesting None",
            "7 | Thread-2 | C2(20), next=[] - done",  # Release C2(0)
            "7 | Thread-2 | C1(10), next=[20] - done",
            "7 | Thread-2 | C2(0), next=[10, 20] - done",
            "7 | Thread-1 | C1(0), next=[0] - done",
        ]
        self.assertEqual(Action.strs(actions), expected)
        self.assertIs(rv1, C1(0))
        self.assertIs(rv2, C2(0))


if __name__ == "__main__":
    unittest.main()
