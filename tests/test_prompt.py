# pylint: disable=missing-module-docstring,missing-class-docstring,missing-function-docstring,unused-variable
from unittest.mock import MagicMock, patch
import unittest

from zstdlib.prompt import prompt_until, prompt_for, yn_prompt


mock_input = lambda *x: patch("builtins.input", side_effect=x)
mock_print = lambda: patch("builtins.print")


def want_have(mock_p: MagicMock, msg: str, n: int) -> tuple[list[str], list[str]]:
    if any(len(i.args) != 1 or i.kwargs for i in mock_p.call_args_list):
        return False
    return [i.args[0] for i in mock_p.call_args_list], [msg] * n


class TestPromptUntil(unittest.TestCase):
    msg = "print_me"

    def test_str(self) -> None:
        with mock_print() as stdout, mock_input("test", "test", "A") as stdout:
            self.assertEqual(prompt_until(self.msg, until="a"), "a")
            self.assertEqual(*want_have(stdout, self.msg, 3))

    def test_set(self) -> None:
        with mock_print() as stdout, mock_input("test", "ab", "A") as stdout:
            self.assertEqual(prompt_until(self.msg, until=("b", "a")), "a")
            self.assertEqual(*want_have(stdout, self.msg, 3))

    def test_case(self) -> None:
        with mock_print() as stdout, mock_input("test", "test", "a", "A") as stdout:
            self.assertEqual(prompt_until(self.msg, until="A", ignore_case=False), "A")
            self.assertEqual(*want_have(stdout, self.msg, 4))

    def test_eof(self) -> None:
        with mock_print() as stdout, mock_input("test", EOFError) as stdout:
            with self.assertRaises(EOFError):
                prompt_until(self.msg, until="A")
            self.assertEqual(*want_have(stdout, self.msg, 2))
        with mock_print() as stdout, mock_input("test", EOFError) as stdout:
            self.assertIs(prompt_until(self.msg, until="A", eof=True), None)
            self.assertEqual(*want_have(stdout, self.msg, 2))

    def test_ctrlc(self) -> None:
        with mock_print() as stdout, mock_input("test", KeyboardInterrupt) as stdout:
            with self.assertRaises(KeyboardInterrupt):
                prompt_until(self.msg, until="A")
            self.assertEqual(*want_have(stdout, self.msg, 2))
        with mock_print() as stdout, mock_input("test", KeyboardInterrupt) as stdout:
            self.assertIs(prompt_until(self.msg, until="A", ctrl_c=True), None)
            self.assertEqual(*want_have(stdout, self.msg, 2))


class TestPromptFor(unittest.TestCase):
    out = "Type continue "

    def test_basic(self) -> None:
        with mock_print() as stdout, mock_input("test", "test", "cOntinue") as stdout:
            self.assertTrue(prompt_for())
            self.assertEqual(*want_have(stdout, self.out, 3))

    def test_eof(self) -> None:
        with mock_print() as stdout, mock_input("test", EOFError) as stdout:
            with self.assertRaises(EOFError):
                prompt_for()
            self.assertEqual(*want_have(stdout, self.out, 2))
        with mock_print() as stdout, mock_input("test", EOFError) as stdout:
            self.assertFalse(prompt_for(eof=True))
            self.assertEqual(*want_have(stdout, self.out, 2))

class TestYNPrompt(unittest.TestCase):
    out = "Yes or no? [yn] "

    def test_basic(self) -> None:
        with mock_print() as stdout, mock_input("test", "yes", "y") as stdout:
            self.assertTrue(yn_prompt())
            self.assertEqual(*want_have(stdout, self.out, 3))
        with mock_print() as stdout, mock_input("test", "no", "n") as stdout:
            self.assertIs(yn_prompt(), False)
            self.assertEqual(*want_have(stdout, self.out, 3))

    def test_yes_no(self) -> None:
        out = "Yes or no? [yes/no] "
        with mock_print() as stdout, mock_input("test", "y", "yes") as stdout:
            self.assertTrue(yn_prompt(yes_no=True))
            self.assertEqual(*want_have(stdout, out, 3))
        with mock_print() as stdout, mock_input("test", "n", "no") as stdout:
            self.assertFalse(yn_prompt(yes_no=True))
            self.assertEqual(*want_have(stdout, out, 3))

    def test_eof(self) -> None:
        with mock_print() as stdout, mock_input("test", EOFError) as stdout:
            with self.assertRaises(EOFError):
                yn_prompt()
            self.assertEqual(*want_have(stdout, self.out, 2))
        with mock_print() as stdout, mock_input("test", EOFError) as stdout:
            self.assertFalse(yn_prompt(eof=True))
            self.assertEqual(*want_have(stdout, self.out, 2))


if __name__ == "__main__":
    unittest.main()
