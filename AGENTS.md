# Peon Pet — Agent Guide

## Overview

A desktop pet that reacts to peon-ping events. Python + PyQt6.

## Working style

- Always assume the user has changed content between two queries. Therefore, re-read any file you want to touch before
  editing it.
- When the user asks you to write some implementation, insist on a test-first approach. There are acceptable exceptions
  for that, for instance
  - a quick proof something actually is possible
  - something not tested yet
- The point is to make good development practice a habit. Deviations from it should be a deliberate choice.

### Test style

- Use the **AAA pattern** (Arrange / Act / Assert) with a dedicated blank line between each section. Exception: a test
  so simple it reads as a one-liner (e.g. `assert f(x) == y`).
- Name the subject under test `sut`.
- Group related tests in `Test*` classes (PascalCase, no underscores — e.g. `TestColdStart`, `TestPollSuppression`).
  Run one group with `pytest file.py::TestGroupName`. Keep stateless helpers as `_`-prefixed module functions and
  stateful drivers as classes at the bottom of the file.
- Organize test files top-down: test classes first, helpers and driver classes at the bottom (same convention as
  source). Within the tests, lead with the highest-value/most-complex behavior and put trivial checks last — mirrors the
  source rule of "primary entry point up top, helpers below".
- When deliberately testing private/internal API (logic with no public entry point, e.g., mtime/timestamp suppression):
  centralize the private access in a single driver class rather than scattering `w._method()` across every test.
  Document *why* the internal API is tested in the driver's docstring — this makes the smell deliberate and reviewable
  instead of pervasive.

## Tech stack

- **Python ≥ 3.10** with **PyQt6** for the GUI (frameless transparent always-on-top window)
- **uv** for project/env management (`pyproject.toml`, `uv.lock`, `.venv/`)
- **hatchling** build backend; produces an installable wheel
- **basedpyright** for type checking (also the LSP Zed uses)
- **ruff** for pretty formatting here
- **pytest** for tests
- **coverage** for test coverage

## Common commands

```bash
uv sync                     # install deps into .venv (run after pull / pyproject change)
uv run peon-pet --help      # all CLI flags
uv run peon-pet --watch     # the main use case
uv run peon-pet --demo      # visual manual QA
uv build                    # produce wheel in dist/
```

Before passing a result to the user, run the following commands first in this order.

```bash
uv run ruff format .        # pretty formatting
LC_ALL=C uv run basedpyright # type-check (Zed uses the same tool/LSP); LC_ALL=C forces English output
uv run pytest               # run tests
```

## Running on Linux + Wayland

Qt6 should work on Wayland, but if you hit GPU/compositor issues fall back to X11:

```bash
QT_QPA_PLATFORM=xcb uv run peon-pet
```

Be transparent about it to the user.

### Sprite atlases

Each atlas is a grid of sprite frames. Most are 6×6; Layouts are declared in `ATLAS_LAYOUTS` — a new atlas needs its
dimensions registered there. Atlas files live in
`src/peon_pet/assets/`.

### Events

Events use the OG peon-ping/Claude hook names (`SessionStart`, `Stop`, `UserPromptSubmit`, `PermissionRequest`,
`PostToolUseFailure`, `PreCompact`). `idle` is a pseudo-event mapping to `sleeping`. The mapping lives in
`EVENT_TO_ANIM`.

## Conventions

- **Types**: all public code is fully type-annotated. `uv run basedpyright` must stay at 0 warnings. The
  `reportUnknown*` / `reportAny` rules are disabled in `pyrightconfig.json` because PyQt6's stubs type `connect()` slots
  as `Unknown` and argparse returns `Any` — both are ecosystem limitations, not code issues. Don't add
  `# pyright: ignore` for those; the config handles them.
- **Enums**: PyQt6 requires fully-qualified enum access (`Qt.WindowType.FramelessWindowHint`, not
  `Qt.FramelessWindowHint`). Don't use the short form — it doesn't exist at runtime.
- **Overrides**: use `@typing.override` on methods that override QWidget base methods (e.g. `paintEvent`). Don't add it
  to our own methods like `advance`.
- **Assets**: use `importlib.resources` (`files(__package__) / "assets"`) — never `__file__`-relative paths. The latter
  breaks after `pip install`.
- **File layout**: organize files top-down. The primary entry point / public function goes at the top; helpers and data
  classes go below it. Put `if __name__ == "__main__"` at the very bottom of the file, never between functions.
- **ASCII only**: avoid Unicode symbols like arrows (`→`), checkmarks, etc. in code and comments — use plain ASCII
  (`->`, `=>`, words) instead. They don't render reliably across terminals/editors and are hard to type.

## Legacy reference

`legacy/` holds the original Electron + Three.js app. Its source originates from https://github.com/PeonPing/peon-pet.
Do not modify anything unless the user explicitly requests it. Use it as a reference instead. This folder is **not**
version-controlled.
