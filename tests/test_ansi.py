# pylint: disable=missing-module-docstring,missing-class-docstring,missing-function-docstring
import unittest

from zstdlib.ansi import PureColor, RawColor, Color


class TestAnsiColor(unittest.TestCase):

    def test_raw_color(self) -> None:
        msg = "Hello, World!"
        for i, k in PureColor.__members__.items():
            self.assertEqual(f"\033[{k.value}m{msg}\033[0m", getattr(Color, i)(msg))

    def test_bright_background_color(self) -> None:
        msg = "Hello, World!"
        for i, k in PureColor.__members__.items():
            self.assertEqual(f"\033[{k.value+70}m{msg}\033[0m", getattr(Color, f"bg_bright_{i}")(msg))

    def test_init(self) -> None:
        msg = "Hello, World!"
        cname = "black"
        c = RawColor(getattr(PureColor, cname))
        self.assertEqual(f"\033[{c.value}m{msg}\033[0m", getattr(Color, cname)(msg))  # Sanity check
        self.assertEqual(f"\033[{c.value}m{msg}\033[0m", Color(c)(msg))
        self.assertEqual(f"\033[{c.value}m{msg}\033[0m", Color(c)(msg))
        self.assertEqual(f"\033[{c.value}m{msg}\033[0m", Color(Color(c))(msg))
        self.assertEqual(f"\033[{c.value}m{msg}\033[0m", Color(code=Color(c).code)(msg))
        # Errors
        with self.assertRaises(ValueError):
            _ = Color("blue_blue")
        with self.assertRaises(ValueError):
            _ = Color("bg_blue_bg_bright_blue")
        with self.assertRaises(ValueError):
            _ = Color(fmt="1", code="1")
        with self.assertRaises(ValueError):
            _ = Color(code="1")
        with self.assertRaises(ValueError):
            _ = Color("bright_bg_red")
        # Error converted
        with self.assertRaises(AttributeError):
            _ = Color.bright_bg_red

    def test_modifiers(self) -> None:
        msg = "Hello, World!"
        self.assertEqual(f"\033[1;34m{msg}\033[0m", Color.bold_blue(msg))  # Small modifier
        self.assertEqual(f"\033[9;32m{msg}\033[0m", Color.strikethrough_green(msg))  # Large modifier
        self.assertEqual(f"\033[2;9;31m{msg}\033[0m", Color.strikethrough_dim_red(msg))
        self.assertEqual(f"\033[3;4;5;39m{msg}\033[0m", Color.underline_italic_blinking_default(msg))
        # Test no colors / multiple colors
        self.assertEqual(f"\033[1m{msg}\033[0m", Color.bold(msg))
        self.assertEqual(f"\033[31;42m{msg}\033[0m", Color.red_bg_green(msg))
        self.assertEqual(f"\033[1;3;32;101m{msg}\033[0m", Color.bg_bright_red_bold_italic_green(msg))


if __name__ == "__main__":
    unittest.main()
