# Peon Pet — Agent Guide

A desktop pet that reacts to peon-ping events. Python + PyQt6.

## Working style

Always assume the user has changed content between two queries.
Therefore, re-read any file you want to touch before editing it.

## Tech stack

- **Python ≥ 3.10** with **PyQt6** for the GUI (frameless transparent always-on-top window)
- **uv** for project/env management (`pyproject.toml`, `uv.lock`, `.venv/`)
- **hatchling** build backend; produces an installable wheel
- **basedpyright** for type checking (also the LSP Zed uses)
- **pytest** for tests (none yet)

## Project layout

```
peon-pet/
├── pyproject.toml          # project metadata + deps + scripts
├── uv.lock                 # pinned lockfile (do not hand-edit)
├── pyrightconfig.json      # type-checker config
├── src/peon_pet/
│   ├── __init__.py
│   ├── __main__.py         # entry point: argparse, Qt event loop
│   ├── config.py           # atlas layouts, ANIM_CONFIG, EVENT_TO_ANIM
│   ├── window.py           # PetWindow (frameless widget + animation state machine)
│   └── assets/             # PNG atlases + borders (bundled as package data)
└── legacy/                 # old Electron/JS project — read-only reference
```

## Common commands

```bash
uv sync                     # install deps into .venv (run after pull / pyproject change)
uv run peon-pet             # run the app (default: peon atlas, idle)
uv run peon-pet --atlas orc --event Stop --loops 2
uv run peon-pet --help      # all CLI flags
uv run basedpyright         # type-check (Zed uses the same tool/LSP)
uv run pytest               # run tests
uv build                    # produce wheel in dist/
```

## Running on Linux + Wayland

Qt6 usually works on Wayland, but if you hit GPU/compositor issues fall back to X11:

```bash
QT_QPA_PLATFORM=xcb uv run peon-pet
```

### Sprite atlases

Each atlas is a grid of sprite frames. Most are 6×6; `laptop-guy` is 6×4. Layouts are declared in `ATLAS_LAYOUTS` — a new atlas needs its dimensions registered there before `--atlas <name>` will resolve it. Atlas files live in `src/peon_pet/assets/` and are bundled into the wheel via hatchling's `force-include`.

### Events

Events use the OG peon-ping/Claude hook names (`SessionStart`, `Stop`, `UserPromptSubmit`, `PermissionRequest`, `PostToolUseFailure`, `PreCompact`). `idle` is a pseudo-event mapping to `sleeping`. The mapping lives in `EVENT_TO_ANIM`.

## Conventions

- **Types**: all public code is fully type-annotated. `uv run basedpyright` must stay at 0 warnings. The `reportUnknown*` / `reportAny` rules are disabled in `pyrightconfig.json` because PyQt6's stubs type `connect()` slots as `Unknown` and argparse returns `Any` — both are ecosystem limitations, not code issues. Don't add `# pyright: ignore` for those; the config handles them.
- **Enums**: PyQt6 requires fully-qualified enum access (`Qt.WindowType.FramelessWindowHint`, not `Qt.FramelessWindowHint`). Don't use the short form — it doesn't exist at runtime.
- **Overrides**: use `@typing.override` on methods that override QWidget base methods (e.g. `paintEvent`). Don't add it to our own methods like `advance`.
- **Assets**: use `importlib.resources` (`files(__package__) / "assets"`) — never `__file__`-relative paths. The latter breaks after `pip install`.
- **File layout**: organize files top-down. The primary entry point / public function goes at the top; helpers and data classes go below it. Put `if __name__ == "__main__"` at the very bottom of the file, never between functions.

## Legacy reference

`legacy/` holds the original Electron + Three.js app. It's kept for reference (sprite assets were copied from `legacy/renderer/assets/`). Don't modify it. The key lesson from its history: the JSONL transcript watcher (`legacy/lib/jsonl-watcher.js`) was a misguided "decoupling" that re-coupled to Claude Code's private transcript format — the rebuild deliberately reads peon-ping's agent-agnostic state file instead.
