# AI Service - Unified LLM Architecture

## Overview
Centralized LLM service providing unified logging, security, and token tracking for all AI calls.

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Application Layer                         │
│  (gap_nodes.py, llm_utils.py, llm_helpers.py, etc.)        │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│              ai_service/core.py                              │
│          generate_completion() [SINGLE ENTRY POINT]          │
│                                                              │
│  ✓ Security validation (prompt size, injection detection)   │
│  ✓ Quota management (user token limits)                     │
│  ✓ Comprehensive logging (input/output with full context)   │
│  ✓ Token tracking (database logging via ai_service/logger)  │
│  ✓ Model routing (OpenAI, Gemini, Claude via LiteLLM)       │
│  ✓ Automatic fallback handling                              │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│                    LiteLLM                                   │
│  (Multi-provider: OpenAI, Gemini, Claude, etc.)             │
└─────────────────────────────────────────────────────────────┘
```

## Key Features

### 1. Unified Entry Point
- **Single source of truth**: All LLM calls go through `generate_completion()`
- **Consistent behavior**: Same security, logging, and tracking for all calls
- **Easy maintenance**: Changes in one place affect entire system

### 2. Security Features
- **Prompt size validation**: Prevents overflow (max 100K chars / ~25K tokens)
- **Injection detection**: Blocks suspicious patterns in user input
- **Quota management**: Enforces daily token limits per user

### 3. Comprehensive Logging
```
[AI SERVICE][call_id] 📤 SENDING TO LLM
  Model: gpt-4o-mini
  Fallbacks: ['gemini/gemini-1.5-flash']
  Call: gap_analysis
  Temperature: 0.1
  JSON Mode: true
======================================================================
[SYSTEM PROMPT]:
You are a career gap analysis expert...
----------------------------------------------------------------------
[USER PROMPT]:
Analyze the following CV and job requirements...
======================================================================

[AI SERVICE][call_id] 📥 RECEIVED FROM LLM
  Model Used: gpt-4o-mini-2024-07-18
  Duration: 2341ms
  Prompt Tokens: 1523
  Completion Tokens: 847
  Total Tokens: 2370
======================================================================
[RESPONSE]:
{"gaps": [...], "recommendations": [...]}
======================================================================
```

### 4. Token Tracking
- All calls logged to `llm_logs` table via `ai_service/logger.py`
- Tracks: user_id, model, provider, tokens, latency, cost, status
- Used for analytics, billing, and quota enforcement

## Usage

### Basic Usage
```python
from shared.ai_service import generate_completion

response = generate_completion(
    prompt="Your user prompt here",
    system_prompt="You are a helpful assistant.",
    json_mode=True,
    temperature=0.1,
    call_name="my_feature",
    user_id="user-uuid-here"  # Optional, for quota tracking
)
```

### With Model Override
```python
response = generate_completion(
    prompt="Your prompt",
    model="gpt-4o",  # Override default model
    call_name="premium_feature"
)
```

### With Model Key (DB Setting)
```python
response = generate_completion(
    prompt="Your prompt",
    model_key="gap_analysis_model",  # Uses DB setting
    call_name="gap_analysis"
)
```

## Wrapper Functions

### llm_utils.py
```python
from shared.llm_utils import get_chat_completion

# Legacy wrapper for backward compatibility
response = get_chat_completion(
    prompt="Your prompt",
    json_mode=True,
    model_key="career_advisor_model"
)
```

### llm_helpers.py (LangGraph)
```python
from worker.langgraph_agents.gap_v3.utils.llm_helpers import llm_json_completion

# Async wrapper for LangGraph nodes
result = await llm_json_completion(
    prompt="Your prompt",
    context="Additional context",
    call_name="gap_analysis_node"
)
```

## Configuration

### Environment Variables
- `LLM_MODEL`: Default model (fallback if not in DB)
- `OPENAI_API_KEY`: OpenAI API key
- `GEMINI_API_KEY`: Google Gemini API key
- `ANTHROPIC_API_KEY`: Anthropic Claude API key

### Database Settings (via config_manager)
- `ai_model`: General AI model
- `career_advisor_model`: Career advisor specific model
- `gap_analysis_model`: Gap analysis specific model
- `FALLBACK_AI_MODEL`: Fallback model if primary fails

## Security Limits

### Prompt Size
- **Max chars**: 100,000 (~25K tokens)
- **Warning threshold**: 80% of max (80K chars)
- **Reason**: Prevent token overflow and excessive costs

### Injection Patterns Blocked
- "ignore all previous instructions"
- "disregard all previous"
- "forget all previous"
- "new instructions:"
- "system: you are"
- "override system"
- "bypass security"

## Token Tracking Schema

```sql
CREATE TABLE llm_logs (
    id UUID PRIMARY KEY,
    user_id UUID,
    model_id VARCHAR(100),
    provider VARCHAR(50),
    call_type VARCHAR(100),
    prompt_tokens INTEGER,
    completion_tokens INTEGER,
    latency_ms INTEGER,
    status VARCHAR(20),
    error_message TEXT,
    request_metadata JSONB,
    created_at TIMESTAMP
);
```

## Migration Notes

### Before (Multiple Entry Points)
```python
# ❌ Old: Direct litellm calls
response = litellm.completion(...)

# ❌ Old: Multiple logging implementations
_log_llm_input(...)
_log_llm_output(...)
```

### After (Unified)
```python
# ✅ New: Single entry point
response = generate_completion(...)
# Logging happens automatically inside generate_completion()
```

## Benefits

1. **Easier debugging**: All LLM calls logged in same format
2. **Better security**: Centralized validation and injection detection
3. **Accurate tracking**: All tokens counted in one place
4. **Cost control**: Quota enforcement prevents runaway costs
5. **Maintainability**: Changes in one place, not scattered across codebase

## Related Files

- `backend/shared/ai_service/core.py` - Main entry point
- `backend/shared/ai_service/logger.py` - Database logging
- `backend/shared/ai_service/registry.py` - Model metadata
- `backend/shared/llm_utils.py` - Legacy wrapper
- `backend/worker/langgraph_agents/gap_v3/utils/llm_helpers.py` - LangGraph wrapper
