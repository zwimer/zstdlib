from collections.abc import Callable, Iterator
from contextlib import contextmanager
from logging import getLogger
import signal


@contextmanager
def signal_cm(
    signalnum: signal.Signals | int,
    handler: signal.Handlers | Callable,
    *,
    disable_logging: bool = False,
) -> Iterator[None]:
    """Install handler while this context manager is active, return to the old handler upon exit

    Args:
        signalnum: The signal to install the handler for
        handler: The signal handler to install
        disable_logging: Do not log anything if true
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
