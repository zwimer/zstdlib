from logging.handlers import QueueHandler
from contextlib import contextmanager
from collections.abc import Callable
from threading import Lock
from typing import Any
import logging
import queue


@contextmanager
def _cml(logger: logging.Logger, exit_func: Callable[[], Any]):
    try:
        yield logger
    finally:
        exit_func()


class LeftBase:
    """
    A base class for tests that hijack loggers
    """

    _hijacked: set[logging.Logger] = set()  # Set of all loggers that have ever been hijacked
    _qmap: dict[logging.Logger, queue.Queue[logging.LogRecord]] = {}
    _lb_old: dict[logging.Logger, list[logging.Handler]] = {}
    _lb_lock = Lock()

    messages: dict[logging.Logger, list[str]] = {}

    @classmethod
    def hijack(cls, name: str, reuse: bool = False, fmt: logging.Formatter | None = None):
        """
        :return: A logger configured to write to an internal queue
        """
        log = logging.getLogger(name)
        q: queue.Queue[logging.LogRecord] = queue.Queue()
        with cls._lb_lock:
            if not reuse and log in cls._hijacked:
                raise RuntimeError("Logger already hijacked")
            cls._hijacked.add(log)
            cls._lb_old[log] = log.handlers
            cls._qmap[log] = q
        log.handlers = [QueueHandler(q)]
        if fmt is not None:
            log.handlers[0].setFormatter(fmt)
        log.setLevel(1)  # Not 0 to ensure that the parent logger level is not used
        return _cml(log, lambda: cls._restore(log))

    @classmethod
    def _restore(cls, logger: logging.Logger) -> None:
        """
        Restore the logger and read all messages from the queue
        :return: The messages stored by the logger queue
        """
        if len(logger.handlers) != 1 or not isinstance(qh := logger.handlers[0], QueueHandler):
            raise RuntimeError("Logger not hijacked")
        # Restore old logger and extract q
        with cls._lb_lock:
            if logger not in cls._hijacked:
                raise RuntimeError("Logger not hijacked")
            logger.handlers = cls._lb_old.pop(logger)
            q = cls._qmap.pop(logger)
        # Read queue
        qh.flush()
        messages = []
        while not q.empty():
            messages.append(q.get(False).msg)
        with cls._lb_lock:
            cls.messages[logger] = messages
