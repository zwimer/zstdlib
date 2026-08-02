__version__ = "0.4.1"

from .not_set import NotSetType, NotSet
from .frozen import Freezable, frozen
from .singleton import Singleton
from .enum import Enum, auto
from . import log, io

__all__ = ("Enum", "Freezable", "NotSet", "NotSetType", "Singleton", "auto", "frozen", "io", "log")
