# Roadmap

Pending work, in rough priority order.

## Tray icon

`QSystemTrayIcon` with Show/Hide + Quit. Replaces the macOS-only `app.dock`
menu from the legacy Electron app.

## Installers

Linux first: `.desktop` file + autostart symlink (or systemd user unit). Then
macOS / Windows.

## Config file

`~/.config/peon-pet/config.json` for corner position, character, loops, etc.
(Window position is already persisted there; the rest of the keys are pending.)
Standardize on XDG dirs — the legacy app used `app.getPath('userData')`.

## Session staleness reconciliation

**Priority: after the tray icon.** The mechanism is well-understood and the
lock is already in place on `_SessionRegistry`. As a user action (not a
background timer), the `max_age` heuristic problem disappears — the user is the
heuristic. Blocked on the tray icon existing, since that's where the "reset to
idle" entry lives.

**Problem.** If a session's end event (`Stop` / `SessionEnd`) is lost in
transit — watcher polls only `last_active`, so two events inside the same 500 ms
window collapse to one — the session stays in `_SessionRegistry` forever and the
pet never returns to idle. The "lost end → never idle" failure mode.

**Mechanism: user action, not background.** Triggered from the tray icon (a
"reset to idle" entry), not a background timer. The user is the heuristic: if the
pet looks stuck typing, click reset; if not, nothing happens. This sidesteps the
`max_age` question entirely — no principled value exists, the wrong guess is
user-visible, and a background reaper risks reaping a slow-but-live agent
mid-task. A user action owns that judgement call instead.

Split along the existing `_SessionRegistry` / `PetStateMachine` boundary —
data vs. emit:

- **`_SessionRegistry.clear() -> bool`** — pure data work. Drops all sessions;
  returns whether the set *transitioned* to empty (was non-empty before, empty
  after). Owns no callbacks, knows nothing about anims. (Per-session dismissal is
  a future refinement — a tray submenu listing sessions — but "clear all" is the
  right first cut since the user is reacting to "something is stuck".)

  ```python
  def clear(self) -> bool:
      with self._lock:
          was_active = bool(self.sessions)
          self.sessions.clear()
          return was_active
  ```

- **`PetStateMachine.reset()`** — calls the registry, then emits `base_anim`
  (SLEEPING) *only* if the registry reports it just emptied. This is the state
  machine's actual job: deciding when an anim change crosses the wire. It owns
  the `on_anim_changed` callback; the registry doesn't.

  ```python
  def reset(self) -> None:
      if self._sessions.clear():
          self.on_anim_changed(self.base_anim)
  ```

This mirrors how `handle_event` / `on_finished` already work: registry mutates,
state machine decides whether to emit.

**Placement.** `state.py`, on both classes. Triggered from the tray icon (see
above) — no timer, no background thread. The state machine still owns no timers.

**Lock.** Already in place — `_lock` lives on `_SessionRegistry`, and its
methods (`add`, `discard`, `active`) take it internally. `clear` is another
mutating method on the registry and follows the same pattern.
`PetStateMachine`'s `handle_event` / `on_finished` don't take the lock; they
call registry methods that do. The `on_anim_changed` callback fires after the
registry method returns (lock released), so a re-entrant callback can't deadlock.

**Out of scope here.** Auto-cleanup of peon-ping's own `session_start_times`
(that's peon-ping's data, not ours). Persisting the registry across restarts
(deliberately not done — `.state.json` is the source of truth on every launch).
A background/timer-based reaper (deferred indefinitely — see the user-action
rationale above; revisit only if the manual reset proves insufficient in
practice).
