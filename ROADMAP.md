# Roadmap

Pending work, in rough priority order.

## Installers

Linux first: `.desktop` file + autostart symlink (or systemd user unit). Then
macOS / Windows.

## Config file

`~/.config/peon-pet/config.json` for corner position, character, loops, etc.
(Window position is already persisted there; the rest of the keys are pending.)
Standardize on XDG dirs — the legacy app used `app.getPath('userData')`.

