#!/usr/bin/env bash
# Install Peon Pet: wheel + desktop entry + icon.
#
# Local checkout:
#   ./install.sh
#
# Web (GitHub Release):
#   curl -fsSL https://github.com/enolive/peon-pet/releases/latest/download/install.sh | bash
set -euo pipefail

RELEASE_BASE="https://github.com/enolive/peon-pet/releases"

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

usage() {
  cat <<'EOF'
Usage: install.sh

Modes:
  Local  - running from a source checkout (builds the wheel with uv)
  Web    - otherwise (downloads latest wheel + desktop assets from GitHub Releases)
EOF
}

resolve_script_dir() {
  local src="${BASH_SOURCE[0]:-}"
  case "$src" in
  "" | bash | sh | -bash | -sh)
    return 1
    ;;
  esac
  [[ -f "$src" ]] || return 1
  cd "$(dirname "$src")" && pwd
}

is_local_checkout() {
  local root="${1:-}"
  [[ -n "$root" && -f "$root/pyproject.toml" && -d "$root/src/peon_pet" ]]
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

resolve_latest_version() {
  local url tag
  url="$(curl -fsSLI -o /dev/null -w '%{url_effective}' "${RELEASE_BASE}/latest")"
  tag="${url##*/}"
  [[ -n "$tag" && "$tag" != "latest" ]] || die "could not resolve latest release from ${RELEASE_BASE}/latest"
  echo "${tag#v}"
}

download() {
  local url="$1"
  local dest="$2"
  echo "Downloading ${url}..."
  curl -fsSL "$url" -o "$dest" || die "download failed: $url"
}

install_wheel() {
  local wheel="$1"
  [[ -f "$wheel" ]] || die "wheel not found: $wheel"
  echo "Installing peon-pet to user bin..."
  uv tool install --force "$wheel"
}

install_desktop() {
  local icon_src="$1"
  local desktop_src="$2"

  case "$(uname -s)" in
  Linux)
    echo "Installing desktop entry + icon..."
    local data_dir="${XDG_DATA_HOME:-$HOME/.local/share}"
    local applications_dir="$data_dir/applications"
    local icon_dir="$data_dir/peon-pet"
    mkdir -p "$applications_dir" "$icon_dir"
    # Absolute icon path sidesteps the hicolor theme machinery (no index.theme/cache needed).
    local icon_path="$icon_dir/peon-pet.png"
    cp "$icon_src" "$icon_path" -v
    sed "s|^Icon=.*|Icon=$icon_path|" "$desktop_src" >"$applications_dir/peon-pet.desktop"
    update-desktop-database "$applications_dir" 2>/dev/null || true
    ;;
  *)
    warn "Skipping desktop entry + icon (not Linux)."
    ;;
  esac
}

install_local() {
  local root="$1"
  echo "Local checkout detected at $root"
  cd "$root"

  echo "Building wheel..."
  uv build --wheel

  local wheel
  wheel="$(find dist -name 'peon_pet-*.whl' | sort | tail -n1)"
  install_wheel "$wheel"
  install_desktop \
    "$root/src/peon_pet/icons/peon-pet.png" \
    "$root/peon-pet.desktop"
}

install_web() {
  local work
  work="$(mktemp -d --tmpdir peon-pet-install.XXXXXX)"
  # expand $work - EXIT runs after locals are gone
  # shellcheck disable=SC2064
  trap "rm -rf $(printf '%q' "$work")" EXIT

  echo "Resolving latest release..."
  local version
  version="$(resolve_latest_version)"
  [[ "$version" =~ ^[0-9] ]] || die "invalid version: $version"

  local tag="v${version}"
  local base="${RELEASE_BASE}/download/${tag}"
  local wheel_name="peon_pet-${version}-py3-none-any.whl"

  echo "Installing from GitHub release ${tag}..."
  download "${base}/${wheel_name}" "${work}/${wheel_name}"
  download "${base}/peon-pet.desktop" "${work}/peon-pet.desktop"
  download "${base}/peon-pet.png" "${work}/peon-pet.png"

  install_wheel "${work}/${wheel_name}"
  install_desktop "${work}/peon-pet.png" "${work}/peon-pet.desktop"
}

main() {
  preflight

  local script_dir=""
  script_dir="$(resolve_script_dir || true)"

  if is_local_checkout "$script_dir"; then
    install_local "$script_dir"
  else
    install_web
  fi

  echo "Done. Run 'peon-pet --watch' to start the pet."
}

main "$@"
