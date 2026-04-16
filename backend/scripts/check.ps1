Set-Location $PSScriptRoot\..
ruff check app tests
ruff format --check app tests
mypy app tests
pytest
