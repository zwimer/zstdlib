# pylint: disable=missing-module-docstring,missing-class-docstring,missing-function-docstring,unused-variable
import unittest

from zstdlib.log import CuteFormatter
from zstdlib.ansi import Color

from .base import LeftBase


class TestCuteFormatter(LeftBase, unittest.TestCase):

    def test_hardcoded_colors(self) -> None:
        color = Color.strikethrough_green
        name = "TestCuteFormatter.test_hardcoded_colors"
        with self.hijack(name, fmt=CuteFormatter(colors={name: color})) as log:
            log.debug("test")
        msg = self.messages[log][0].rsplit("|", 1)[-1]
        self.assertEqual(f" {color.code}test{Color.RESET}", msg)

    def test_name_width(self) -> None:
        width = 123
        color = Color.red
        name = "TestCuteFormatter.name_width"
        with self.hijack(name, fmt=CuteFormatter(colors={name: color}, name_width=width)) as log:
            log.debug("test")
        lvl, _, nam, msg = self.messages[log][0].split("|")
        self.assertEqual("DEBUG", lvl.strip())
        self.assertEqual(f" {color(name.ljust(width))} ", nam)
        self.assertEqual(f" {color('test')}", msg)

    def test_no_color(self) -> None:
        name = "TestCuteFormatter.test_no_color"
        with self.hijack(name, fmt=CuteFormatter(colored=False)) as log:
            log.debug("test")
        lvl, _, nam, msg = self.messages[log][0].split("|")
        self.assertEqual("DEBUG", lvl.strip())
        self.assertEqual(name, nam.strip())
        self.assertEqual(" test", msg)

    def test_edit_colors(self) -> None:
        name = "TestCuteFormatter.edit_colors"
        cf = CuteFormatter(colored=False)
        color = Color.strikethrough_red
        with self.hijack(name, fmt=cf) as log:
            log.critical("test")
        msg = self.messages[log][0].rsplit("|", 1)[-1]
        self.assertEqual(" test", msg)
        with self.hijack(name, reuse=True, fmt=cf) as log:
            cf.colored = True
            cf.update({name: color})
            log.critical("test")
        msg = self.messages[log][0].rsplit("|", 1)[-1]
        self.assertEqual(f" {color.code}test{Color.RESET}", msg)

    def test_level_color(self) -> None:
        name = "TestCuteFormatter.test_level_color"
        msg = "test"
        levels = (5, 10, 20, 30, 40, 50, 60)
        with self.hijack(name, fmt=CuteFormatter()) as log:
            for i in levels:
                log.log(i, msg)
        self.assertEqual(len(levels), len(self.messages[log]))
        l_name = lambda idx: self.messages[log][idx].split("|")[0].strip()
        self.assertEqual(Color.dim("Level 5".ljust(8)), l_name(0))
        self.assertEqual("DEBUG", l_name(1))
        self.assertEqual(Color.blue("INFO".ljust(8)), l_name(2))
        self.assertEqual(Color.yellow("WARNING".ljust(8)), l_name(3))
        self.assertEqual(Color.red("ERROR".ljust(8)), l_name(4))
        self.assertEqual(Color.bright_red_bg_yellow("CRITICAL".ljust(8)), l_name(5))
        self.assertEqual(Color.bright_red_bg_yellow("Level 60".ljust(8)), l_name(6))

    def test_exception(self) -> None:
        name = "TestCuteFormatter.test_exception"
        with self.hijack(name, fmt=CuteFormatter()) as log:
            try:
                raise ValueError(name)
            except ValueError:
                log.error("test", exc_info=True)
        spt = self.messages[log][0].split("\n")
        self.assertTrue(len(spt) > 2)
        self.assertEqual("Traceback (most recent call last):", spt[1].strip())
        self.assertEqual("raise ValueError(name)", spt[-2].strip())
        self.assertEqual(f"ValueError: {name}", spt[-1].strip())

    def test_multi_color(self) -> None:
        base = "TestCuteFormatter.test_multi_color."
        cf = CuteFormatter()
        messages: set[str] = set()
        for i in range(100):
            with self.hijack(f"{base}{i}", fmt=cf) as log:
                log.info(base)
            messages.add(self.messages[log][0].rsplit("|", 1)[-1].strip())
        cols = ("red", "green", "yellow", "blue", "magenta", "cyan", "default")
        self.assertEqual({getattr(Color, i)(base) for i in cols}, messages)


if __name__ == "__main__":
    unittest.main()
