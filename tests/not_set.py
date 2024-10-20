import unittest

from zstdlib import NotSetType, NotSet


class TestNotSet(unittest.TestCase):
    def test_not_set(self):
        self.assertIsInstance(NotSetType, type)
        self.assertIsInstance(NotSet, NotSetType)
        self.assertIsNot(None, NotSet)
        self.assertIs(NotSet, NotSetType())


if __name__ == "__main__":
    unittest.main()
