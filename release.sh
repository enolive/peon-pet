#!/usr/bin/env bash
# Tag and push a release from the version already set in pyproject.toml.
# Bump the version yourself first (e.g. uv version --bump patch), then run this.
set -euo pipefail

cd "$(dirname "$0")"

die() {
  echo "ERROR: $*" >&2
  exit 1
}

RELEASE_PATHS=(pyproject.toml uv.lock)

is_release_path() {
  local candidate="$1" p
  for p in "${RELEASE_PATHS[@]}"; do
    [[ "$candidate" == "$p" ]] && return 0
  done
  return 1
}

# Prints dirty paths (one per line). Aborts if any path is outside the release allowlist.
collect_release_dirty() {
  local line path
  while IFS= read -r line; do
    [[ -z "$line" ]] && continue
    path="${line:3}"
    if [[ "$path" == *" -> "* ]]; then
      path="${path##* -> }"
    fi
    if ! is_release_path "$path"; then
      die "dirty file not allowed for release: ${path}
Commit or stash unrelated changes first. Allowed: ${RELEASE_PATHS[*]}"
    fi
    printf '%s\n' "$path"
  done < <(git status --porcelain)
}

version="$(uv version --short)"
[[ -n "$version" ]] || die "could not read version from pyproject.toml"
tag="v${version}"

git rev-parse --is-inside-work-tree >/dev/null 2>&1 || die "not a git repository"

branch="$(git branch --show-current)"
[[ "$branch" == "main" ]] || die "must be on main (currently on '${branch}')"

if git rev-parse "$tag" >/dev/null 2>&1; then
  die "tag ${tag} already exists locally"
fi

if git ls-remote --exit-code --tags origin "refs/tags/${tag}" >/dev/null 2>&1; then
  die "tag ${tag} already exists on origin"
fi

dirty_files="$(collect_release_dirty)"

echo "About to release ${tag} from branch ${branch} (HEAD $(git rev-parse --short HEAD))"
echo
git status --short
echo
if [[ -n "$dirty_files" ]]; then
  echo "Will commit allowlisted release files, then tag:"
  while IFS= read -r path; do
    [[ -n "$path" ]] && echo "  ${path}"
  done <<<"$dirty_files"
else
  echo "Working tree is clean: will tag the current HEAD."
fi
echo
echo "Then: push ${branch} and tag ${tag} to origin (CI builds the GitHub Release)."
echo

printf "Release %s now? [y/N] " "$tag" >/dev/tty
read -r answer </dev/tty
case "$answer" in
y | Y | yes | YES) ;;
*)
  die "aborted"
  ;;
esac

if [[ -n "$dirty_files" ]]; then
  while IFS= read -r path; do
    [[ -n "$path" ]] && git add -- "$path"
  done <<<"$dirty_files"
  git commit -m "🔖 Release ${tag}"
fi

git tag -a "$tag" -m "🔖 Release ${tag}"
git push origin "$branch"
git push origin "$tag"

echo "Done. CI should publish GitHub Release ${tag}."
