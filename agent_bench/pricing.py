"""Model pricing data for cost calculation."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class ModelPricing:
    """Pricing for a single model (per million tokens, USD)."""
    name: str
    input: float = 0.0
    output: float = 0.0

    def cost(self, tokens_in: int, tokens_out: int) -> float:
        return (tokens_in / 1_000_000 * self.input) + (tokens_out / 1_000_000 * self.output)


# Default pricing per million tokens (USD)
DEFAULT_PRICING: dict[str, dict[str, float]] = {
    # ── Anthropic ──
    "claude-sonnet-4": {"input": 3.00, "output": 15.00},
    "claude-opus-4": {"input": 15.00, "output": 75.00},
    "claude-haiku-3.5": {"input": 0.80, "output": 4.00},
    "claude-code": {"input": 3.00, "output": 15.00},
    "claude-3.5-sonnet": {"input": 3.00, "output": 15.00},
    "claude-3.5-haiku": {"input": 0.80, "output": 4.00},
    "claude-3-opus": {"input": 15.00, "output": 75.00},
    "claude-3-sonnet": {"input": 3.00, "output": 15.00},
    "claude-3-haiku": {"input": 0.25, "output": 1.25},
    # ── OpenAI ──
    "gpt-5.2-codex": {"input": 2.50, "output": 10.00},
    "gpt-5.4": {"input": 2.50, "output": 10.00},
    "gpt-5.4-thinking": {"input": 5.00, "output": 20.00},
    "o3-mini": {"input": 1.10, "output": 4.40},
    "o3": {"input": 2.50, "output": 10.00},
    "o4-mini": {"input": 1.10, "output": 4.40},
    "gpt-4o": {"input": 2.50, "output": 10.00},
    "gpt-4o-mini": {"input": 0.15, "output": 0.60},
    "gpt-4-turbo": {"input": 10.00, "output": 30.00},
    # ── Google ──
    "gemini-3.1-flash": {"input": 0.15, "output": 0.60},
    "gemini-3.1-pro": {"input": 1.25, "output": 10.00},
    "gemini-3.1-ultra": {"input": 2.50, "output": 15.00},
    "gemini-3.5-pro": {"input": 1.25, "output": 10.00},
    "gemini-2.5-flash": {"input": 0.15, "output": 0.60},
    "gemini-2.5-pro": {"input": 1.25, "output": 10.00},
    "gemini-2.0-flash": {"input": 0.10, "output": 0.40},
    "gemini-1.5-pro": {"input": 1.25, "output": 5.00},
    "gemini-1.5-flash": {"input": 0.075, "output": 0.30},
    # ── xAI ──
    "grok-4.20": {"input": 3.00, "output": 15.00},
    "grok-3": {"input": 0.50, "output": 2.00},
    "grok-3-mini": {"input": 0.30, "output": 1.00},
    "grok-2": {"input": 2.00, "output": 10.00},
    # ── DeepSeek ──
    "deepseek-v4": {"input": 0.27, "output": 1.10},
    "deepseek-v4-reasoning": {"input": 0.55, "output": 2.19},
    "deepseek-v3": {"input": 0.27, "output": 1.10},
    "deepseek-r1": {"input": 0.55, "output": 2.19},
    "deepseek-chat": {"input": 0.14, "output": 0.28},
    # ── Meta ──
    "llama-4-maverick": {"input": 0.20, "output": 0.80},
    "llama-4-scout": {"input": 0.10, "output": 0.40},
    "llama-3.3-70b": {"input": 0.20, "output": 0.80},
    # ── Mistral ──
    "mistral-large": {"input": 2.00, "output": 6.00},
    "mistral-medium": {"input": 0.40, "output": 1.50},
    "mistral-small": {"input": 0.20, "output": 0.60},
    "codestral": {"input": 0.30, "output": 0.90},
    # ── Cohere ──
    "command-r-plus": {"input": 2.50, "output": 10.00},
    "command-r": {"input": 0.50, "output": 1.50},
    # ── Open source / Chinese ──
    "glm-5": {"input": 0.10, "output": 0.40},
    "glm-4": {"input": 0.10, "output": 0.40},
    "qwen-3": {"input": 0.15, "output": 0.60},
    "qwen-2.5-coder": {"input": 0.15, "output": 0.60},
    "yi-large": {"input": 0.30, "output": 0.90},
}

# Default model per agent for cost estimation
AGENT_DEFAULT_MODEL: dict[str, str] = {
    "claude-code": "claude-code",
    "codex-cli": "gpt-5.2-codex",
    "gemini-cli": "gemini-2.5-flash",
    "openclaw": "glm-5",
    "aider": "gpt-4o",
    "hermes": "deepseek-v4",
    "opencode": "gemini-2.5-flash",
}


def get_pricing(model: str) -> ModelPricing:
    """Get pricing for a model with fuzzy matching."""
    if model in DEFAULT_PRICING:
        return ModelPricing(name=model, **DEFAULT_PRICING[model])
    norm = model.lower().strip()
    for key, prices in DEFAULT_PRICING.items():
        if key in norm or norm in key:
            return ModelPricing(name=key, **prices)
    return ModelPricing(name=model)


def estimate_cost(agent: str, tokens_in: int, tokens_out: int) -> float:
    """Estimate cost for an agent run."""
    model = AGENT_DEFAULT_MODEL.get(agent, agent)
    return get_pricing(model).cost(tokens_in, tokens_out)
