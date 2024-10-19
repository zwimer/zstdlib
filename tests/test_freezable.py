# pylint: disable=missing-module-docstring,missing-class-docstring,missing-function-docstring,unused-variable,attribute-defined-outside-init
import unittest

from zstdlib.freezable import Freezable


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
        f1.freeze(permanent=True)
        self.assertEqual(f1.a, 1)
        with self.assertRaises(RuntimeError):
            f1.thaw()
        with self.assertRaises(AttributeError):
            f1.a = 1


if __name__ == "__main__":
    unittest.main()
