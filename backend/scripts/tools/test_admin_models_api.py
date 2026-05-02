"""
Test script to verify admin AI models API

Run with: python -m scripts.test_admin_models_api
"""

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from shared.ai_service.registry import AI_REGISTRY, get_available_models
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_models_registry():
    """Test AI models registry."""
    logger.info("=" * 80)
    logger.info("AI MODELS REGISTRY TEST")
    logger.info("=" * 80)
    
    logger.info(f"\n✓ Total models in registry: {len(AI_REGISTRY)}\n")
    
    # Group by provider
    providers = {}
    for model in AI_REGISTRY:
        if model.provider not in providers:
            providers[model.provider] = []
        providers[model.provider].append(model)
    
    for provider, models in sorted(providers.items()):
        logger.info(f"📦 {provider.upper()} ({len(models)} models)")
        for model in models:
            caps = ", ".join(model.capabilities) if model.capabilities else "none"
            logger.info(f"   • {model.id}")
            logger.info(f"     Name: {model.name}")
            logger.info(f"     Type: {model.type}")
            logger.info(f"     Capabilities: {caps}")
            logger.info(f"     Description: {model.description}")
            logger.info("")
    
    # Test filtering
    logger.info("=" * 80)
    logger.info("FILTERING TESTS")
    logger.info("=" * 80)
    
    chat_models = get_available_models("chat")
    embedding_models = get_available_models("embedding")
    
    logger.info(f"\n✓ Chat models: {len(chat_models)}")
    for m in chat_models:
        logger.info(f"   - {m.id} ({m.provider})")
    
    logger.info(f"\n✓ Embedding models: {len(embedding_models)}")
    for m in embedding_models:
        logger.info(f"   - {m.id} ({m.provider})")
    
    # Verify specific models
    logger.info("\n" + "=" * 80)
    logger.info("ANTHROPIC MODELS VERIFICATION")
    logger.info("=" * 80)
    
    anthropic_models = [m for m in AI_REGISTRY if m.provider == "anthropic"]
    logger.info(f"\n✓ Found {len(anthropic_models)} Anthropic models:\n")
    
    expected_anthropic = [
        "claude-3-5-sonnet",
        "claude-3-5-haiku",
        "claude-3-haiku",
        "claude-3-opus"
    ]
    
    for expected in expected_anthropic:
        found = any(m.id == expected for m in anthropic_models)
        status = "✓" if found else "✗"
        logger.info(f"   {status} {expected}")
    
    logger.info("\n" + "=" * 80)
    logger.info("TEST COMPLETED")
    logger.info("=" * 80)
    
    if len(anthropic_models) == 4:
        logger.info("\n✓ All Anthropic models are present!")
        logger.info("\nThese models should now be available in Admin UI:")
        logger.info("  - Settings → AI & Agent → Default Model dropdown")
        logger.info("  - Settings → AI & Agent → Fallback Model dropdown")
        return 0
    else:
        logger.error(f"\n✗ Expected 4 Anthropic models, found {len(anthropic_models)}")
        return 1

if __name__ == "__main__":
    sys.exit(test_models_registry())
