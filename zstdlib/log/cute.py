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

    __slots__ = ("colored", "_color", "_cmap", "_lvl_cmap", "_dim_level", "_name_width")
    DEFAULT_CUTE_WIDTHS: dict[str, int] = {"cute_levelname": 8, "cute_time": 23, "cute_name": 12}
    DEFAULT_LEVEL_COLORS: dict[int, Color] = {
        INFO: Color.blue,
        WARNING: Color.yellow,
        ERROR: Color.red,
        CRITICAL: Color.bright_red_bg_yellow,
    }

    # pylint: disable=dangerous-default-value,keyword-arg-before-vararg,too-many-arguments
    def __init__(
        self,
        fmt="%(cute_levelname)s | %(cute_asctime)s | %(cute_name)s | %(cute_message)s",
        *args,
        colored: bool = True,
        dim_level: int = DEBUG,
        colors: dict[str, Color] = {},
        level_colors: dict[int, Color] = {},
        cute_widths: dict[str, int] = {},
        **kwargs,
    ):
        """
        log_colors may be overridden, for example, trace logs are printed dimly
        Do not modify cute_ parameters in the fmt string; they might have special formatting that is not visible
        Ex. %(cute_name)-8s should be done via cute_widths["cute_name"] = 8
        This is because cute_widths takes into account 0-width color codes when padding
        Level colors used are: DEFAULT_LEVEL_COLORS | level_colors
        Dimming of log messages is done for levels < dim_level
        :param fmt: The format string to use for the log message; do not modify cute_ parameters
        :param args: Passed to logging.Formatter
        :param colored: If False, no colors will be used regardless of the colors parameter
        :param colors: The colors to use for the given loggers, automatic for non-specified loggers
        :param level_colors: The colors to use >= the given levels, automatic for non-specified loggers
        :param cute_widths: The widths of the cute_ columns in the log message
        :param kwargs: Passed to logging.Formatter
        """
        super().__init__(fmt, *args, **kwargs)
        self._dim_level: int = dim_level
        self._cmap: dict[str, Color] = dict(colors)
        self._lvl_cmap: dict[int, Color] = self.DEFAULT_LEVEL_COLORS | level_colors
        self._widths = defaultdict(int, self.DEFAULT_CUTE_WIDTHS | cute_widths)
        if any(not i.startswith("cute_") for i in self._widths):
            raise ValueError("cute_widths must only contain cute_ parameters")
        self.colored: bool = colored

    def update(self, colors: dict[str, Color]):
        """
        Set the colors for all loggers; enables colors if disabled
        """
        self._cmap |= colors

    def format(self, record: LogRecord) -> str:
        levelname: str = record.levelname.ljust(self._widths["cute_levelname"])
        asctime = self.formatTime(record, self.datefmt).ljust(self._widths["cute_asctime"])
        name: str = record.name.ljust(self._widths["cute_name"])
        message: str = record.getMessage().ljust(self._widths["cute_message"])
        if self.colored:
            # Color level
            opts = tuple(i for i in self._lvl_cmap if i <= record.levelno)
            col: Color | None = self._lvl_cmap[max(opts)] if opts else None
            if record.levelno < self._dim_level:
                col = Color.dim if col is None else (col + Color.dim)
            if col is not None:
                levelname = col(levelname)
            # Color text
            if (col := self._cmap.get(record.name, None)) is None:
                c: int = adler32(record.name.encode()) % 7
                col = Color(RawColor(PureColor.black.value + c)) if c != 0 else Color.default
            if record.levelno < self._dim_level:
                col += Color.dim
            message = col(message)
            name = col(name)
            # Color timestamp
            if record.levelno < self._dim_level:
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
