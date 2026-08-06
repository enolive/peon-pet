# Peon Pet - Agent Guide

## Overview

A desktop pet that reacts to peon-ping events. Python + PySide6.

## Working style

- Always assume the user has changed content between two queries. Therefore, re-read any file you want to touch before
  editing it.
- When the user asks you to write some implementation, insist on a test-first approach. There are acceptable exceptions
  for that. The point is to make good development practice a habit. Deviations from it should be a deliberate choice.
  For instance:
  - a quick proof something actually is possible
  - something not tested yet
  - trivial shell glue (`release.sh`, one-shot install helpers) where a pytest wrapper would only assert
    `bash -n` / executable bits - that is ceremony, not coverage. Don't add tests just to satisfy TDD optics.

### Test style

- Use the **AAA pattern** (Arrange / Act / Assert) with a dedicated blank line between each section. Exception: a test
  so simple it reads as a one-liner (e.g. `assert f(x) == y`).
- Name the subject under test `sut`.
- Group related tests in `Test*` classes (PascalCase, no underscores - e.g. `TestColdStart`, `TestPollSuppression`). Run
  one group with `pytest file.py::TestGroupName`. Keep stateless helpers as `_`-prefixed module functions and stateful
  drivers as classes at the bottom of the file.
- Organize test files top-down: test classes first, helpers and driver classes at the bottom (same convention as
  source). Within the tests, lead with the highest-value/most-complex behavior and put trivial checks last - mirrors the
  source rule of "primary entry point up top, helpers below".
- When deliberately testing private/internal API (logic with no public entry point, e.g., mtime/timestamp suppression):
  <!-- agnix-disable-next-line CDX-AG-005 -->
- centralize the private access in a single driver class rather than scattering `w._method()` across every test.
  Document *why* the internal API is tested in the driver's docstring - this makes the smell deliberate and reviewable
  instead of pervasive.

## Tech stack

- **Python >= 3.12** with **PySide6** for the GUI (frameless transparent always-on-top window)
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
uv run ruff format .         # pretty formatting
uv run ruff check .         # pretty formatting
LC_ALL=C uv run basedpyright # type-check. LC_ALL=C forces English output
uv run pytest                # run tests
```

## Releases

- Version source of truth is `pyproject.toml` only (no `__version__` mirror).
- **Do not** create release tags, push `v*` tags, or craft GitHub Releases by hand.
- Ask the user to do that by increasing the version in `pyproject.toml` and running `./release.sh`.
- That script confirms with an explicit `y/N` prompt; may auto-commit `pyproject.toml` / `uv.lock` if those are the only
  dirty files, then tags `vX.Y.Z` and pushes so CI can publish the release assets. Any other dirty files abort the
  release.

### Sprite atlases

Each atlas is a grid of sprite frames. Most are 6x6; Layouts are declared in `ATLAS_LAYOUTS` - a new atlas needs its
dimensions registered there. Atlas files live in
`src/peon_pet/assets/`.

### Events

Events use the OG peon-ping/Claude hook names (`SessionStart`, `Stop`, `UserPromptSubmit`, `PermissionRequest`,
`PostToolUseFailure`, `PreCompact`). `idle` is a pseudo-event mapping to `sleeping`. The mapping lives in
`EVENT_TO_ANIM`.

## Conventions

- **Types**: all public code is fully type-annotated. `uv run basedpyright` must stay at 0 warnings. Don't add any new
  pyright suppressions silently. Instead, state this to the user and ask for review and consent.
- **Enums**: PySide6 requires fully-qualified enum access (`Qt.WindowType.FramelessWindowHint`, not
  `Qt.FramelessWindowHint`). Don't use the short form - it doesn't exist at runtime.
- **Signals**: use `QtCore.Signal` (not PyQt's `pyqtSignal`).
- **Overrides**: use `@typing.override` on methods that override QWidget base methods (e.g. `paintEvent`). Don't add it
  to our own methods like `advance`.
- **Assets**: use `importlib.resources` (`files(__package__) / "assets"`) - never `__file__`-relative paths. The latter
  breaks after `pip install`.
- **File layout**: organize files top-down. The primary entry point / public function goes at the top; helpers and data
  classes go below it. Put `if __name__ == "__main__"` at the very bottom of the file, never between functions.
- **WET over premature DRY**: prefer a second local copy over a shared helper until a third real call site (or a clear
  shared owner) appears. Tiny utilities (`_noop`, one-line adapters) stay module-private. When you do duplicate, keep
  signatures aligned so extraction later is mechanical, not a redesign.
- **ASCII only**: avoid Unicode symbols like arrows (`->`), checkmarks, em dashes (`—`), ellipses (`…`), etc. in code
  and comments - use plain ASCII (`-`, `->`, `=>`, `...`, words) instead. They don't render reliably across
  terminals/editors and are hard to type.
- **Comments**: avoid them. Prefer self-documenting code (clear names, small functions) over comments that restate what
  the code does. A comment is justified only when it captures a *why* the code can't - a non-obvious constraint, a
  workaround, or intent that isn't visible in the code. Don't write comments that narrate the code.
- **Docstrings**: keep them to a minimum. A module or function docstring is justified only when the name and signature
  <!-- agnix-disable-next-line PE-006 - not a negative instruction  -->
  don't already convey the contract - e.g. a non-obvious invariant, a responsibility the code can't show, or a *why*
  that would otherwise need a comment. Don't restate what the code does; don't pad. The one standing exception is the
  driver-class docstring in tests (see Test style) that documents *why* internal API is under test.

## Legacy reference

`legacy/` holds the original Electron + Three.js app. Its source originates from https://github.com/PeonPing/peon-pet.
Do not modify anything unless the user explicitly requests it. Use it as a reference instead. This folder is **not**
version-controlled.

## References

- `docs/ARCHITECTURE.md` for the overall architecture and design decisions.
- `docs/ROADMAP.md` for the project roadmap.