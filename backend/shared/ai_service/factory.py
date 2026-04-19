import os
import logging
import openai
from typing import Dict, Any, Optional

logger = logging.getLogger("ai_service")

class AIProviderFactory:
    """
    Lazy-loading factory for AI client singletons.
    Ensures environment variables are only checked when a provider is actually used.
    """
    _clients: Dict[str, Any] = {}

    @classmethod
    def get_openai_client(cls) -> Optional[openai.OpenAI]:
        if "openai" not in cls._clients:
            api_key = os.getenv("OPENAI_API_KEY")
            if api_key:
                cls._clients["openai"] = openai.OpenAI(api_key=api_key)
            else:
                logger.error("OPENAI_API_KEY is not set.")
                return None
        return cls._clients["openai"]

    @classmethod
    def get_google_sdk(cls):
        """Returns the configured google.generativeai module."""
        if "google" not in cls._clients:
            try:
                import google.generativeai as genai
                api_key = os.getenv("GEMINI_API_KEY")
                if api_key:
                    genai.configure(api_key=api_key)
                    cls._clients["google"] = genai
                else:
                    logger.error("GEMINI_API_KEY is not set.")
                    return None
            except ImportError:
                logger.error("google-generativeai package not installed.")
                return None
        return cls._clients["google"]

    @classmethod
    def get_anthropic_client(cls):
        # Placeholder for future implementation
        return None
