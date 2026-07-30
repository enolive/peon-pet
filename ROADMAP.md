# Roadmap

Pending work, in rough priority order.

## Installers

**Shape: separate `install.sh` script, not a wheel-installed hook.**
Wheels can bundle a `.desktop` file + icon (as package data) but can't install
them to where the desktop environment looks (`~/.local/share/applications/`,
`~/.local/share/icons/`) — wheels only write into the package dir + `bin/`.
So the installer is a standalone script.

### Done

Basic `install.sh` — builds the wheel, `uv tool install --force`s it, copies
the icon to `$XDG_DATA_HOME/peon-pet/peon-pet.png`, and renders the `.desktop`
entry with an absolute `Icon=` path into `$XDG_DATA_HOME/applications/`.
Absolute icon path sidesteps the hicolor theme machinery (no `index.theme` /
cache needed). `update-desktop-database` runs best-effort.

### Remaining

**Web install / `curl … | sh` one-liner.**
`install.sh` should support `curl -fsSL https://…/install.sh | sh` — the web
variant just fetches the wheel first. The script is the single entry point for
both "install from a built wheel" and "install from the web".

**Update.** `peon-pet --update` — curls the latest `install.sh` and pipes it to
`sh`, same as the web install one-liner. `install.sh` detects an already
installed version (via `uv tool list` / checking for the existing binary) and
upgrades in place instead of erroring. So install.sh is idempotent: fresh
install and update are the same code path, distinguished by whether a version
is already present.

**Uninstall.** `peon-pet --uninstall` — a flag on the executable that forwards
  to `uninstall.sh`. The script is installed by `install.sh` to
  `~/.local/bin/peon-pet-uninstall.sh` (next to the `peon-pet` entry point),
  *not* bundled inside the wheel — so the uninstall works even if the Python
  env is broken or the package can't be imported. `peon-pet --uninstall` just
  `exec`s that script. The script removes the XDG files, runs
  `uv tool uninstall peon-pet`, and self-deletes at the end. The flag is a thin
  shell forward, not Python logic — uninstall steps live in one shell script.

**Autostart entry.** `install.sh` optionally drops
  `~/.config/autostart/peon-pet.desktop` so the pet launches on login. Likely a
  `--autostart` flag to `install.sh` (off by default — don't surprise users).

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

**Cross-platform.** Linux only for now. macOS / Windows later — they have
their own bundle formats (`.app` / `.dmg`, `.exe`) and the install model
differs enough that a separate script per platform is cleaner than one
cross-platform script.

## Rendering / reaction effects

The current `QPainter` path draws the sprite cell + optional border + a
numeric session-count badge. The legacy Electron build layered more on top of
the sprite — all pure rendering, no event-source dependency, so re-addable:

- **Per-anim color flash** — a brief tint overlay on `waking`/`alarmed`/
  `celebrate`/`annoyed` (shader in legacy; a flat `QPainter` fill with alpha
  decay would do here).
- **Particle burst** — gold confetti on `celebrate`.
- **Screen shake** — jitter the sprite on `annoyed`.
- **Background image** — `bg-pixel.png` behind the sprite (legacy tinted it
  grey; current has no bg).

These are QoL polish, not core. Flash is the cheapest win; particles + shake
need a small animation driver beyond the sprite timer.

## Optional: remote relay sync

peon-ping can relay state to `http://127.0.0.1:19998/state` for sessions from
other machines. Legacy polled this every 5s and merged remote sessions into the
tracker. Agent-agnostic, but only useful if you run the relay — so low
priority unless someone asks.
