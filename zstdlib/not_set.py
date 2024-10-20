from .singleton import Singleton


class NotSetType(Singleton):
    """
    A type that exists to denote a value has not been set
    This might be useful when None is a valid value for a type
    """


# The sole value for NotSetType
NotSet = NotSetType()
