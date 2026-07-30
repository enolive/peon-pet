# Roadmap

Pending work, in rough priority order.

## Installers

**Shape: separate `install.sh` script, not a wheel-installed hook.**
Wheels can bundle a `.desktop` file + icon (as package data) but can't install
them to where the desktop environment looks (`~/.local/share/applications/`,
`~/.local/share/icons/`) — wheels only write into the package dir + `bin/`.
So the installer is a standalone script that:

1. `uv tool install`s the wheel (or `curl`s it first from a release URL).
2. Copies the bundled `.desktop` + icon out of the installed package into the
   XDG user dirs (no sudo needed).
3. Optionally drops an autostart entry at `~/.config/autostart/peon-pet.desktop`.

This shape also supports the `curl … | sh` one-liner install pattern:

```bash
curl -fsSL https://…/install.sh | sh
```

The script is the single entry point for both “install from a built wheel” and
“install from the web” — the web variant just fetches the wheel first.

**Bundled artifacts (in the wheel, under `peon_pet/assets/`):**
- `peon-pet.desktop` — `Exec=` points at `~/.local/bin/peon-pet` (where `uv tool`
  symlinks the entry point). `Icon=peon-pet`.
- `peon-pet.png` (or reuse `orc-dock-icon.png`) — copied to
  `~/.local/share/icons/peon-pet.png`.

The `.desktop` and icon get bundled via `force-include` (the asset case that
*is* needed — unlike the earlier duplicate-atlas bug, these files live outside
`src/peon_pet/` or are explicitly meant as installable resources).

**Uninstall.** `peon-pet --uninstall` — a flag on the executable that forwards
  to `uninstall.sh`. The script is installed by `install.sh` to
  `~/.local/bin/peon-pet-uninstall.sh` (next to the `peon-pet` entry point),
  *not* bundled inside the wheel — so the uninstall works even if the Python
  env is broken or the package can't be imported. `peon-pet --uninstall` just
  `exec`s that script. The script removes the XDG files, runs
  `uv tool uninstall peon-pet`, and self-deletes at the end. The flag is a thin
  shell forward, not Python logic — uninstall steps live in one shell script.

**Update.** `peon-pet --update` — curls the latest `install.sh` and pipes it to
  `sh`, same as the web install one-liner. `install.sh` detects an already
  installed version (via `uv tool list` / checking for the existing binary) and
  upgrades in place instead of erroring. So install.sh is idempotent: fresh
  install and update are the same code path, distinguished by whether a version
  is already present.

**Preflight.** `install.sh` checks for required tools before doing anything,
  and exits with a clear message if missing:
- `curl` — needed for the web install / update flow (no-op when installing from
  a local wheel, but the check is cheap and the message is clearer than a later
  `command not found`).
- `uv` — needed to install the wheel into an isolated env.
- `python3` (or `python` / `py` fallback) — `uv` can fetch its own Python
  (`uv tool install --python 3.12`), so a missing system Python isn't fatal;
  the preflight just warns and lets `uv` resolve one. Hard fail only if neither
  `uv` nor a system Python is usable.

Missing `uv` is the common case on a fresh box — the message should suggest the
  one-liner from the uv docs (`curl -LsSf https://astral.sh/uv/install.sh | sh`)
  rather than just failing.

**Scope for now:** Linux only. macOS / Windows later — they have their own
bundle formats (`.app` / `.dmg`, `.exe`) and the install model differs enough
that a separate script per platform is cleaner than one cross-platform script.


