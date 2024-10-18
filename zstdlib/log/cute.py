from __future__ import annotations
from logging import CRITICAL, ERROR, WARNING, INFO, DEBUG, Formatter
from traceback import format_exception
from typing import TYPE_CHECKING
from zlib import adler32
from copy import copy

from ..ansi import PureColor, RawColor, Color

if TYPE_CHECKING:
    from logging import LogRecord


class CuteFormatter(Formatter):
    """
    A log formatter that can print log messages with colors.
    """

    __slots__ = ("colored", "_color", "_cmap", "_name_width")

    def __init__(
        self,
        colors: dict[str, Color] | None = None,
        *,
        colored: bool = True,
        name_width: int = 12,
        fmt="%(cute_levelname)s | %(cute_time)s | %(cute_name)s | %(cute_message)s%(cute_exc)s",
        **kwargs,
    ):
        """
        log_colors may be overridden, for example, trace logs are printed dimly
        Do not modify cute_ parameters in the fmt string; they might have special formatting that is not visible
        Ex. %(cute_name)-8s should be done via name_width, that takes into account 0-width color codes
        :param colors: The colors to use for the given loggers, automatic for non-specified loggers
        :param colored: If False, no colors will be used regardless of the colors parameter
        :param fmt: The format string to use for the log message; do not modify cute_ parameters
        :param name_width: How wide the column containing the logger name should be (minus padding)
        :param kwargs: Passed to logging.Formatter
        """
        super().__init__(fmt=fmt, **kwargs)
        self._cmap: dict[str, Color] = {}
        if colors is not None:
            self.update(colors)
        self._name_width = name_width
        self.colored: bool = colored

    def update(self, colors: dict[str, Color]):
        """
        Set the colors for all loggers; enables colors if disabled
        """
        self._cmap.update(colors)

    def format(self, record: LogRecord) -> str:
        level: str = record.levelname.ljust(8)
        when = self.formatTime(record, self.datefmt).ljust(23)
        name: str = record.name.ljust(self._name_width)
        message: str = record.getMessage()
        if self.colored:
            # Color level
            if record.levelno >= CRITICAL:
                level = Color.bright_red_bg_yellow(level)
            elif record.levelno >= ERROR:
                level = Color.red(level)
            elif record.levelno >= WARNING:
                level = Color.yellow(level)
            elif record.levelno >= INFO:
                level = Color.blue(level)
            elif record.levelno < DEBUG:
                level = Color.dim(level)
            # Color text
            if (col := self._cmap.get(record.name, None)) is None:
                c: int = adler32(record.name.encode()) % 7
                col = Color(RawColor(PureColor.black.value + c)) if c != 0 else Color.default
            if record.levelno < DEBUG:
                col += Color.dim
            message = col(message)
            name = col(name)
            # Color timestamp
            if record.levelno < DEBUG:
                when = Color.dim(when)
        # Create an updated record then format that
        new = copy(record)
        new.__dict__.update(
            {
                "cute_levelname": level,
                "cute_time": when,
                "cute_name": name,
                "cute_message": message,
                "cute_exc": ("\n" + "".join(format_exception(*new.exc_info))[:-1]) if new.exc_info else "",
            }
        )
        return super().format(new)
