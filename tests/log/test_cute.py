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

    def test_width(self) -> None:
        color = Color.red
        name = "TestCuteFormatter.test_width"
        cw = {
            "cute_levelname": 300,
            "cute_asctime": 200,
            "cute_name": 100,
            "cute_message": 400,
        }
        fmt = CuteFormatter(fmt="|".join(f"%({i})s" for i in cw), colors={name: color}, cute_widths=cw)
        with self.hijack(name, fmt=fmt) as log:
            log.debug("test")
        lvl, date, nam, msg = self.messages[log][0].split("|")
        self.assertEqual("DEBUG".ljust(cw["cute_levelname"]), lvl)
        self.assertEqual(cw["cute_asctime"], len(date))
        self.assertEqual(f"{color(name.ljust(cw['cute_name']))}", nam)
        self.assertEqual(f"{color('test'.ljust(cw['cute_message']))}", msg)
        with self.assertRaises(ValueError):
            CuteFormatter(cute_widths={"name": 123})

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

    def test_custom_dim_level(self) -> None:
        name = "TestCuteFormatter.test_dim_level"
        msg = "test"
        with self.hijack(name, fmt=CuteFormatter(dim_level=5)) as log:
            log.log(4, msg)
            log.log(5, msg)
        self.assertEqual(2, len(self.messages[log]))
        l_name = lambda idx: self.messages[log][idx].split("|")[0].strip()
        self.assertEqual(Color.dim("Level 4".ljust(8)), l_name(0))
        self.assertEqual("Level 5", l_name(1))

    def test_custom_level_color(self) -> None:
        name = "TestCuteFormatter.test_custom_level_color"
        msg = "test"
        with self.hijack(name, fmt=CuteFormatter(level_colors={15: Color.bright_red_bg_yellow})) as log:
            log.log(14, msg)
            log.log(15, msg)
        self.assertEqual(2, len(self.messages[log]))
        l_name = lambda idx: self.messages[log][idx].split("|")[0].strip()
        self.assertEqual("Level 14".ljust(8), l_name(0))
        self.assertEqual(Color.bright_red_bg_yellow("Level 15".ljust(8)), l_name(1))

    def test_exception(self) -> None:
        name = "TestCuteFormatter.test_exception"
        with self.hijack(name, fmt=CuteFormatter()) as log:
            try:
                raise ValueError(name)
            except ValueError:
                log.error("test", exc_info=True)
        spt = self.messages[log][0].split("\n")
        self.assertGreater(len(spt), 2)
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
        self.assertSetEqual({getattr(Color, i)(base) for i in cols}, messages)


if __name__ == "__main__":
    unittest.main()
