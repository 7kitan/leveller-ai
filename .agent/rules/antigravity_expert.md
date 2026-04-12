# Antigravity Expert Directives (v1.0)

## Core Philosophy: Artifact-First
You are running inside Google Antigravity. DO NOT just write code. 
For every complex task, you MUST generate an **Artifact** first.

### Artifact Protocol:
1. **Planning**: Create `artifacts/plan_[task_id].md` before touching code.
2. **Evidence**: When testing, save output logs to `artifacts/logs/`.

## Context Management
- Read the entire `src/` tree before answering architectural questions.
- Consult `mission.md` before starting any task.

## Continuous Delivery Loop
**STRICT MANDATE:** Automate the following loop using `gh` CLI or `git` immediately upon task completion:
1. Update `CHANGELOG.md`.
2. Commit semantically: `feat: [Description]`.
3. Push and Create PR.
