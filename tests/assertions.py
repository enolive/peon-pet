import time
from collections.abc import Callable, Generator
from contextlib import contextmanager


def wait_until(predicate: Callable[[], bool], *, timeout_s: float = 2.0) -> bool:
    """Poll `predicate` every 5ms until it's true or `timeout_s` elapses."""
    deadline = time.monotonic() + timeout_s
    while time.monotonic() < deadline:
        if predicate():
            return True
        time.sleep(0.005)
    return predicate()


@contextmanager
def does_not_raise() -> Generator[None, None, None]:
    """Assert the block does not raise. Symmetric with `pytest.raises`.

    Neither pytest nor the stdlib provides this on Python 3.10–3.12; it's a
    hand-rolled no-op context manager whose only job is to make the intent
    read explicitly at the call site.
    """
    yield
