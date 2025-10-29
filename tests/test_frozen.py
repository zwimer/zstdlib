# pylint: disable=missing-module-docstring,missing-class-docstring,missing-function-docstring,unused-variable,attribute-defined-outside-init
from sys import version_info
import unittest

from zstdlib.frozen import Freezable, frozen


class TestFreezable(unittest.TestCase):

    def test_unfrozen(self):
        class F1(Freezable):
            pass

        f1 = F1()
        f1.a = 1
        self.assertEqual(f1.a, 1)
        del f1.a
        self.assertIs(getattr(f1, "a", None), None)

    def test_frozen(self):
        class F1(Freezable):
            pass

        f1 = F1()
        f1.a = 1
        f1.freeze()
        self.assertEqual(f1.a, 1)
        with self.assertRaises(AttributeError):
            f1.a = 2
        with self.assertRaises(AttributeError):
            del f1.a
        f1.freeze()  # Should not raise an error

    def test_thaw(self):
        class F1(Freezable):
            pass

        f1 = F1()
        f1.a = 1
        f1.freeze()
        self.assertEqual(f1.a, 1)
        f1.thaw()
        f1.a = 2
        self.assertEqual(f1.a, 2)
        del f1.a
        self.assertIs(getattr(f1, "a", None), None)

    def test_permanent_freeze(self):
        class F1(Freezable):
            pass

        f1 = F1()
        f1.a = 1
        f1.freeze()  # To ensure that .freeze(permanent=True) works when already frozen too
        f1.freeze(permanent=True)
        f1.freeze(permanent=True)  # Should not raise an error
        self.assertEqual(f1.a, 1)
        with self.assertRaises(RuntimeError):
            f1.thaw()
        with self.assertRaises(AttributeError):
            f1.a = 1

    def test_properties(self):

        class F1(Freezable):
            pass

        f1 = F1()
        self.assertFalse(f1.frozen)
        self.assertTrue(f1.thawable)
        f1.freeze()
        self.assertTrue(f1.frozen)
        self.assertTrue(f1.thawable)
        f1.freeze(permanent=True)
        self.assertTrue(f1.frozen)
        self.assertFalse(f1.thawable)


class TestFrozen(unittest.TestCase):

    def test_frozen(self):
        @frozen
        class F1:
            def __init__(self):
                self.a = 1
                self.b = 1
                del self.b

        f1 = F1()
        self.assertEqual(f1.a, 1)
        self.assertIs(getattr(f1, "b", None), None)
        with self.assertRaises(AttributeError):
            f1.a = 1
        with self.assertRaises(AttributeError):
            del f1.a

    def test_metadata(self):
        @frozen
        class F1:
            def __init__(self, a: int = 1, *, b: bool = False) -> None:
                """
                init doc
                """

        f1 = F1()
        self.assertEqual(f1.__init__.__doc__.strip(), "init doc")
        self.assertEqual(f1.__init__.__name__, "__init__")
        self.assertEqual(f1.__init__.__qualname__, "TestFrozen.test_metadata.<locals>.F1.__init__")
        self.assertTupleEqual(f1.__init__.__defaults__, (1,))
        self.assertDictEqual(f1.__init__.__kwdefaults__, {"b": False})
        if version_info <= (3, 13) or hasattr(f1.__init__, "__annotations__"):
            self.assertDictEqual(f1.__init__.__annotations__, {"a": int, "b": bool, "return": None})
        else:  # annotations changed in 3.14, .__annotations__ *might* not exist
            from annotationlib import get_annotations

            self.assertDictEqual(get_annotations(f1.__init__), {"a": int, "b": bool, "return": None})

    def test_frozen_custom(self):
        @frozen("custom")
        class F1:
            def __init__(self):
                self.a = 1

            def custom(self):
                self.a = 2

        f1 = F1()
        self.assertEqual(f1.a, 1)
        f1.custom()
        self.assertEqual(f1.a, 2)
        with self.assertRaises(AttributeError):
            f1.a = 1


if __name__ == "__main__":
    unittest.main()
