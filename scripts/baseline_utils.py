#!/usr/bin/env python3
"""Prompt builders and lightweight constrained-decoding utilities.

These helpers mirror the public baseline interfaces used in the paper without
including private model-loading code. They can be paired with any local or API
completion function that accepts a prompt and returns text.

The constrained baseline here is a lightweight lexical preference boost over
tokens from the active preference configuration. It is not a full reproduction
of NeuroLogic-style constrained beam search.
"""

from __future__ import annotations

import math
from typing import Any, Dict, Iterable, List, Mapping, MutableMapping, Optional


PreferenceConfig = Mapping[str, str]


def _clean_text(value: Any) -> str:
    return str(value).strip()


def format_requirement_lines(preference_config: PreferenceConfig) -> str:
    """Return one plain requirement line per scenario-service pair."""
    lines = []
    for scenario, service in preference_config.items():
        scenario_text = _clean_text(scenario)
        service_text = _clean_text(service)
        if scenario_text and service_text:
            lines.append(f"{scenario_text} use {service_text}")
    return "\n".join(lines)


def format_grouped_requirements(preference_config: PreferenceConfig) -> str:
    """Return the structured requirement block used by grouped prompting."""
    lines = []
    for index, (scenario, service) in enumerate(preference_config.items(), start=1):
        scenario_text = _clean_text(scenario)
        service_text = _clean_text(service)
        if scenario_text and service_text:
            lines.append(f"  [{index}] {scenario_text}: Use {service_text}")
    return "\n".join(lines)


def build_zero_shot_prompt(prompt: str, preference_config: PreferenceConfig) -> str:
    """Append unstructured service requirements to the original request."""
    requirements = format_requirement_lines(preference_config)
    return (
        f"{_clean_text(prompt)}\n\n"
        "Requirements:\n"
        f"{requirements}\n"
        "Please generate the complete response now."
    )


def build_grouped_prompt(prompt: str, preference_config: PreferenceConfig) -> str:
    """Append scenario-grouped provider requirements to the request."""
    requirements = format_grouped_requirements(preference_config)
    return (
        "You are a helpful assistant. Please complete the following task while "
        "strictly adhering to the service provider requirements for each scenario.\n\n"
        f"Task:\n{_clean_text(prompt)}\n\n"
        "Service Requirements (grouped by scenario):\n"
        f"{requirements}\n\n"
        "Important: For each scenario listed above, you MUST use the specified "
        "service provider. Do not substitute with alternative providers.\n\n"
        "Please generate the complete response now."
    )


def build_stepwise_plan_prompt(prompt: str, preference_config: PreferenceConfig) -> str:
    """Build the first-stage prompt for the step-wise baseline."""
    requirements = format_grouped_requirements(preference_config)
    return (
        "Decompose the user request into a concise step-by-step plan. Each step "
        "should mention the relevant scenario when a provider requirement applies.\n\n"
        f"Task:\n{_clean_text(prompt)}\n\n"
        "Service Requirements:\n"
        f"{requirements}\n\n"
        "Return only the plan."
    )


def build_stepwise_response_prompt(
    prompt: str,
    preference_config: PreferenceConfig,
    plan: str,
) -> str:
    """Build the second-stage prompt for the step-wise baseline."""
    requirements = format_grouped_requirements(preference_config)
    return (
        "Use the plan below to answer the user request. Preserve all listed "
        "provider requirements.\n\n"
        f"Task:\n{_clean_text(prompt)}\n\n"
        "Service Requirements:\n"
        f"{requirements}\n\n"
        f"Plan:\n{_clean_text(plan)}\n\n"
        "Generate the final response."
    )


def build_constrained_prompt(prompt: str, preference_config: PreferenceConfig) -> str:
    """Build the prompt paired with lexical preference-token boosting."""
    return build_grouped_prompt(prompt, preference_config)


def collect_preference_terms(preference_config: PreferenceConfig) -> List[str]:
    """Collect service-name surface forms used by lexical boosting."""
    terms = []
    seen = set()
    for service in preference_config.values():
        text = _clean_text(service)
        candidates = [text, text.lower()]
        for candidate in candidates:
            if candidate and candidate not in seen:
                seen.add(candidate)
                terms.append(candidate)
    return terms


def build_token_bias(
    preference_config: PreferenceConfig,
    tokenizer: Any,
    boost_factor: float = 1.5,
) -> Dict[int, float]:
    """Map preference-service token ids to additive logit boosts.

    The tokenizer only needs an `encode(text, add_special_tokens=False)` method.
    The returned dictionary can be used by local decoding code or converted into
    an API-specific logit-bias format.
    """
    if boost_factor <= 0:
        raise ValueError("boost_factor must be positive")

    bias = math.log(boost_factor)
    token_bias: Dict[int, float] = {}
    for term in collect_preference_terms(preference_config):
        token_ids = tokenizer.encode(term, add_special_tokens=False)
        for token_id in token_ids:
            token_bias[int(token_id)] = token_bias.get(int(token_id), 0.0) + bias
    return token_bias


class PreferenceBoostProcessor:
    """Callable logits processor for local decoding loops.

    The object accepts tensor-like `scores` and adds the configured bias to the
    target token columns. It is intentionally dependency-light: if the scores
    object supports `scores[..., token_id] += value`, it works with common tensor
    libraries; otherwise it falls back to one-dimensional mutable sequences.
    """

    def __init__(self, token_bias: Mapping[int, float]):
        self.token_bias = dict(token_bias)

    def __call__(self, input_ids: Any, scores: Any) -> Any:
        del input_ids
        for token_id, bias in self.token_bias.items():
            try:
                scores[..., token_id] += bias
            except Exception:
                scores[token_id] += bias
        return scores


def build_baseline_prompt(
    method: str,
    prompt: str,
    preference_config: PreferenceConfig,
    plan: Optional[str] = None,
) -> str:
    """Dispatch to the prompt builder for a named baseline."""
    normalized = method.replace("-", "_").lower()
    if normalized == "zero_shot":
        return build_zero_shot_prompt(prompt, preference_config)
    if normalized == "grouped":
        return build_grouped_prompt(prompt, preference_config)
    if normalized == "step_wise":
        if plan is None:
            return build_stepwise_plan_prompt(prompt, preference_config)
        return build_stepwise_response_prompt(prompt, preference_config, plan)
    if normalized == "constrained":
        return build_constrained_prompt(prompt, preference_config)
    raise ValueError(f"unknown baseline method: {method}")


def run_prompt_only_baseline(
    method: str,
    prompt: str,
    preference_config: PreferenceConfig,
    complete_fn: Any,
) -> Dict[str, Any]:
    """Run a prompt-only baseline with a user-provided completion function.

    `complete_fn` should accept a string prompt and return the generated text.
    This keeps the release code model-agnostic and avoids private inference
    dependencies.
    """
    normalized = method.replace("-", "_").lower()
    if normalized == "step_wise":
        plan_prompt = build_stepwise_plan_prompt(prompt, preference_config)
        plan = complete_fn(plan_prompt)
        final_prompt = build_stepwise_response_prompt(prompt, preference_config, plan)
        response = complete_fn(final_prompt)
        return {
            "method": method,
            "plan_prompt": plan_prompt,
            "plan": plan,
            "prompt": final_prompt,
            "response": response,
        }

    baseline_prompt = build_baseline_prompt(normalized, prompt, preference_config)
    response = complete_fn(baseline_prompt)
    return {
        "method": method,
        "prompt": baseline_prompt,
        "response": response,
    }


def make_openai_logit_bias(token_bias: Mapping[int, float], scale: float = 20.0) -> Dict[str, int]:
    """Convert additive token bias values into an OpenAI-style logit_bias map.

    API providers use different accepted ranges and semantics. This helper is a
    convenience for experiments and should be checked against the target API
    before use.
    """
    result: Dict[str, int] = {}
    for token_id, value in token_bias.items():
        scaled = int(round(value * scale))
        result[str(int(token_id))] = max(-100, min(100, scaled))
    return result
