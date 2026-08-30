__version__ = "0.8.0"

from .not_set import NotSetType, NotSet
from .frozen import Freezable, frozen
from .singleton import Singleton
from .signal_cm import signal_cm
from .enum import Enum, auto
from . import macos, lazy, log, io

__all__ = (
    "Enum",
    "Freezable",
    "NotSet",
    "NotSetType",
    "Singleton",
    "auto",
    "frozen",
    "io",
    "lazy",
    "log",
    "macos",
    "signal_cm",
)
