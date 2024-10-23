from enum import Enum, unique, auto
from functools import cache
from typing import Self
import re


MODIFIERS = ("bold", "dim", "italic", "underline", "blinking", "inverse", "hidden", "strikethrough")

_PREFIX = "\033["


@unique
class PureColor(Enum):
    """
    An enum of ansi color values
    """

    black = 30
    red = auto()
    green = auto()
    yellow = auto()
    blue = auto()
    magenta = auto()
    cyan = auto()
    white = auto()
    default = 39


class RawColor:
    """
    A class that represents a color with all possible modifiers
    """

    __slots__ = ("color", "bright", "background", "value")

    def __init__(self, color: PureColor | str | int, *, bright: bool = False, background: bool = False):
        self.color = PureColor(getattr(PureColor, color) if isinstance(color, str) else color)
        self.bright = bright
        self.background = background
        self.value = self.color.value + (10 if self.background else 0) + (60 if self.bright else 0)


class _ColorMeta(type):
    """
    A metaclass that implements __getattr__ at the class level for Color
    """

    def __getattr__(cls, item: str) -> "Color":
        try:
            return cls(code=_parse_color(item))
        except ValueError as e:
            raise AttributeError(str(e)) from e


class Color(metaclass=_ColorMeta):
    """
    Represents an Ansi color code; calling this on a string will apply the code to the string
    Can be constructed via .factory; alternatively calling Color.<name> or Color(<name>) will
    automatically construct a color. Colors are constructed with attributes determined by
    splitting <name> on "_". Colors may be made bright by prepending "bright_" to the color name
    Background colors may be specified by prepending "BG_" to a color name
        BG_ must precede bright_ if both are specified
    Foreground and background colors may both be specified at once
    Examples:
        Color.red
        Color.default
        Color.BRIGHT_BLUE
        Color.BG_green
        Color.Bright_BG_black
        Color.bold_underline_yellow
        Color.bold_bright_bg_BLUE_bright_green
        Color.BOLD_bright_Red_strikethrough_bg_Bright_GREEN
    """

    __slots__ = ("code",)

    RESET: str = f"{_PREFIX}0m"

    def __init__(self, fmt: Self | RawColor | str = "", *, code: str = "") -> None:
        """
        Create a Color based on either the format or code, exactly one must be passed
        :param fmt: A Color, RawColor, or string representation of this desired color
        :param code: The ansi color code this object represents
        """
        if fmt != "" and code != "":
            raise ValueError("code and fmt may not both be passed")
        if code:
            if not code.startswith(_PREFIX) or not code.endswith("m"):
                raise ValueError("Invalid ansi color code")
            self.code: str = code
        elif isinstance(fmt, RawColor):
            self.code = f"{_PREFIX}{fmt.value}m"
        else:
            self.code = _parse_color(fmt) if isinstance(fmt, str) else fmt.code

    def __call__(self, string: str) -> str:
        """
        :return: The string color codes with the given ansi code
        """
        return f"{self.code}{string}{self.RESET}"

    def __add__(self, other: Self) -> Self:
        """
        :return: A new color made by concatenating these two
        """
        if not isinstance(other, type(self)):
            raise TypeError("Cannot add non-Color to Color")
        return type(self)(code=f"{self.code[:-1]};{other.code[len(_PREFIX):]}")

    def __eq__(self, other: object) -> bool:
        """
        :return: Whether the two colors are equal
        """
        return isinstance(other, type(self)) and self.code == other.code

    def __repr__(self) -> str:
        """
        :return: The ansi color code this object represents
        """
        return f"<Color {repr(self.code)}>"

    @classmethod
    def factory(
        cls, *, foreground: RawColor | None = None, background: RawColor | None = None, **modifiers
    ) -> Self:
        """
        :return: The Ansi given the chosen color and various modifiers
        """
        return cls(code=_generate_code(foreground, background, modifiers))


def _generate_code(
    foreground: RawColor | None, background: RawColor | None, modifiers: dict[str, bool]
) -> str:
    """
    :return: The Ansi given the chosen color and various modifiers
    """
    if any(bad := [i for i in modifiers if i not in MODIFIERS]):
        raise ValueError(f"Unknown modifier(s): {bad}")
    modifiers = {i: modifiers.get(i, False) for i in MODIFIERS}
    raw = (MODIFIERS.index(i) + 1 for i, k in modifiers.items() if k)
    ints = [i + (0 if i < 6 else 1) for i in raw]  # Ansi skips 6 for some reason
    if foreground:
        ints.append(foreground.value)
    if background:
        ints.append(background.value)
    return f"{_PREFIX}{';'.join(str(i) for i in ints)}m"


@cache
def _parse_color(item: str) -> str:
    """
    Construct a color following the rules defined by Color
    This method is not a classmethod since python3.13 deprecates mixing classmethod and cache
    """
    item = item.lower()
    if "bright_bg" in item:
        raise ValueError("bg_ must precede bright_ in color specification")
    pat = f"(:?bright_)?({'|'.join(list(PureColor.__members__))})"
    shx = re.findall(f"(bg_){pat}", item)
    if len(shx) > 1:
        raise ValueError(f"Multiple background colors specified in {item}")
    bg: RawColor | None = None
    if len(shx) == 1:
        item = item.replace("".join(shx[0]), "")
        bg = RawColor(shx[0][-1], bright="bright_" in shx[0], background=True)
    shx = re.findall(pat, item)
    if len(shx) > 1:
        raise ValueError(f"Multiple foreground colors specified in {item}")
    fg: RawColor | None = None
    if len(shx) == 1:
        item = item.replace("".join(shx[0]), "")
        fg = RawColor(shx[0][-1], bright="bright_" in shx[0])
    # Determine modifiers and construct the color
    attrs = [i for i in item.split("_") if i]
    if any(bad := [i for i in attrs if i not in MODIFIERS]):
        raise ValueError(f"Unknown modifiers(s): {', '.join(bad)}")
    return _generate_code(fg, bg, {i: True for i in MODIFIERS if i in attrs})
