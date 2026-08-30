from typing import NamedTuple, ParamSpec, ClassVar, TypeVar, Self
from subprocess import TimeoutExpired, Popen
from collections.abc import Callable
from multiprocessing import Process
from logging import getLogger
from functools import wraps
from threading import Lock
from pathlib import Path
from os import getpid
import atexit

import osascript

CAFFEINATE = "/usr/bin/caffeinate"  # This is a hard-coded location on macOS
P = ParamSpec("P")
R = TypeVar("R")
_log = getLogger(__name__)


__all__ = ("Caffeinate", "osascript")


class Caffeinate:
    """A small wrapper class around macOS' CLI tool Caffeinate"""

    _armed_lock: ClassVar[Lock] = Lock()
    _armed: ClassVar[set[Self]] = set()
    __slots__ = ("_cmd", "_data", "_lock", "_wait")

    class _Data(NamedTuple):
        owner: int
        proc: Popen

    # pylint: disable=too-many-arguments
    def __init__(
        self,
        cmd: list[Path | str | None] | None = None,
        *,
        wait_for_cmd: bool = False,
        display: bool = False,
        idle: bool = False,
        disk: bool = False,
        system: bool = False,
        user: bool = False,
        timeout: int | None = None,
        wait: int | Popen | Process | None = None,
    ) -> None:
        """Invokes the macOS Caffeinate CLI tool to prevent sleeping.
        Arguments are passed through to Caffeinate, descriptions are taken from the CLI tool; if they disagree with those found in `man caffeinate`, theirs are more likely to be correct.
        Warning: If cmd is passed, re-invoking __enter__ after an __exit__ will cause Caffeinate to run again and thus the command will run again

        Args:
            cmd: An optional CLI command (and arguments) to run under the Caffeinate process
            wait_for_cmd: If True: Wait until cmd has finished executing before returning from __enter__
            display: If True: Create an assertion to prevent the display from sleeping.
            idle: If True: Create an assertion to prevent the system from idle sleeping.
            disk: If True: Create an assertion to prevent the disk from idle sleeping.
            system: If True: Create an assertion to prevent the system from sleeping. This assertion is valid only when system is running on AC power.
            user: If True: Create an assertion to declare that user is active. If the display is off, this option turns the display on and prevents the display from going into idle sleep. If a timeout is not specified with '-t' option, then this assertion is taken with a default of 5 second timeout.
            timeout: Specifies the timeout value in seconds for which this assertion has to be valid. The assertion is dropped after the specified timeout. This option conflicts with cmd. Note: this timeout is passed to the Caffeinate CLI command, it is not enforced by python
         with this command.
            wait: Waits for the process with the specified pid to exit. Once the the process exits, the assertion is also released. This option conflicts with cmd.
        """
        if cmd is None:
            if wait_for_cmd:
                raise ValueError("wait_for_cmd requires cmd not be None")
            cmd = []
        elif not cmd:
            raise ValueError("Empty cmd; did you mean to use None?")
        elif timeout is not None:
            raise ValueError("timeout may not be used with cmd")
        elif wait is not None:
            raise ValueError("wait may not be used with cmd")
        else:
            cmd = list(cmd)
        self._lock = Lock()
        self._data: Caffeinate._Data | None = None  # Have to hardcode "Caffeinate" for mypy :/
        if isinstance(timeout, float):
            raise TypeError("Float timeout not supported")
        if timeout is not None and timeout < 1:
            raise ValueError("Timeout should be a positive integer")
        wait = wait.pid if isinstance(wait, Popen | Process) else wait
        flags = [
            "-d" if display else None,
            "-i" if idle else None,
            "-m" if disk else None,
            "-s" if system else None,
            "-u" if user else None,
            None if timeout is None else f"-t {timeout}",
            None if wait is None else f"-w {wait}",
        ]
        self._cmd = list(map(str, [CAFFEINATE] + [k for i in flags if i for k in i.split(" ")] + cmd))
        self._wait = wait_for_cmd

    def __enter__(self) -> Self:
        """Start Caffeinate-ing"""
        with self._lock:
            if self._data is not None:
                raise RuntimeError("This context manager has already been entered")
            self._data = self._Data(getpid(), Popen(self._cmd))
            _log.debug("Created Popen(%s), pid=%s", self._cmd, self._data.proc.pid)
        if self._wait:
            self._data.proc.wait()
        return self

    def __exit__(self, *_: object) -> None:
        with self._lock:
            if self._data is None:
                raise RuntimeError("Context managernever __enter__'d or already __exit__'d")
            if getpid() != self._data.owner:
                return
            _log.debug("Reaping Caffeinate process: %s", self._data.proc.pid)
            self._data.proc.terminate()
            try:
                self._data.proc.wait(timeout=1)
            except TimeoutExpired:
                _log.error("Caffeinate process didn't exit on .terminate()")
                self._data.proc.kill()
            self._data = None

    @classmethod
    def decorate(
        cls, cmd: list[Path | str | None] | None = None, **caffeinate_kwargs: object
    ) -> Callable[[Callable[P, R]], Callable[P, R]]:
        """A decorator to wrap a function with a Caffeinate instance
        Example:
            @decorate(idle=True)
            def foo():
        """
        if cmd and callable(cmd[0]):
            raise ValueError(f"Invalid usage of .decorate; see help({cls.__name__}.decorate)")

        def outer(f: Callable[P, R]) -> Callable[P, R]:
            @wraps(f)
            def inner(*args: P.args, **kwargs: P.kwargs) -> R:
                with cls(cmd, **caffeinate_kwargs):  # type: ignore[arg-type]
                    return f(*args, **kwargs)

            return inner

        return outer

    @classmethod
    def new(
        cls,
        cmd: list[Path | str | None] | None = None,
        *,
        survive_exit: bool = False,
        **kwargs: object,
    ) -> Self:
        """Return an __enter__'d Caffeinate, whose __exit__ will run atexit
        cmd and **kwargs are passed to __init__

        Args:
            cmd: Passed to Caffeinate
            survive_exit: Do not kill this Caffeinate instance when this process exits
            kwargs: Passed to Caffeinate
        """
        ret = cls(cmd, **kwargs)  # type: ignore[arg-type]
        _ = ret.__enter__()  # pylint: disable=unnecessary-dunder-call
        if not survive_exit:
            with cls._armed_lock:
                cls._armed.add(ret)
        return ret

    def survive_exit(self) -> None:
        """Disable atexit death; only permitted for instances created by .new()"""
        # pylint: disable=protected-access
        with self._armed_lock:
            if self not in self._armed:
                msg = f"This instance was not created by {self.__class__.__name__}.new() or already called .survive_exit()"
                raise ValueError(msg)
            self._armed.remove(self)
            assert self._data is not None
            _log.debug("Disabled cleanup of caffeinate subprocess PID=%s", self._data.proc.pid)

    @classmethod
    def _atexit(cls) -> None:
        """Clean up child Caffeinate subprocesses started by this class"""
        # pylint: disable=protected-access
        pid = getpid()
        _log.debug("Cleaning up all owned Caffeinate subprocesses started this process (PID=%s)", pid)
        with cls._armed_lock:
            for i in cls._armed:
                if i._data is None:
                    _log.error("Unentered Caffeinate process in ._armed; this should never happen")
                    continue
                if i._data.owner == pid:
                    i.__exit__()
            cls._armed.clear()

    def __repr__(self) -> str:
        if self._data is None:
            return f"<Caffeinate: NOT RUNNING, flags={self._cmd[1:]}>"
        return f"<Caffeinate: PID={self._data.proc.pid}, flags={self._cmd[1:]}>"


atexit.register(Caffeinate._atexit)  # pylint: disable=protected-access
