class Freezable:
    """
    A base class for objects that can be frozen
    """

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)  # For MRO super classes
        if hasattr(self, "_frozen") or hasattr(self, "_can_thaw"):
            raise ValueError("Base class defines _frozen or _can_thaw")
        self._can_thaw: bool = True
        self._frozen: bool = False

    def freeze(self, *, permanent: bool = False):
        """
        Prevent further modifications to this object
        """
        if permanent:
            self._can_thaw = False
        self._frozen = True

    def thaw(self):
        """
        Allow modifications to this object
        """
        if not self._can_thaw:
            raise RuntimeError("Cannot thaw permanently frozen object")
        object.__setattr__(self, "_frozen", False)

    def __setattr__(self, key: str, value) -> None:
        if getattr(self, "_frozen", False):
            raise AttributeError("Cannot modify frozen object")
        super().__setattr__(key, value)

    def __delattr__(self, item: str) -> None:
        if getattr(self, "_frozen", False):
            raise AttributeError("Cannot modify frozen object")
        super().__delattr__(item)


def frozen(cls):
    """
    A class decorator to permanently freeze a class after __init__
    """

    def __setattr__(self, key: str, value) -> None:
        if getattr(self, "_frozen", False):
            raise AttributeError("Cannot modify frozen object")
        super(cls, self).__setattr__(key, value)

    def __delattr__(self, item: str) -> None:
        if getattr(self, "_frozen", False):
            raise AttributeError("Cannot modify frozen object")
        super(cls, self).__delattr__(item)

    init = cls.__init__

    def __init__(self, *args, **kwargs):
        init(self, *args, **kwargs)
        self._frozen = True  # pylint: disable=protected-access

    # Update cls with the new methods
    cls.__setattr__ = __setattr__
    cls.__delattr__ = __delattr__
    cls.__init__ = __init__
    return cls
