"""
gap_v3 config: Feature flags và thresholds.
"""

import os
from shared.config_utils import config_manager

# Feature flags
def get_pii_masking_enabled():
    return config_manager.get_setting("gap_pii_masking", default=True, cast=bool)

def get_redis_cache_enabled():
    return config_manager.get_setting("gap_redis_cache", default=True, cast=bool)

def get_use_llm_gap_agent_v3():
    return config_manager.get_setting("use_llm_gap_agent_v3", default=True, cast=bool)

# LLM
def get_gap_llm_model():
    return config_manager.get_setting("gap_llm_model") or config_manager.get_setting("ai_model") or os.getenv("LLM_MODEL", "gpt-4o-mini")

# Legacy constants (for compatibility, but prefer functions above)
GAP_LLM_MODEL = get_gap_llm_model()
ENABLE_PII_MASKING = get_pii_masking_enabled()

# Redis cache TTL (seconds)
GAP_CACHE_TTL = int(os.getenv("GAP_CACHE_TTL", "1800"))  # 30 min
JD_EXTRACT_CACHE_TTL = int(os.getenv("JD_EXTRACT_CACHE_TTL", "3600"))  # 1 hour
CV_PARSED_CACHE_TTL = int(os.getenv("CV_PARSED_CACHE_TTL", "86400"))  # 24h

# Vector search thresholds
def get_vector_sim_threshold():
    return config_manager.get_setting("gap_vector_sim_threshold", default=0.35, cast=float)

# Legacy constant
VECTOR_SIM_THRESHOLD = get_vector_sim_threshold()
