__version__ = "0.5.0"

from .not_set import NotSetType, NotSet
from .frozen import Freezable, frozen
from .singleton import Singleton
from .signal_cm import signal_cm
from .enum import Enum, auto
from . import log, io

__all__ = (
    "Enum",
    "Freezable",
    "NotSet",
    "NotSetType",
    "Singleton",
    "auto",
    "frozen",
    "io",
    "log",
    "signal_cm",
)
