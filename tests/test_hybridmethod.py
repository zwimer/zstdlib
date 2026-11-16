# pylint: disable=missing-module-docstring,missing-class-docstring,missing-function-docstring,unused-variable
from typing import ClassVar
import unittest

from zstdlib import hybridmethod


class TestHybridMethod(unittest.TestCase):

    def test_hybridmethod(self) -> None:

        class A:
            objs: ClassVar[dict[int, A]] = {}

            def __init__(self, x: int) -> None:
                self.x: int = x
                self.objs[x] = self

            @hybridmethod
            def get(self: A | None, cls: type[A], *, x: int | None = None) -> A:
                if x is not None:
                    return cls.objs[x]
                if self is None:
                    raise TypeError("Unable to determine x")
                return cls.objs[self.x]

        a = A(1)
        b = A(2)
        self.assertIsNot(a, b)
        self.assertIs(a.get(), a)
        self.assertIs(A.get(x=2), b)
        with self.assertRaises(TypeError):
            A.get()

    def test_metadata(self) -> None:

        class A:

            @hybridmethod
            def foo(self: A | None, cls: type[A]) -> None:
                """hi"""

            foo2 = foo

            @staticmethod
            def bar(self: A | None, cls: type[A]) -> None:  # noqa: PLW0211
                """hi2"""

            baz = hybridmethod(bar)
            baz2 = baz

        a = A()
        self.assertEqual(A.foo.__doc__, "hi")
        self.assertEqual(a.foo.__doc__, "hi")
        self.assertEqual(A.bar.__doc__, "hi2")
        self.assertEqual(a.bar.__doc__, "hi2")
        self.assertEqual(A.baz.__doc__, "hi2")
        self.assertEqual(a.baz.__doc__, "hi2")

        def qn_a(x: str) -> str:
            return f"{self.__class__.__qualname__}.test_metadata.<locals>.A.{x}"

        self.assertEqual(A.foo.__name__, "foo")
        self.assertEqual(a.foo.__name__, "foo")
        self.assertEqual(A.foo.__qualname__, qn_a("foo"))
        self.assertEqual(a.foo.__qualname__, qn_a("foo"))

        self.assertEqual(A.foo2.__name__, "foo")
        self.assertEqual(a.foo2.__name__, "foo")
        self.assertEqual(A.foo2.__qualname__, qn_a("foo"))
        self.assertEqual(a.foo2.__qualname__, qn_a("foo"))

        self.assertEqual(A.bar.__name__, "bar")
        self.assertEqual(a.bar.__name__, "bar")
        self.assertEqual(A.bar.__qualname__, qn_a("bar"))
        self.assertEqual(a.bar.__qualname__, qn_a("bar"))

        self.assertEqual(A.baz.__name__, "baz")
        self.assertEqual(a.baz.__name__, "baz")
        self.assertEqual(A.baz.__qualname__, qn_a("baz"))
        self.assertEqual(a.baz.__qualname__, qn_a("baz"))

        self.assertEqual(A.baz2.__name__, "baz")

        class B(A):
            pass

        b = B()
        self.assertEqual(B.baz.__name__, "baz")
        self.assertEqual(b.baz.__name__, "baz")


if __name__ == "__main__":
    unittest.main()
