# pylint: disable=missing-module-docstring,missing-class-docstring,missing-function-docstring,unused-variable
import unittest

from zstdlib.enum import EnumType, Enum


class TestEnumType(unittest.TestCase):

    def test_valid(self) -> None:
        class ET1(metaclass=EnumType):
            arg1: int = 0
            arg2: int = 1

    def test_empty(self) -> None:
        class ET2(metaclass=EnumType, empty_ok=True):
            pass

        with self.assertRaises(ValueError):

            class ET3(metaclass=EnumType):
                pass

    def test_dupe(self) -> None:
        with self.assertRaises(ValueError):

            class ET4(metaclass=EnumType):
                arg1: int = 0
                arg2: int = 0

    def test_annotations(self) -> None:
        with self.assertRaises(ValueError):

            class ET5(metaclass=EnumType):
                arg1 = 1

        with self.assertRaises(ValueError):

            class ET6(metaclass=EnumType):
                arg1: int

        with self.assertRaises(TypeError):

            class ET7(metaclass=EnumType):
                arg1: str = 0  # type: ignore[assignment]

    def test_instantiation(self) -> None:
        with self.assertRaises(AttributeError):

            class ET8(metaclass=EnumType):
                arg1: int = 1

                def __init__(self):
                    pass

        with self.assertRaises(AttributeError):

            class ET9(metaclass=EnumType):
                arg1: int = 1

                def __new__(cls):
                    pass

        class ET10(metaclass=EnumType):
            arg1: int = 0

        with self.assertRaises(TypeError):
            ET10()
        with self.assertRaises(TypeError):
            ET10.__init__({})


class TestEnum(unittest.TestCase):
    def test_valid(self) -> None:
        class E1(Enum):
            arg1: int = 0
            arg2: int = 1

    def test_empty(self) -> None:
        class E2(Enum, empty_ok=True):
            pass

        with self.assertRaises(ValueError):

            class E3(Enum):
                pass

    def test_dupe(self) -> None:
        with self.assertRaises(ValueError):

            class E4(Enum):
                arg1: int = 0
                arg2: int = 0

    def test_annotations(self) -> None:
        with self.assertRaises(ValueError):

            class E5(Enum):
                arg1 = 1

        with self.assertRaises(ValueError):

            class E6(Enum):
                arg1: int

        with self.assertRaises(TypeError):

            class E7(Enum):
                arg1: str = 0  # type: ignore[assignment]

    def test_instantiation(self) -> None:
        with self.assertRaises(AttributeError):

            class E8(Enum):
                arg1: int = 1

                def __init__(self):
                    pass

        with self.assertRaises(AttributeError):

            class E9(Enum):
                arg1: int = 1

                def __new__(cls):
                    pass

        class E10(Enum):
            arg1: int = 0

        with self.assertRaises(TypeError):
            E10()
        with self.assertRaises(TypeError):
            E10.__init__({})


if __name__ == "__main__":
    unittest.main()
