from functools import wraps, partial
import logging as log

from rich.console import Console

_debug = False


def setup_logging(debug: bool = False):
    log_level = log.INFO
    global _debug
    _debug = debug
    if debug:
        log_level = log.DEBUG
    log.basicConfig(level=log_level, format='%(asctime)s - %(levelname)s - %(message)s')


def catch_exception(func=None, *, handle):
    if not func:
        return partial(catch_exception, handle=handle)

    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except handle as e:
            if _debug:
                Console().print_exception()
            else:
                log.error("An error occurred: " + str(e))
            exit(1)
        except KeyboardInterrupt:
            log.error("Command was interrupted, exiting.")
            exit(2)

    return wrapper
