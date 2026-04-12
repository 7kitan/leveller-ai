# Automated Logging Rule

## Behavioral Hook
- **Mandate**: AFTER receiving each user prompt or completing a major task, the agent MUST execute the logging script.
- **Command**: `python scripts/log_hook.py antigravity`
- **Output**: This ensures all interactions are persisted in `.ai-log/session.jsonl` even if the system-level shell hooks are not firing.

## Maintenance
- Do not modify this rule without explicit user instruction.
