#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
ruff check app tests
ruff format --check app tests
mypy app tests
pytest
