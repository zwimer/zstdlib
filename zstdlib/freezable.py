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
