# Roadmap

Pending work, in rough priority order.

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

## Background Image

(`bg-pixel.png`, legacy grey tint) — worth considering for **transparent sprites on a bare canvas** (contrast against
busy wallpapers). Not useful while atlases ship with their own border/frame; a full-rect bg tends to fight the
floating-pet look. Revisit if a borderless atlas lands or users report wallpaper clash.