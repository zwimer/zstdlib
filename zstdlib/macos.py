from typing import NamedTuple, ParamSpec, ClassVar, TypeVar, Self
from collections.abc import Callable, Iterable
from subprocess import TimeoutExpired, Popen
from multiprocessing import Process
from contextlib import suppress
from logging import getLogger
from functools import wraps
from threading import Lock
from signal import Signals
from pathlib import Path
from os import getpid
import atexit

import osascript

__all__ = ("Caffeinate", "osascript")

CAFFEINATE = Path("/usr/bin/caffeinate")  # This is a hard-coded location on macOS
KILL_WAIT_SECONDS: int = 60  # How long to .wait after .send_signal

P = ParamSpec("P")
R = TypeVar("R")


class Caffeinate:
    """A small wrapper class around macOS' CLI tool Caffeinate"""

    _finalizing: ClassVar[bool] = False
    _instances_lock: ClassVar[Lock] = Lock()
    _instances: ClassVar[set[Caffeinate]] = set()  # Self makes mypy upset here; maybe b/c of subclassing? :/
    _log = getLogger(f"{__name__}.Caffeinate")

    __slots__ = ("_cmd", "_data", "_lock", "block", "signal")

    class _Data(NamedTuple):
        owner: int
        proc: Popen

    class SignalZeroError(ValueError):
        """Raised when calling __enter__ or __exit__ on a Caffeinate instance with .signal == 0"""

        def __init__(self) -> None:
            msg = "The context manager is meant for managing the subprocess' lifetime, which is disable by .signal == 0, consider using .start() / .stop() instead."
            super().__init__(msg)

    # pylint: disable=too-many-arguments
    def __init__(
        self,
        # Passed through to CLI tool
        cmd: Iterable[Path | str | None] | None = None,
        *,
        display: bool = False,
        idle: bool = False,
        disk: bool = False,
        system: bool = False,
        user: bool = False,
        timeout: int | None = None,
        wait: int | Popen | Process | None = None,
        # For Caeffinate class itself
        signal: Signals | int = Signals.SIGTERM,
        block: bool = False,
    ) -> None:
        """Invokes the macOS Caffeinate CLI tool to prevent sleeping.
        Arguments are passed through to Caffeinate, descriptions are taken from the CLI tool; if they disagree with those found in `man caffeinate`, theirs are more likely to be correct.
        No Caffeinate subprocess is started until .start() is called (or .__enter__ calls it)
        All created children subprocesses will be cleaned up during atexit unless they have .signal == 0
        After .stop()'d processes can .start() once more if desired
        Warning: If cmd is passed, re-invoking __enter__ after an __exit__ will cause Caffeinate to run again and thus the command will run again
        Warning: Trying to use a Caffeinate with signal == 0 will raise a SignalZeroError as it is likely undesired to try to manage the lifetime of a process excluded from lifetime management

        Args:
            cmd: An optional CLI command (and arguments) to run under the Caffeinate process
            display: If True: Create an assertion to prevent the display from sleeping.
            idle: If True: Create an assertion to prevent the system from idle sleeping.
            disk: If True: Create an assertion to prevent the disk from idle sleeping.
            system: If True: Create an assertion to prevent the system from sleeping. This assertion is valid only when system is running on AC power.
            user: If True: Create an assertion to declare that user is active. If the display is off, this option turns the display on and prevents the display from going into idle sleep. If a timeout is not specified with '-t' option, then this assertion is taken with a default of 5 second timeout.
            timeout: Specifies the timeout value in seconds for which this assertion has to be valid. The assertion is dropped after the specified timeout. Timeout value is not used by the Caeffinate CLI when cmd is passed. Note: this timeout is passed to the Caffeinate CLI command, it is not enforced by python
            wait: Waits for the process with the specified pid to exit. Once the the process exits, the assertion is also released. This option is ignored by the Caeffinate CLI when cmd is passed.
            This option conflicts with cmd.
            signal: The signal used to kill the child process (if cmd likely the process Caffeinate execs into). If 0, do not kill it
            block: If True: Block until cmd has finished executing before returning from __enter__
        """
        if not CAFFEINATE.exists():
            raise NotImplementedError(f"This class is only available on macOS via: {CAFFEINATE}")
        if (
            isinstance(timeout, float)
            or not isinstance(timeout, int | None)
            or (timeout is not None and timeout < 1)
        ):
            raise TypeError("timeout must be a positive integer or None")
        if not isinstance(wait, int | Popen | Process | None):
            raise TypeError(f"wait is of the wrong type: {type(wait)}")
        if not isinstance(signal, int | Signals):
            msg = f"signal is of the wrong type: {type(signal)}{"; did you mean signal=0?" if signal is None else ""}"
            raise TypeError(msg)
        if isinstance(cmd, str | Path):
            raise TypeError(f"cmd is of the wrong type: {type(cmd)}")
        if cmd is None:
            if block:
                raise ValueError("block requires cmd")
            cmd = []
        else:
            cmd = list(cmd)
            if not cmd:
                raise ValueError("Empty cmd iterable; did you mean to use cmd=None?")
        self._lock = Lock()
        self._data: Caffeinate._Data | None = None  # Have to hardcode "Caffeinate" for mypy :/
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
        self.signal = signal
        self.block = block

    def start(self) -> None:
        """Start Caffeinate-ing; nop if already started"""
        with self._lock:
            if self._data is not None:
                return
            pid = getpid()
            with self._instances_lock:
                if self._finalizing:
                    raise PythonFinalizationError("No more new Caeffinate subprocesses are allowed")
                self._data = self._Data(pid, Popen(self._cmd))  # pylint: disable=consider-using-with
                self._instances.add(self)
            self._log.debug("Created Popen(%s), pid=%s", self._cmd, self._data.proc.pid)
        if self.block:
            self._data.proc.wait()

    def stop(self) -> None:
        """
        Terminate the Caffeinate subprocess via self.signal; nop if not .stop()'d
        .wait() will timeout after KILL_WAIT_SECONDS
        """
        self._stop(self.signal)

    def __enter__(self) -> Self:
        """Call .start(), if .signal == 0, raise a SignalZeroError, returns self"""
        if not self.signal:
            raise self.SignalZeroError()
        self.start()
        return self

    def __exit__(self, *_: object) -> None:
        """Calls .stop(); if called with .signal == 0, raise an SignalZeroError"""
        signal = self.signal  # So user can't change it on us from another thread!
        if not signal:  # Before atexit removal (so users change .signal later if desired)
            raise self.SignalZeroError()
        self._stop(signal)

    @classmethod
    def decorate(
        cls, cmd: list[Path | str | None] | None = None, **init_kwargs: object
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
                with cls(cmd, **init_kwargs):  # type: ignore[arg-type]
                    return f(*args, **kwargs)

            return inner

        return outer

    def __repr__(self) -> str:
        pid = "NOT RUNNING" if self._data is None else self._data.proc.pid
        return f"<Caffeinate: PID={pid}, flags={self._cmd[1:]}, signal={self.signal}, block={self.block}>"

    # Rarely used methods

    @classmethod
    def kill_children(cls) -> None:
        """
        Clean up child Caffeinate subprocesses started by this class using their requested signals
        If any child has .signal == 0, that process is not killed
        """
        with cls._instances_lock:
            remove = list(cls._instances)
        cls._log.debug("Caffeinate: Cleaning up child subprocesses (if any)")
        for i in remove:
            with suppress(cls.SignalZeroError):
                i.__exit__()  # modifies cls._instances

    @classmethod
    def forget_signal_zero_children(cls) -> None:
        """
        This method exists to allow long running processes that
        endlessly spawns children with .signal == 0 to avoid memory leaks
        Normally these instances are stored until atexit in case .signal changes before then
        This methods forgets about all children with .signal == 0 (frees up the memory used storing them)
        This cannot be undone; avoid callng this unless you need the memory
        Warning: This does not remove any other references or destroy the instance
        """
        with cls._instances_lock:
            cls._instances -= {i for i in cls._instances if not i.signal}

    # Private methods

    def _stop(self, signal: int | Signals) -> None:
        """Workhose of .stop()"""
        with self._lock:
            if self._data is None:
                return
            # After this point, ensure no second removal attempt happens at atexit
            with self._instances_lock:
                self._instances.discard(self)
            if getpid() != self._data.owner:  # We don't care about these
                return
            if self._data.proc.poll() is None:  # No need to kill it if it's already dead
                self._log.debug("Cleaning up process %s with signal %s", self._data.proc.pid, signal)
                self._data.proc.send_signal(signal)
            try:
                self._data.proc.wait(timeout=KILL_WAIT_SECONDS)
            except TimeoutExpired:
                # Technically, Caffeinate itself forks and its child remains Caffeinate while the
                # parent becomes the cmd process, so say subprocess instead of Caffeinate processes
                self._log.error(
                    "subprocess (PID=%s) didn't exit on .send_signal(%s)", self._data.proc.pid, signal
                )
                raise
            self._data = None

    @classmethod
    def _atexit(cls) -> None:
        """
        Never invoke this manually; it is called by atexit
        Disallows instance constructon then invokes kill_chilren()
        """
        with cls._instances_lock:
            cls._finalizing = True
            cls._log.debug("Disallowing future child Caffeinate subprocesses")
        cls.kill_children()


assert 0 not in Signals, "0 not expected in signal.Signals as it's a nop"
atexit.register(Caffeinate._atexit)  # pylint: disable=protected-access
