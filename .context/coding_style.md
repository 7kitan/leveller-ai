# Antigravity Context: Coding Style

## Philosophy
- **Autonomous Agents**: Design for Gemini 3 agentic workflows.
- **Type Safety**: Python code MUST use strict Type Hints.
- **Documentation**: Google-style docstrings for all entries.

## Python Standards
1. Use `pydantic` for data schemas.
2. Async-first logic for I/O operations.
3. Wrap external APIs in `tools/` directory.

## Testing
- Mandatory `pytest` execution before PR creation.
