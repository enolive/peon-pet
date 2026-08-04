#!/usr/bin/env bash
# Tag and push a release from the version already set in pyproject.toml.
# Bump the version yourself first (e.g. uv version --bump patch), then run this.
set -euo pipefail

cd "$(dirname "$0")"

die() {
  echo "ERROR: $*" >&2
  exit 1
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

echo "About to release ${tag} from branch ${branch} (HEAD $(git rev-parse --short HEAD))"
echo
git status --short
echo
if [[ -n "$(git status --porcelain)" ]]; then
  die "Working tree is dirty: aborting."
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

git tag -a "$tag" -m "🔖 Release ${tag}"
git push origin "$branch"
git push origin "$tag"

echo "Done. CI should publish GitHub Release ${tag}."
