# pylint: disable=missing-module-docstring,missing-class-docstring,missing-function-docstring
from pathlib import Path
import unittest
import os

from zstdlib import normpath


class TestUtil(unittest.TestCase):

    def test_normpath(self) -> None:
        tests_raw = {
            "": ".",
            "/": "/",
            "/a/": "/a",
            "/a/..": "/",
            "/a/../": "/",
            "/a/b/..": "/a",
            "/a/b/../": "/a",
            "/a//b": "/a/b",
            "/a//b/": "/a/b",
            "c": "c",
            "c//d///": "c/d",
        }
        res = [(k, os.path.normpath(i), normpath(Path(i))) for i, k in tests_raw.items()]
        for want, os_np, np in res:
            self.assertEqual(want, os_np)
            self.assertEqual(Path(want), np)


if __name__ == "__main__":
    unittest.main()
