from threading import Lock
from typing import Any
import logging


class _State:
    __init__ = NotImplemented
    start: bool = False
    ready: bool = False
    lock = Lock()


def install(*, value: int = logging.DEBUG // 2, force: bool = False) -> None:
    """Install TRACE, logging.trace, getLogger().trace, etc into the logging module

    Args:
        value: The TRACE log level; default: logging.DEBUG // 2
        force: If true, force install most errors
    """
    with _State.lock:
        _install(value, force)


# Helpers


def _define_logger_trace(lc: type, method: str, value: int) -> None:
    # Define the function in the logger class, match name and help method style
    def trace(self: Any, msg: str, *args: Any, **kwargs: Any) -> Any:
        """Log 'msg % args' with severity 'TRACE'.

        To pass exception information, use the keyword argument exc_info with
        a true TRACE, e.g.

        logger.trace("Houston, we have a %s", "tiny problem", exc_info=True)
        """
        return self.log(value, msg, *args, **kwargs)

    setattr(lc, method, trace)


def _define_logging_trace(method: str, value: int) -> None:
    # Define the function in the logging module, match name and help method style
    def trace(msg: str, *args: Any, **kwargs: Any) -> Any:
        """Log a message with severity 'TRACE' on the root logger. If the logger
        has no handlers, call basicConfig() to add a console handler with a
        pre-defined format.
        """
        return logging.log(value, msg, *args, **kwargs)  # noqa: LOG015

    setattr(logging, method, trace)


def _error_check(value: int, lgc: type, name: str, method: str) -> None:
    if not 0 < value < logging.DEBUG:
        raise ValueError(f"value should be within: 0 < value < {logging.DEBUG}")
    if _State.ready:
        raise RuntimeError("Already installed trace")
    if _State.start:
        raise RuntimeError("Incomplete install detected")
    if hasattr(logging, name):
        raise AttributeError(f"logging module already has {name} defined")
    if hasattr(logging, method):
        raise AttributeError(f"logging module already has {method} defined")
    if hasattr(lgc, method):
        raise AttributeError(f"logging.getLoggerClass() class already has {method} defined")


def _install(value: int, force: bool) -> None:
    lgc = logging.getLoggerClass()
    method = "trace"
    name = method.upper()
    # Error check
    if not force:
        _error_check(value, lgc, name, method)
    _State.start = True
    # Add trace into the logging moule
    logging.addLevelName(value, name)
    setattr(logging, name, value)
    _define_logging_trace(method, value)
    _define_logger_trace(lgc, method, value)
    _State.ready = True
