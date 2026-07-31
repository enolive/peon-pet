# Testing plan

How to test peon-pet. The project follows the humble-dialog pattern: pure logic (state, watcher, prefs, config) is
trivially testable; the "dialog"
(`PetWindow` rendering) and the wiring (`__main__`) need more thought.

## Tooling

- **`pytest-qt`** as a dev dep — provides `qtbot`, `QSignalSpy`, the `qapp`
  fixture, and signal-wait helpers. The standard PyQt6 test harness.
- **`tests/`** directory (not type-checked — `pyrightconfig.include` is
  `src` only).
- **`force_qt_offscreen.py`** with a session fixture that sets `QT_QPA_PLATFORM=offscreen`
  so Qt constructs without a display.

## What's easy (pure, no Qt)

These are the humble side — fake callbacks / tmp files, no Qt, no display.

### `state.py` — highest value

Drive `PetStateMachine.handle_event` with recording `on_anim_changed` /
`on_session_count_changed` callbacks, assert the emitted anim + count for every transition.

- IDLE ↔ ACTIVE flips (`UserPromptSubmit` / `PreToolUse` / `PostToolUse` → ACTIVE → TYPING; `Stop` → IDLE → SLEEPING).
- `SessionEnd` removes the session (count drops, base → SLEEPING).
- `clear()` emits-on-change only if a session was known.
- `resolve_anim` fallback to base when no reaction entry.
- Unknown event → stderr message, no emit.

**Cold-start matrix** (the logic we just built) as a table test — empty registry, first event of each type:

| event            | session added? | anim     |
|------------------|----------------|----------|
| SessionStart     | yes            | waking   |
| UserPromptSubmit | yes            | waking   |
| PreToolUse       | yes            | waking   |
| PostToolUse      | yes            | waking   |
| Stop             | yes            | waking   |
| SessionEnd       | no             | sleeping |

The `SessionEnd` row is the exception: the session was never tracked and
`discard` leaves it absent, so nothing to wake for — falls through to
`resolve_anim` → no reaction → `base_anim` (SLEEPING). Every other cold event registers the session (alive-if-new
recovery) and announces with `waking`.

### `watcher.py`

Tmp state file via `tmp_path`. Write `last_active`, start watcher, assert
`on_event(event, sid)`. Then:

- Unchanged mtime → no re-emit.
- New mtime, equal timestamp → suppressed.
- New mtime, newer timestamp → emits.
- Malformed JSON / missing file → no emit (no crash).

### `prefs.py`

Point `XDG_CONFIG_HOME` at `tmp_path`:

- Defaults when config absent.
- Valid atlas read; `ValueError` on bad atlas name (with available list in the message).
- `loops` read / default.
- Position save → read round-trip.

### `config.py`

Invariant asserts (catches the class of bugs `_warn_missing_anims` detects at runtime):

- Every `Anim` has an `AnimConfig`.
- Every `ANIM_CONFIG` row < its atlas's `rows` (so no anim falls back to row 0 on a given atlas).

## The dialog: `PetWindow`

The animation loop (`play` / `advance` / frame stepping, loop counting,
`finished` emission) is **not** worth extracting into its own class. The logic is integer arithmetic — a test that
asserts `frame == 5` after 5 advances just transcribes the `+= 1` back at itself. That's the "tests that restate the
implementation" trap: busywork that looks like coverage. Mishaps here are better caught visually (demo mode exists for
exactly this).

The genuine logic worth testing is the **sprite-map math** and the **missing-row detection** — but as **module-level
functions in `window.py`**, not a new class and not a `utils.py` (no junk drawers). Keep them where the domain is;
`PetWindow` calls them; the methods become thin.

- `cell_rect(frame, row, cell_w, cell_h) -> QRectF` — the "which sprite" math currently inlined in `paintEvent`.
  `QRectF` is a value type, no
  `QApplication` needed to construct or assert on it. Tests: `frame=0,row=0` → top-left origin; `frame=5,row=2` → x =
  `5*cell_w`, y = `2*cell_h`.
- `missing_anims(rows) -> list[Anim]` — the row-count check currently in
  `_warn_missing_anims`. Pure given `rows`. Tests: `missing_anims(6) == []`; `missing_anims(4) == [CELEBRATE, ANNOYED]`.
  The actual stderr print stays in the method.

The one widget-level test with real regression value is the **`finished`
boundary** — it emits exactly once at `frames * loops`, holds the last frame, and looping anims never emit. That's the
contract the state machine depends on. Test it directly on the widget with offscreen Qt + `QSignalSpy`, no extraction:

```python
def test_one_shot_emits_finished_at_boundary(qtbot):
    win = PetWindow(make_prefs())  # offscreen
    win.play(Anim.WAKING)
    spy = QSignalSpy(win.finished)
    for _ in range(ANIM_CONFIG[Anim.WAKING].frames * win.loops):
        win.advance()
    assert len(spy) == 1
    assert win.frame == ANIM_CONFIG[Anim.WAKING].frames - 1
```

Single test, real object, covers the one non-trivial contract. Skip the rest of playback testing.

### Visual smoke test (not full regression)

Full pixel-baseline visual regression is not worth it here. The window is almost entirely fixed-asset bitmap blits
(sprite atlas cell + border PNG, fixed transform) — about as stable as Qt rendering gets, and either right or visibly
wrong, with demo mode already covering visual QA. Per-pixel baselines would mostly assert "the atlas still blits" — low
signal, ongoing maintenance (regenerate on every intentional change, tolerate cross-platform / font differences), and
the one fragile element (badge text, font-dependent) is exactly where pixel comparison helps least.

What's worth it is a **smoke test** using `QWidget.grab()` (returns a `QPixmap`, offscreen Qt renders without a
display): construct the window, `play(WAKING)`,
`grab()`, assert the image isn't empty and has non-transparent pixels in the sprite region. Catches the "rendered
nothing" / compositing-broke class of regressions without baseline maintenance. One test, no committed PNGs.

## The wiring: `__main__.py`

`main()` is one long function mixing argparse, Qt construction, single instance, and signal wiring. Two layers.

### 1. Extract + unit-test pure helpers (no Qt)

Keep them in `__main__.py` — the `if __name__ == "__main__"` guard means importing the module doesn't run `main()`, so
tests can `from peon_pet.__main__
import _resolve_anim` safely. No `utils.py`.

- `_parse_args(argv) -> CliArgs` — feed argv, assert fields. (`CliArgs` is already the seam.)
- `_resolve_anim(arg)` — happy path returns the `Anim`; error path currently
  `sys.exit`s, so assert it raises `SystemExit` (or refactor to raise
  `ValueError` and let `main` exit — cleaner, testable without catching
  `SystemExit`).
- `_print_event_anim_mapping()` — `capsys`, assert the printed lines.
- `_claim_single_instance(app)` — the one tricky bit: it hardcodes the server name `"peon-pet"`, so tests collide with
  each other / a running instance. **Give it a `name` param (default `"peon-pet"`)** and inject a unique name in tests.
  Then: second call on the same name exits; a unique name succeeds.

### 2. Integration test of the wired chain

The real "wiring" test — the part that's hard to test in isolation but matters most. With offscreen Qt + `pytest-qt`,
run `main(["--watch",
str(tmp_state)])` but break the blocking `app.exec()`: schedule a
`QTimer.singleShot` that writes an event to the temp state file, then
`app.quit()` after a `qtbot.waitSignal`. Assert `win.anim` changed to the expected anim. Exercises watcher → state →
seam → window end-to-end with no display and no real peon-ping. Skip the single-instance collision via the injectable
name.

## Suggested order

1. Tooling: `pytest-qt` dev dep, `tests/` dir, `force_qt_offscreen.py` offscreen fixture.
2. `state.py` tests (incl. cold-start matrix) — pure, immediate, highest value.
3. `watcher.py` + `prefs.py` + `config.py` — pure, quick.
4. Extract `cell_rect` / `missing_anims` in `window.py` + their tests; add the single `finished`-boundary widget test.
5. Extract `_parse_args` / `_resolve_anim` / `_print_event_anim_mapping` /
   `_claim_single_instance` name param in `__main__.py` + unit tests.
6. The `--watch` integration test.
