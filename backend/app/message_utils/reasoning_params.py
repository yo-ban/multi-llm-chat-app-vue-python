"""
Reasoning parameter helpers

Centralizes logic for translating UI reasoning settings into API-friendly
structures, keeping handlers small and testable.
"""
from typing import Dict, Optional


def _normalize_thinking_level(reasoning_level: Optional[str]) -> Optional[str]:
    """Normalize thinking levels to the expected string literal ("low"/"high")."""
    if not reasoning_level:
        return None
    normalized = reasoning_level.strip().lower()
    if normalized not in {"low", "high"}:
        return None
    return normalized


def build_gemini_thinking_config_kwargs(
    reasoning_parameter_type: Optional[str],
    budget_tokens: Optional[int],
    reasoning_level: Optional[str],
) -> Optional[Dict[str, int | str]]:
    """Return ThinkingConfig keyword args using snake_case fields."""
    if reasoning_parameter_type == "budget" and isinstance(budget_tokens, int):
        if budget_tokens >= 0:
            return {"thinking_budget": budget_tokens}
        return None

    if reasoning_parameter_type == "level":
        normalized_level = _normalize_thinking_level(reasoning_level)
        if normalized_level:
            return {"thinking_level": normalized_level}

    return None


__all__ = ["build_gemini_thinking_config_kwargs"]
