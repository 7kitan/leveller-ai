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
    # ─── Google Gemini ────────────────────────────────────────────────────────
    # 2026 Generation
    AIModelDefinition(
        id="gemini-3.1-pro",
        provider="google",
        name="Gemini 3.1 Pro",
        type="chat",
        capabilities=["json", "vision", "long_context"],
        description="Latest flagship Google model (Feb 2026). Native multimodality and 1M+ context."
    ),
    AIModelDefinition(
        id="gemini-3.1-flash",
        provider="google",
        name="Gemini 3.1 Flash",
        type="chat",
        capabilities=["json", "vision"],
        description="Ultra-fast high-throughput model (March 2026)."
    ),
    AIModelDefinition(
        id="gemini-3.0-pro",
        provider="google",
        name="Gemini 3.0 Pro",
        type="chat",
        capabilities=["json", "vision", "long_context"],
        description="Foundational 3rd generation Google model (Nov 2025)."
    ),
    # 2024-2025 Generation
    AIModelDefinition(
        id="gemini-2.0-flash-exp",
        provider="google",
        name="Gemini 2.0 Flash (Exp)",
        type="chat",
        capabilities=["json", "vision", "long_context"],
        description="Experimental next-gen model (Late 2024)."
    ),
    AIModelDefinition(
        id="gemini-1.5-pro",
        provider="google",
        name="Gemini 1.5 Pro",
        type="chat",
        capabilities=["json", "vision", "long_context"],
        description="Highly capable legacy model for complex reasoning."
    ),
    AIModelDefinition(
        id="gemini-1.5-flash",
        provider="google",
        name="Gemini 1.5 Flash",
        type="chat",
        capabilities=["json", "vision"],
        description="Fast and efficient legacy model for high-volume tasks."
    ),
    AIModelDefinition(
        id="gemini-1.0-pro",
        provider="google",
        name="Gemini 1.0 Pro",
        type="chat",
        capabilities=["json"],
        description="Classic stable Gemini model."
    ),

    # ─── OpenAI ───────────────────────────────────────────────────────────────
    # 2026 Generation
    AIModelDefinition(
        id="gpt-5.5",
        provider="openai",
        name="GPT-5.5",
        type="chat",
        capabilities=["json", "vision", "long_context"],
        description="Current OpenAI flagship (April 2026). Advanced agentic reasoning."
    ),
    AIModelDefinition(
        id="gpt-5.4",
        provider="openai",
        name="GPT-5.4",
        type="chat",
        capabilities=["json", "vision"],
        description="High-performance version of GPT-5 (March 2026)."
    ),
    AIModelDefinition(
        id="gpt-5.0",
        provider="openai",
        name="GPT-5 (Base)",
        type="chat",
        capabilities=["json", "vision"],
        description=" Breakthrough base release (August 2025)."
    ),
    # Reasoning Series
    AIModelDefinition(
        id="o1-preview",
        provider="openai",
        name="OpenAI o1 Preview",
        type="chat",
        capabilities=["json"],
        description="First generation reasoning model."
    ),
    AIModelDefinition(
        id="o1-mini",
        provider="openai",
        name="OpenAI o1 Mini",
        type="chat",
        capabilities=["json"],
        description="Fast reasoning model optimized for coding."
    ),
    # Classic Series
    AIModelDefinition(
        id="gpt-4o",
        provider="openai",
        name="GPT-4o",
        type="chat",
        capabilities=["json", "vision"],
        description="Classic omni model, high intelligence and speed."
    ),
    AIModelDefinition(
        id="gpt-4o-mini",
        provider="openai",
        name="GPT-4o Mini",
        type="chat",
        capabilities=["json"],
        description="Affordable and fast flagship-class model."
    ),
    AIModelDefinition(
        id="gpt-4-turbo",
        provider="openai",
        name="GPT-4 Turbo",
        type="chat",
        capabilities=["json"],
        description="Legacy model with 128k context window."
    ),
    AIModelDefinition(
        id="gpt-4",
        provider="openai",
        name="GPT-4 (Classic)",
        type="chat",
        capabilities=["json"],
        description="Gold standard for reliability (Legacy)."
    ),
    AIModelDefinition(
        id="gpt-3.5-turbo",
        provider="openai",
        name="GPT-3.5 Turbo",
        type="chat",
        capabilities=["json"],
        description="Legacy standard for fast, cost-effective completions."
    ),
    # Embeddings
    AIModelDefinition(
        id="text-embedding-3-small",
        provider="openai",
        name="Embedding 3 Small",
        type="embedding",
        description="Efficient modern text embeddings."
    ),
    AIModelDefinition(
        id="text-embedding-3-large",
        provider="openai",
        name="Embedding 3 Large",
        type="embedding",
        description="Highest quality text embeddings."
    ),
    AIModelDefinition(
        id="text-embedding-ada-002",
        provider="openai",
        name="Embedding Ada 002",
        type="embedding",
        description="Previous generation industry standard."
    ),

    # ─── Anthropic ────────────────────────────────────────────────────────────
    AIModelDefinition(
        id="claude-3-5-sonnet-20241022",
        provider="anthropic",
        name="Claude 3.5 Sonnet (New)",
        type="chat",
        capabilities=["json", "vision"],
        description="Latest high-performance model from Anthropic."
    ),
    AIModelDefinition(
        id="claude-3-5-sonnet",
        provider="anthropic",
        name="Claude 3.5 Sonnet",
        type="chat",
        capabilities=["json", "vision"],
        description="Highly balanced intelligence and speed."
    ),
    AIModelDefinition(
        id="claude-3-5-haiku-20241022",
        provider="anthropic",
        name="Claude 3.5 Haiku",
        type="chat",
        capabilities=["json"],
        description="Ultra-fast model for simple tasks."
    ),
    AIModelDefinition(
        id="claude-3-opus-20240229",
        provider="anthropic",
        name="Claude 3 Opus",
        type="chat",
        capabilities=["json", "vision"],
        description="Powerful model for complex reasoning."
    ),
    AIModelDefinition(
        id="claude-3-haiku-20240307",
        provider="anthropic",
        name="Claude 3 Haiku (Classic)",
        type="chat",
        capabilities=["json"],
        description="Legacy fast model."
    ),
    AIModelDefinition(
        id="claude-2.1",
        provider="anthropic",
        name="Claude 2.1",
        type="chat",
        capabilities=[],
        description="Legacy model with 200k context window."
    ),

    # ─── Groq (Llama, Mixtral, Gemma) ─────────────────────────────────────────
    AIModelDefinition(
        id="llama-3.3-70b-versatile",
        provider="groq",
        name="Llama 3.3 70B (Groq)",
        type="chat",
        capabilities=["json"],
        description="Fastest Llama 3.3 on Groq."
    ),
    AIModelDefinition(
        id="llama-3.1-8b-instant",
        provider="groq",
        name="Llama 3.1 8B (Groq)",
        type="chat",
        capabilities=["json"],
        description="Instant responses for simple tasks."
    ),
    AIModelDefinition(
        id="mixtral-8x7b-32768",
        provider="groq",
        name="Mixtral 8x7B (Groq)",
        type="chat",
        capabilities=["json"],
        description="High-quality MoE model."
    ),
    AIModelDefinition(
        id="gemma2-9b-it",
        provider="groq",
        name="Gemma 2 9B (Groq)",
        type="chat",
        capabilities=["json"],
        description="Google's open model on Groq."
    ),

    # ─── Mistral AI ───────────────────────────────────────────────────────────
    AIModelDefinition(
        id="mistral-large-latest",
        provider="mistral",
        name="Mistral Large",
        type="chat",
        capabilities=["json"],
        description="Top reasoning model from Mistral."
    ),
    AIModelDefinition(
        id="mistral-small-latest",
        provider="mistral",
        name="Mistral Small",
        type="chat",
        capabilities=["json"],
        description="Fast and efficient model."
    ),
    AIModelDefinition(
        id="open-mixtral-8x22b",
        provider="mistral",
        name="Mixtral 8x22B",
        type="chat",
        capabilities=["json"],
        description="Large-scale MoE model."
    ),

    # ─── DeepSeek ─────────────────────────────────────────────────────────────
    AIModelDefinition(
        id="deepseek-v3",
        provider="deepseek",
        name="DeepSeek V3",
        type="chat",
        capabilities=["json"],
        description="Latest high-performance DeepSeek model."
    ),
    AIModelDefinition(
        id="deepseek-chat",
        provider="deepseek",
        name="DeepSeek V2.5",
        type="chat",
        capabilities=["json"],
        description="Excellent price/performance ratio."
    ),
    AIModelDefinition(
        id="deepseek-coder",
        provider="deepseek",
        name="DeepSeek Coder V2",
        type="chat",
        capabilities=["json"],
        description="Coding specialist model."
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
