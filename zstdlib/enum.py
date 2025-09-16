from collections.abc import Iterator
from typing import Any


class _Auto:
    """A sentinel value for automatic enum values"""


# Pass this as a value to have it automatically assigned
auto = _Auto()


class EnumType(type):
    """
    Metaclass for uninstantiable Enum classes with required annotations and unique values
    Enum entry names may not be prefixed with __ or be an EnumType._AutoValue
    These 'Enum' classes may not be modified after creation
    Items of annotation types in type_check will be type-checked
    Duplicate values (as determined by set()) are not allowed unless dupes_ok is True
    """

    _AUTO_PREFIX = "Enum_Auto_"
    _TC_DEFAULT: set[type | None] = {int, str, float, bool, complex, bytes, None, type(None)}

    class _AutoValue:
        """A class representing an automatically assigned enum value"""

        def __init__(self, value: int) -> None:
            self._value = value

        def __str__(self) -> str:
            return f"<Auto: {self._value}>"

        def __repr__(self) -> str:
            return str(self)

    @classmethod
    def _gen_entries_and_annotations(
        mcs, attrs: dict, dupes_ok: bool
    ) -> tuple[dict[str, tuple[type | None, Any]], dict[str, type | None]]:
        """
        Generate enum entries from attrs, checking for duplicates and missing annotations
        Does not check for empty enum or type correctness
        """
        seen = set()
        auto_val = 0
        _entries = {}
        _annotations = dict(attrs.get("__annotations__", {}))
        try:
            for a_name, value in ((i, k) for i, k in attrs.items() if not i.startswith("__")):
                if value is auto:
                    auto_val += 1
                    value = mcs._AutoValue(auto_val)
                    if a_name in _annotations:
                        raise TypeError("Auto enum entries may not be type annotated")
                    _annotations[a_name] = mcs._AutoValue
                elif isinstance(value, mcs._AutoValue):
                    raise ValueError("Enum entries may not be of type EnumType._AutoValue")
                if not dupes_ok:
                    if value in seen:
                        raise ValueError(f"Duplicate enum value: {value}")
                    seen.add(value)
                _entries[a_name] = (_annotations[a_name], value)
        except TypeError:
            raise TypeError(f"Unhashable enum value: {value}") from None
        except KeyError:
            raise ValueError("Non-auto enum entries must be type annotated") from None
        return _entries, _annotations

    # pylint: disable=too-many-arguments, dangerous-default-value
    def __new__(
        mcs,
        name,
        bases,
        attrs,
        *,
        empty_ok: bool = False,
        dupes_ok: bool = False,
        type_check: set[type | None] = _TC_DEFAULT,
        **kwargs,
    ):
        # Disallow undesired instance methods
        if bad := attrs.keys() & {"__init__", "__new__", "__entries__"}:
            raise AttributeError(f"Illegal methods in Enum class: {', '.join(bad)}")
        # Generate entries
        _entries, _annotations = mcs._gen_entries_and_annotations(attrs, dupes_ok)
        # Validate entries
        if no_value := (_annotations.keys() - _entries.keys()):
            raise ValueError(f"Entries must have a value: {' '.join(no_value)}")
        if (not empty_ok) and not _entries:
            raise ValueError("Enum type may not be empty")
        if type_check:
            for a_name, (ann, val) in _entries.items():
                if ann in type_check and (
                    (ann is None is not val) or (ann is not None and not isinstance(val, ann))
                ):
                    raise TypeError(f"Entry {a_name} is not of type {ann}")
        # Construct class
        attrs["__entries__"] = _entries
        attrs["__annotations__"] = _annotations
        attrs["__init__"] = attrs["__new__"] = NotImplemented
        return type.__new__(mcs, name, bases, attrs, **kwargs)

    # Disallow modification

    def __delattr__(cls, *_):
        raise AttributeError("This class cannot be modified")

    def __setattr__(cls, *_):
        raise AttributeError("This class cannot be modified")

    # Class methods for the derived types

    def __iter__(cls) -> Iterator[str]:
        """Iterator over enum keys"""
        yield from cls.__entries__  # type: ignore

    def _disallow(cls):
        """Disallow instantiation"""
        raise AttributeError("This class may not be instantiated")


class Enum(metaclass=EnumType, empty_ok=True):
    """
    An uninstantiable Enum base type
    Subclasses must provide type-annotated fields with unique values
    Fields may not be prefixed with "__"
    Derived classes will not be modifiable
    """


def entries(enum: Any) -> dict[str, tuple[type | None, Any]]:
    """
    :param enum: A class whose metaclass is EnumType
    :return: A dict mapping names to (type annotation, value) pairs
    If enum's type is not an EnumType, raises TypeError
    """
    if not isinstance(enum, EnumType):
        raise TypeError("enum must have a metaclass of EnumType")
    return dict(enum.__entries__)  # type: ignore[attr-defined]


def values(enum: Any) -> tuple[Any, ...]:
    """
    :param enum: A class whose metaclass is EnumType
    :return: A tuple of all values of enum
    If enum's type is not an EnumType, raises TypeError
    """
    if not isinstance(enum, EnumType):
        raise TypeError("enum must have a metaclass of EnumType")
    return tuple(k[1] for k in enum.__entries__.values())  # type: ignore[attr-defined]


__all__ = ("Enum", "EnumType", "entries", "values", "auto")
