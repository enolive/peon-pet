# Roadmap

Pending work, in rough priority order.

## Rendering / reaction effects

Pure paint/timer polish on top of the sprite — no event-source changes. Iterate one effect per slice; each needs eyes
via `--anim <name>` / `--demo` (not worth automating).

### Done

- **Per-anim color flash** — `AnimConfig.flash: FlashConfig | None` with `Rgba.from_hex("#RRGGBB", a=...)` + decay.
  Effect timer (~60fps) while live. Paint order: sprite → border → flash → badge (flash above border, legacy z-order).
  Pure helpers in `effects.py`. Optional effects live on `AnimConfig` (sane middle: no EffectConfig hierarchy / Noop).
- **Screen shake** on `annoyed` — `AnimConfig.shake: ShakeConfig | None` (intensity 12, decay 8). Jitters the **sprite
   draw offset** only (not the window). Shares the effect timer with flash. QA: `uv run peon-pet --anim annoyed`.
- **Particle burst** on `celebrate` — `AnimConfig.particles: ParticleConfig | None` (30 gold confetti, 1.2s).
  Pure spawn/step/opacity in `effects.py`; drawn above flash. QA: `uv run peon-pet --anim celebrate`.

### Next (reuse the effect timer)

1. **Background image** — `bg-pixel.png` under the sprite (legacy grey tint). Independent of motion FX; easy rollback
   if it fights the frameless look.

### Conventions (carry forward)

- Trigger only from `PetWindow.play()` via `ANIM_CONFIG[anim]` fields; state machine untouched.
- Redundant `play` (same anim+loop) stays a no-op — do not re-arm effects mid-cycle.
- A real anim switch clears residual FX first, then arms the new anim's effects (no shake bleed into sleeping).
- Test pure math with Hypothesis where the space is large (`decay_linear`, `shake_offset` bounds, `Rgba.from_hex`);
  `play()` effect clear/re-arm is a couple of focused examples. Not `paintEvent`. Visual sign-off before the next slice.
- Hardcode legacy constants first; prefs toggles only if someone asks.

### Out of scope here

Shader parity, screenshot tests, new events/anims, installers/relay.

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