@echo off
if "%1"=="install" (
    pip install -e .[dev]
    goto :eof
)
if "%1"=="test" (
    pytest
    goto :eof
)
if "%1"=="lint" (
    ruff check src tests
    goto :eof
)
if "%1"=="typecheck" (
    mypy src
    goto :eof
)
if "%1"=="run-scenarios" (
    python -m langgraph_agent_lab.cli run-scenarios --config configs/lab.yaml --output outputs/metrics.json
    goto :eof
)
if "%1"=="grade-local" (
    python -m langgraph_agent_lab.cli validate-metrics --metrics outputs/metrics.json
    goto :eof
)
if "%1"=="clean" (
    if exist .pytest_cache rmdir /s /q .pytest_cache
    if exist .ruff_cache rmdir /s /q .ruff_cache
    if exist .mypy_cache rmdir /s /q .mypy_cache
    if exist htmlcov rmdir /s /q htmlcov
    if exist dist rmdir /s /q dist
    if exist build rmdir /s /q build
    for /d %%p in (*.egg-info) do rmdir /s /q "%%p"
    if exist outputs\*.json del /q outputs\*.json
    goto :eof
)
echo Target "%1" not found. Available targets: install, test, lint, typecheck, run-scenarios, grade-local, clean
