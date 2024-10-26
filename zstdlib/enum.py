import collections


class EnumType(type):
    """
    Metaclass for uninstantiable Enum classes with required annotations and unique values
    Enum values may not be prefixed with _
    These 'Enum' classes may not be modified after creation
    """

    def __new__(mcs, name, bases, attrs, **kwargs):
        # Disallow instantiation
        for bad in ("__init__", "__new__"):
            if bad in attrs:
                raise AttributeError("Cannot define __init__ or __new__")
            attrs[bad] = None
        # Check annotations
        public = {i: k for i, k in attrs.items() if not i.startswith("__")}
        annotations = attrs.get("__annotations__", {})
        eok = kwargs.pop("empty_ok", False)
        if not public and not annotations:
            if not eok:
                raise ValueError("Enum type is empty")
        if bad := (pub_set := set(public)) - (an_set := set(annotations)):
            raise ValueError(f"All enum entries must be type annotated: {bad}")
        if bad := an_set - pub_set:
            raise ValueError(f"All type annotated entries must have a value: {bad}")
        for i, typ in annotations.items():
            if not isinstance(attrs[i], typ):
                raise TypeError(f"{i} is not of type {typ}")
        # Disallow duplicate values
        counts = collections.Counter(public.values())
        if dups := {i: k for i, k in public.items() if counts[k] > 1}:
            raise ValueError(f"Duplicate values: {dups}")
        # Construct class
        return type.__new__(mcs, name, bases, attrs, **kwargs)

    # Disallow modification

    def __delattr__(cls, *_):
        raise AttributeError("This class cannot be modified")

    def __setattr__(cls, *_):
        raise AttributeError("This class cannot be modified")


class Enum(metaclass=EnumType, empty_ok=True):
    """
    A uninstantiable Enum base type
    Subclasses must provide type-annotated fields with unique values
    Fields may not be prefixed with "_"
    Derived classes will not be modifiable
    """
