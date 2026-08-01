"""Tests for Demo's cycling and stop behavior.

`Demo` cycles through every `Anim` on a daemon thread, emitting each via
`on_anim_changed`. The unit tests drive the real thread with a short interval
and a sleep-poll helper (no Qt, no event loop — `Demo` is pure Python).
"""

import time

from peon_pet.config import Anim
from peon_pet.demo import Demo
from tests.assertions import wait_until


def test_emits_every_anim_then_wraps_to_sleeping() -> None:
    # The cycle skips the initial SLEEPING (the window starts on it), then emits
    expected_cycle: list[Anim] = [
        Anim.WAKING,
        Anim.TYPING,
        Anim.ALARMED,
        Anim.CELEBRATE,
        Anim.ANNOYED,
        Anim.SLEEPING,
    ]
    seen: list[Anim] = []
    sut = Demo(on_anim_changed=seen.append, interval_s=0.05)
    try:
        sut.start()

        # Wait until the cycle has come back around to SLEEPING — that proves
        # it traversed every anim and wrapped, not just emitted a fixed list.
        assert wait_until(lambda: len(seen) == len(expected_cycle))
        assert seen == expected_cycle
    finally:
        sut.stop()


def test_stop_halts_emission() -> None:
    seen: list[Anim] = []
    sut = Demo(on_anim_changed=seen.append, interval_s=0.05)
    sut.start()
    assert wait_until(lambda: len(seen) >= 1)

    sut.stop()
    last_seen_at_stop = seen[-1]
    # A short sleep (not _wait_until) is right here: asserting the *absence*
    # of a change, so give it time to (not) happen, then check it didn't.
    time.sleep(0.2)

    assert seen[-1] == last_seen_at_stop
