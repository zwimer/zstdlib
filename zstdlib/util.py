from pathlib import Path

__all__ = ("normpath",)


def normpath(path: Path) -> Path:
    """normpath for pathlib.Path"""
    return Path(path.parser.normpath(path))
