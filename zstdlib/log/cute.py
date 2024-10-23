from __future__ import annotations
from logging import CRITICAL, ERROR, WARNING, INFO, DEBUG, Formatter
from collections import defaultdict
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

    DEFAULT_CUTE_WIDTHS = {"cute_levelname": 8, "cute_time": 23, "cute_name": 12}
    __slots__ = ("colored", "_color", "_cmap", "_name_width")

    # pylint: disable=dangerous-default-value
    def __init__(
        self,
        colors: dict[str, Color] | None = None,
        *,
        colored: bool = True,
        cute_widths: dict[str, int] = {},
        fmt="%(cute_levelname)s | %(cute_asctime)s | %(cute_name)s | %(cute_message)s",
        **kwargs,
    ):
        """
        log_colors may be overridden, for example, trace logs are printed dimly
        Do not modify cute_ parameters in the fmt string; they might have special formatting that is not visible
        Ex. %(cute_name)-8s should be done via cute_widths["cute_name"] = 8
        This is because cute_widths takes into account 0-width color codes when padding
        :param colors: The colors to use for the given loggers, automatic for non-specified loggers
        :param colored: If False, no colors will be used regardless of the colors parameter
        :param fmt: The format string to use for the log message; do not modify cute_ parameters
        :param cute_widths: The widths of the cute_ columns in the log message
        :param kwargs: Passed to logging.Formatter
        """
        super().__init__(fmt=fmt, **kwargs)
        self._cmap: dict[str, Color] = {}
        if colors is not None:
            self.update(colors)
        self._widths = defaultdict(int, self.DEFAULT_CUTE_WIDTHS | cute_widths)
        if any(not i.startswith("cute_") for i in self._widths):
            raise ValueError("cute_widths must only contain cute_ parameters")
        self.colored: bool = colored

    def update(self, colors: dict[str, Color]):
        """
        Set the colors for all loggers; enables colors if disabled
        """
        self._cmap.update(colors)

    def format(self, record: LogRecord) -> str:
        levelname: str = record.levelname.ljust(self._widths["cute_levelname"])
        asctime = self.formatTime(record, self.datefmt).ljust(self._widths["cute_asctime"])
        name: str = record.name.ljust(self._widths["cute_name"])
        message: str = record.getMessage().ljust(self._widths["cute_message"])
        if self.colored:
            # Color level
            if record.levelno >= CRITICAL:
                levelname = Color.bright_red_bg_yellow(levelname)
            elif record.levelno >= ERROR:
                levelname = Color.red(levelname)
            elif record.levelno >= WARNING:
                levelname = Color.yellow(levelname)
            elif record.levelno >= INFO:
                levelname = Color.blue(levelname)
            elif record.levelno < DEBUG:
                levelname = Color.dim(levelname)
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
                asctime = Color.dim(asctime)
        # Create an updated record then format that
        new = copy(record)
        new.__dict__.update(
            {
                "cute_levelname": levelname,
                "cute_asctime": asctime,
                "cute_name": name,
                "cute_message": message,
            }
        )
        return super().format(new)
