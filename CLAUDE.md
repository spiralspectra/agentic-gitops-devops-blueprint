# Developer & Agent Guidelines (CLAUDE.md)

This file defines the operational context and development standards for Claude in this repository.

See [AGENTS.md](AGENTS.md) for the binding rules, security boundaries, and mandatory verification gates.

## Development Workflow

1. **Python Tooling**: Always use `uv` for environment management, dependency resolution, and script execution (`uv run pytest`, `uv run ruff`, etc.).
2. **Coding Standards**:
   - Strict typing across Python code.
   - Clean docstrings and module documentation.
   - Guardrails against prompt injection and unauthorized command execution.
3. **Observability**:
   - Telemetry must be formatted for structured Cloud Logging ingestion.
   - Latency must be tracked per request to satisfy SLO criteria.
4. **Testing**:
   - Unit tests under `tests/unit/` must run hermetically without external network dependencies.
   - Use `AGENT_EVAL_MOCK=1` for offline evaluation test runs.
