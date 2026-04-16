"""
gap_v3 config: Feature flags và thresholds.
"""

import os

# Feature flags
ENABLE_PII_MASKING = os.getenv("GAP_PII_MASKING", "true").lower() == "true"
ENABLE_REDIS_CACHE = os.getenv("GAP_REDIS_CACHE", "true").lower() == "true"
USE_LLM_GAP_AGENT_V3 = os.getenv("USE_LLM_GAP_AGENT_V3", "true").lower() == "true"

# LLM
GAP_LLM_MODEL = os.getenv("GAP_LLM_MODEL", os.getenv("LLM_MODEL", "gpt-4o-mini"))

# Redis cache TTL (seconds)
GAP_CACHE_TTL = int(os.getenv("GAP_CACHE_TTL", "1800"))  # 30 min
JD_EXTRACT_CACHE_TTL = int(os.getenv("JD_EXTRACT_CACHE_TTL", "3600"))  # 1 hour
CV_PARSED_CACHE_TTL = int(os.getenv("CV_PARSED_CACHE_TTL", "86400"))  # 24h

# Vector search thresholds
VECTOR_SIM_THRESHOLD = float(os.getenv("GAP_VECTOR_SIM_THRESHOLD", "0.60"))
