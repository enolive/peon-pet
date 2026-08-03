#!/usr/bin/env bash
set -euo pipefail

./agent-lint.sh
uv run ruff format --check .
uv run ruff check .
LC_ALL=C uv run basedpyright
