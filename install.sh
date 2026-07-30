#!/usr/bin/env bash
# Install Peon Pet: build wheel, install it, and drop the desktop entry + icon.
set -euo pipefail

cd "$(dirname "$0")"

echo "Building wheel..."
uv build --wheel

echo "Installing peon-pet to user bin..."
uv tool install --force dist/peon_pet-*.whl

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
    echo "Skipping desktop entry + icon (not Linux)."
    ;;
esac

echo "Done. Run 'peon-pet --watch' to start the pet."
