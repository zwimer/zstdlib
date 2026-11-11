from typing import Literal, overload
from collections.abc import Iterable
from shlex import quote

__all__ = ("prompt_for", "prompt_until", "yn_prompt")

@overload
def prompt_until(
    msg: str,
    until: str | Iterable[str],
    *,
    ignore_case: bool = True,
    eof: Literal[False] = False,
    ctrl_c: Literal[False] = False,
) -> str: ...


@overload
def prompt_until(
    msg: str,
    until: str | Iterable[str],
    *,
    ignore_case: bool = True,
    eof: bool = False,
    ctrl_c: bool = False,
) -> str | None: ...


def prompt_until(
    msg: str,
    until: str | Iterable[str],
    *,
    ignore_case: bool = True,
    eof: bool = False,
    ctrl_c: bool = False,
) -> str | None:
    """
    Prompt the user with msg until they respone with a string in until, ignore case as needed
    Whitespace is stripped
    If ctrl_c and KeyboardInterrupt is caught, return None
    If eof EOFError is caught, return None
    Return the case-adjusted string the user entered
    """
    cased = lambda x: (x.casefold() if ignore_case else x)
    until = frozenset(map(cased, (until,) if isinstance(until, str) else until))
    try:
        while (ret := cased(input(msg).strip())) not in until:
            pass
        return ret
    except (EOFError, KeyboardInterrupt) as e:
        if eof if isinstance(e, EOFError) else ctrl_c:
            return None
        raise


def prompt_for(
    continue_str: str = "continue",
    *,
    ignore_case: bool = True,
    eof: bool = False,
    ctrl_c: bool = False,
) -> bool:
    """
    Prompt the user to contine by entering continue_str, whitespace is stripped
    If eof/ctrl_c, interpret EOFError/KeyboardInterrupt as commands to return False
    """
    ret = prompt_until(
        f"Type {quote(continue_str)} ",
        ignore_case=ignore_case,
        until={continue_str},
        eof=eof,
        ctrl_c=ctrl_c,
    )
    return isinstance(ret, str)


def yn_prompt(
    msg: str = "Yes or no?",
    *,
    eof: bool = False,
    ctrl_c: bool = False,
    yes_no: bool = False,
) -> bool:
    """
    Prompt the user to select from [yn], or [yes/no] if [yes/no], whitespace is stripped
    If eof/ctrl_c, interpret EOFError/KeyboardInterrupt as commands to return False
    """
    return prompt_until(
        f"{msg} [{"yes/no" if yes_no else "yn"}] ",
        until=("yes", "no") if yes_no else ("y", "n"),
        eof=eof,
        ctrl_c=ctrl_c,
    ) in ("y", "yes")
