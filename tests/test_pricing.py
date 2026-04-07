"""Tests for pricing module."""

from agent_bench.pricing import get_pricing, estimate_cost, DEFAULT_PRICING, ModelPricing


def test_get_pricing_exact():
    p = get_pricing("claude-sonnet-4")
    assert p.input == 3.00
    assert p.output == 15.00


def test_get_pricing_fuzzy():
    p = get_pricing("claude-sonnet-4-20250514")
    assert p.input == 3.00


def test_get_pricing_unknown():
    p = get_pricing("totally-unknown-model")
    assert p.input == 0.0
    assert p.output == 0.0


def test_model_pricing_cost():
    m = ModelPricing(name="test", input=3.0, output=15.0)
    cost = m.cost(1_000_000, 1_000_000)
    assert cost == 18.0


def test_model_pricing_zero():
    m = ModelPricing(name="test", input=0.0, output=0.0)
    assert m.cost(1000, 1000) == 0.0


def test_estimate_cost_known_agent():
    cost = estimate_cost("claude-code", 100000, 50000)
    assert cost > 0


def test_estimate_cost_unknown_agent():
    cost = estimate_cost("unknown-agent", 100000, 50000)
    assert cost == 0.0


def test_default_pricing_has_entries():
    assert len(DEFAULT_PRICING) > 20


def test_all_providers_represented():
    providers = ["claude", "gpt", "gemini", "grok", "deepseek", "llama", "mistral", "glm"]
    keys = " ".join(DEFAULT_PRICING.keys()).lower()
    for p in providers:
        assert p in keys


def test_cost_calculation_precision():
    p = get_pricing("o3-mini")
    cost = p.cost(500000, 200000)
    expected = 500000/1e6 * 1.10 + 200000/1e6 * 4.40
    assert abs(cost - expected) < 0.001
