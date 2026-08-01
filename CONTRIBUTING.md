# Contributing Guide

Thanks for your interest in contributing.

## Useful scripts

These will also be run in the CI/CD pipeline. Make sure to run them beforehand to get faster feedback about the overall
quality.

```bash
# lint agent configs
./aget-lint.sh
# install all dependencies
uv sync
# format files
uv run ruff format .
# type check project
uv run basedpyright
# run all tests
uv run pytest
# run all tests with coverage
uv run coverage run -m pytest 
# generate coverage report
uv run coverage report
```

Run the tool from the command line in DEBUG mode:

```bash
uv run peon-pet --watch -vv
```

# Notes

Please keep changes focused and include tests or docs when behavior changes.

* Keep implementation in `src/`, tests in `tests/`.
* Edit `README.md` if necessary.
* See `AGENTS.md` for detailed repository conventions.
* See `docs/ARCHITECTURE.md` for the architecture and design decisions.
* See `docs/ROADMAP.md` for the project roadmap.
* I am pretty good at identifying AI slop 😁.
