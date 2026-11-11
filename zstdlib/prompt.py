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
    *,
    msg: str = "Continue?",
    key: str = "continue",
    ignore_case: bool = True,
    eof: bool = False,
    ctrl_c: bool = False,
) -> bool:
    """
    Prompt the user with msg to contine by entering key, whitespace is stripped
    If eof/ctrl_c, interpret EOFError/KeyboardInterrupt as commands to return False
    Returns True otherwise
    """
    ret = prompt_until(
        f"{msg} [{quote(key)}] ",
        ignore_case=ignore_case,
        until={key},
        eof=eof,
        ctrl_c=ctrl_c,
    )
    return isinstance(ret, str)


def yn_prompt(
    msg: str = "Continue?",
    *,
    empty_ok: bool = False,
    eof: bool = False,
    ctrl_c: bool = False,
    short: bool = True,
) -> bool:
    """
    Prompt the user to select from [yn] if short else [yes/no], whitespace is stripped
    If eof/ctrl_c, interpret EOFError/KeyboardInterrupt as commands to return False
    If empty_ok, "" is considered the same as "n"; empty_ok is a nop when not short
    """
    return prompt_until(
        f"{msg} [{"yn" if short else "yes/no"}] ",
        until=(("y", "n") + (("",) if empty_ok else ())) if short else ("yes", "no"),
        eof=eof,
        ctrl_c=ctrl_c,
    ) in ("y", "yes")
