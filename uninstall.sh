#!/usr/bin/env bash
# Remove Peon Pet: desktop entry, icon, uv tool, and this script.
set -euo pipefail

warn() {
  echo "WARNING: $*" >&2
}

have_cmd() {
  command -v "$1" >/dev/null 2>&1
}

echo "Uninstalling peon-pet..."

data_dir="${XDG_DATA_HOME:-$HOME/.local/share}"
applications_dir="$data_dir/applications"
icon_dir="$data_dir/peon-pet"

rm -f "$applications_dir/peon-pet.desktop"
rm -rf "$icon_dir"
update-desktop-database "$applications_dir" 2>/dev/null || true

if ! have_cmd uv; then
  warn "uv not found; skipped uv tool uninstall."
elif uv tool list 2>/dev/null | grep -q '^peon-pet '; then
  uv tool uninstall peon-pet
else
  warn "peon-pet is not installed as a uv tool (skipping uv tool uninstall)."
fi

self="${BASH_SOURCE[0]:-}"
if [[ -n "$self" && -f "$self" ]]; then
  rm -f "$self"
fi

echo "Done. Config under ${XDG_CONFIG_HOME:-~/.config}/peon-pet was left in place."
echo "Thank you for using peon-pet!"
