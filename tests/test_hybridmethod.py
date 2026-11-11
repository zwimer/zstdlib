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


if __name__ == "__main__":
    unittest.main()
