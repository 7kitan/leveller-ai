from typing import List, Dict, Optional, Any
from dataclasses import dataclass, field

@dataclass
class AIModelDefinition:
    id: str
    provider: str  # 'openai', 'google', 'anthropic', 'deepseek'
    name: str      # Display name
    type: str      # 'chat', 'embedding'
    capabilities: List[str] = field(default_factory=list) # 'vision', 'json', 'long_context'
    description: str = ""

# Single Source of Truth for all supported AI Models
AI_REGISTRY: List[AIModelDefinition] = [
    # Google Gemini
    AIModelDefinition(
        id="gemini-1.5-pro",
        provider="google",
        name="Gemini 1.5 Pro",
        type="chat",
        capabilities=["json", "vision", "long_context"],
        description="Most capable Google model for complex reasoning."
    ),
    AIModelDefinition(
        id="gemini-1.5-flash",
        provider="google",
        name="Gemini 1.5 Flash",
        type="chat",
        capabilities=["json", "vision"],
        description="Fast and efficient Google model."
    ),
    # OpenAI
    AIModelDefinition(
        id="gpt-4o",
        provider="openai",
        name="GPT-4o",
        type="chat",
        capabilities=["json", "vision"],
        description="Omni model, high intelligence and speed."
    ),
    AIModelDefinition(
        id="gpt-4o-mini",
        provider="openai",
        name="GPT-4o Mini",
        type="chat",
        capabilities=["json"],
        description="Affordable and fast flagship model."
    ),
    AIModelDefinition(
        id="gpt-4-turbo",
        provider="openai",
        name="GPT-4 Turbo",
        type="chat",
        capabilities=["json"],
        description="Previous generation high-capability model."
    ),
    AIModelDefinition(
        id="text-embedding-3-small",
        provider="openai",
        name="Embedding Small",
        type="embedding",
        description="Efficient text embeddings."
    ),
    # Anthropic (Future ready)
    AIModelDefinition(
        id="claude-3-5-sonnet",
        provider="anthropic",
        name="Claude 3.5 Sonnet",
        type="chat",
        capabilities=["json", "vision"],
        description="Balanced performance and speed from Anthropic."
    ),
]

def get_model_info(model_id: str) -> Optional[AIModelDefinition]:
    """Lookup model metadata from registry."""
    for m in AI_REGISTRY:
        if m.id == model_id:
            return m
    return None

def get_available_models(model_type: Optional[str] = None) -> List[AIModelDefinition]:
    """Filter models by type (chat, embedding)."""
    if not model_type:
        return AI_REGISTRY
    return [m for m in AI_REGISTRY if m.type == model_type]
