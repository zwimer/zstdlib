from contextlib import contextmanager
from collections.abc import Callable
from logging import getLogger
import signal


@contextmanager
def signal_cm(
    signalnum: signal.Handlers | int,
    handler: Callable,
    *,
    disable_logging: bool = False,
):
    """
    Install handler while this context manager is active, return to the old handler upon exit
    :param signalnum: The signal to install the handler for
    :param handler: The signal handler to install
    :param disable_logging: Do not log anything if true
    """
    log = getLogger(__name__)
    name: str = signal.Signals(signalnum).name
    if not disable_logging:
        log.debug("Installing signal handler for %s...", name)
    old = signal.signal(signalnum, handler)
    try:
        yield
    finally:
        if not disable_logging:
            log.debug("Restoring signal handler for %s...", name)
        signal.signal(signalnum, old)
