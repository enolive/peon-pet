"""Demo mode - cycles every Anim forever, for visual QA.

Pure Python like the watcher: a daemon thread calls `on_anim_changed` every
`interval` seconds; `__main__` marshals it onto the GUI thread via the seam,
same as for the state machine. Each anim is played with `play_forever=True` (the
window loops its frames instead of emitting `finished`) so one-shots cycle
visibly with no freeze - the demo just advances on its timer.
"""

from __future__ import annotations

import threading
from collections.abc import Callable
from itertools import cycle
from typing import final

from .config import Anim

DEFAULT_INTERVAL_S = 3.0

OnAnim = Callable[[Anim], None]


@final
class Demo:
    def __init__(
        self,
        on_anim_changed: OnAnim,
        interval_s: float = DEFAULT_INTERVAL_S,
    ) -> None:
        self._interval = interval_s
        self._it = cycle(Anim)
        next(self._it)  # skip SLEEPING, which the window starts on
        self.on_anim_changed = on_anim_changed
        self._stop = threading.Event()

    def start(self) -> None:
        self._stop.clear()
        thread = threading.Thread(target=self._run, daemon=True)
        thread.start()

    def stop(self) -> None:
        self._stop.set()

    def _run(self) -> None:
        # Emit the first anim immediately so the demo starts without waiting
        # a full interval, then advance on the timer.
        self._emit()
        while not self._stop.wait(self._interval):
            self._emit()

    def _emit(self) -> None:
        self.on_anim_changed(next(self._it))
