#!/usr/bin/env bash
# Install Peon Pet: build wheel, install it, and drop the desktop entry + icon.
set -euo pipefail

cd "$(dirname "$0")"

have_cmd() {
  command -v "$1" >/dev/null 2>&1
}

die() {
  echo "ERROR: $*" >&2
  exit 1
}

warn() {
  echo "WARNING: $*" >&2
}

preflight() {
  echo "Checking prerequisites..."

  if ! have_cmd uv; then
    die "uv is required but not found.
Install it with:
  curl -LsSf https://astral.sh/uv/install.sh | sh
Then re-run this script."
  fi

  if ! have_cmd curl; then
    die "curl is required but not found.
Install curl via your package manager, then re-run this script."
  fi

  if ! have_cmd python3 && ! have_cmd python && ! have_cmd py; then
    warn "no system Python found (python3/python/py).
uv will try to fetch a Python runtime on its own."
  fi
}

install() {
  echo "Building wheel..."
  uv build --wheel

  echo "Installing peon-pet to user bin..."
  uv tool install --force dist/peon_pet-*.whl
}

install_desktop() {
  case "$(uname -s)" in
    Linux)
      echo "Installing desktop entry + icon..."
      data_dir="${XDG_DATA_HOME:-$HOME/.local/share}"
      applications_dir="$data_dir/applications"
      icon_dir="$data_dir/peon-pet"
      mkdir -p "$applications_dir" "$icon_dir"
      # Absolute icon path sidesteps the hicolor theme machinery (no index.theme/cache needed).
      icon_path="$icon_dir/peon-pet.png"
      cp src/peon_pet/icons/peon-pet.png "$icon_path" -v
      # Render the desktop entry with the installed icon path.
      sed "s|^Icon=.*|Icon=$icon_path|" peon-pet.desktop > "$applications_dir/peon-pet.desktop"
      update-desktop-database "$applications_dir" 2>/dev/null || true
      ;;
    *)
      warn "Skipping desktop entry + icon (not Linux)."
      ;;
  esac
}

preflight
install
install_desktop

echo "Done. Run 'peon-pet --watch' to start the pet."
