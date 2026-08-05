# Roadmap

Pending work, in rough priority order.

## Rendering / reaction effects

The current `QPainter` path draws the sprite cell + optional border + a numeric session-count badge. The legacy Electron
build layered more on top of the sprite — all pure rendering, no event-source dependency, so re-addable:

- **Per-anim color flash** — done (`AnimConfig.flash` + effect timer; flat `QPainter` fill with alpha decay).
- **Particle burst** — gold confetti on `celebrate`.
- **Screen shake** — jitter the sprite on `annoyed`.
- **Background image** — `bg-pixel.png` behind the sprite (legacy tinted it grey; current has no bg).

These are QoL polish, not core. Particles + shake can reuse the effect timer introduced for flash.
Visual QA: `uv run peon-pet --anim celebrate` (etc.) and `--demo`.

## Cross-platform desktop install

The wheel + `uv tool install` already work everywhere; only desktop glue is Linux-only (`.desktop` / XDG). Share
`install.sh` for Linux and macOS (`Darwin` branch: tool install + optional thin `.app` launcher stub, same idea as
`.desktop` / `.lnk`). Windows gets a separate `install.ps1` (shortcuts + uninstaller beside the shim) — do not force it
into bash. Keep the pure wheel as the single artifact; no frozen exe/DMG until demand. peon-ping state stays
`~/.claude/hooks/peon-ping/.state.json` by default, overridable via `--watch` and later a config `state_path` — do not
mirror peon-ping's install-mode matrix.

## Remote relay sync

peon-ping can relay state to `http://127.0.0.1:19998/state` for sessions from other machines. Legacy polled this every
5s and merged remote sessions into the tracker. Agent-agnostic, but only useful if you run the relay — so low priority
unless someone asks.

## Autostart entry

Probably too intrusive. On Linux, Autostart is basically copy-pasting the .desktop file to
`$HOME/.config/autostart/peon-pet.desktop`. If going to the installer, this should be optional and explicitly asked from
the user.

Linux users usually know how to autostart things. There are visual helpers to edit autostart entries.