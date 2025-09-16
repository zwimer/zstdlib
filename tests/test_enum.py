# pylint: disable=missing-module-docstring,missing-class-docstring,missing-function-docstring,unused-variable
import unittest

from zstdlib.enum import EnumType, Enum, entries, values, auto


class TestEnumType(unittest.TestCase):

    def test_valid(self) -> None:
        class ET1(metaclass=EnumType):
            arg1: int = 0
            arg2: int = 1

    def test_empty(self) -> None:
        class ET1(metaclass=EnumType, empty_ok=True):
            pass

        with self.assertRaises(ValueError):

            class ET2(metaclass=EnumType):
                pass

    def test_dupes(self) -> None:
        class ET1(metaclass=EnumType, dupes_ok=True):
            a: int = 5
            b: int = 5
            c: dict = {}

        with self.assertRaises(ValueError):

            class ET2(metaclass=EnumType):
                a: int = 5
                b: int = 5

        with self.assertRaises(TypeError):

            class ET3(metaclass=EnumType):
                a: dict = {}

    def test_type_check(self) -> None:
        class ET1(metaclass=EnumType, type_check=set()):
            a: str = 5  # type: ignore[assignment]

        with self.assertRaises(TypeError):

            class ET2(metaclass=EnumType):
                a: str = 5  # type: ignore[assignment]

    def test_annotations(self) -> None:
        with self.assertRaises(ValueError):

            class ET1(metaclass=EnumType):
                arg1 = 1

        with self.assertRaises(ValueError):

            class ET2(metaclass=EnumType):
                arg1: int

    def test_instantiation(self) -> None:
        with self.assertRaises(AttributeError):

            class ET1(metaclass=EnumType):
                arg1: int = 1

                def __init__(self):
                    pass

        with self.assertRaises(AttributeError):

            class ET2(metaclass=EnumType):
                arg1: int = 1

                def __new__(cls):
                    pass

        class ET3(metaclass=EnumType):
            arg1: int = 0

        with self.assertRaises(TypeError):
            ET3()

        with self.assertRaises(TypeError):
            ET3.__new__({})  # type: ignore[arg-type]

    def test_iter(self) -> None:

        class ET11(metaclass=EnumType):
            arg1: int = 0
            arg2: str = "1"

        self.assertEqual(tuple(ET11), ("arg1", "arg2"))

    def test_auto(self) -> None:

        class ET1(metaclass=EnumType):
            arg1: int = 0
            arg2 = auto
            arg3 = auto

        self.assertEqual(3, len(set(values(ET1))))

        with self.assertRaises(TypeError):

            class ET2(metaclass=EnumType):
                arg1: int = 0
                arg2: str = auto  # type: ignore[assignment]


class TestEnum(unittest.TestCase):

    def test_is(self) -> None:
        self.assertIsInstance(Enum, EnumType)


class TestFunctions(unittest.TestCase):
    def test_entries(self) -> None:
        class E1(Enum):
            arg1: int = 0
            arg2: str = "1"

        self.assertEqual(entries(E1), {"arg1": (int, 0), "arg2": (str, "1")})

    def test_values(self) -> None:
        class E1(Enum):
            arg1: int = 0
            arg2: str = "1"

        self.assertEqual(values(E1), (0, "1"))


if __name__ == "__main__":
    unittest.main()
