"""Preference-config-bounded task planning helpers.

The release pipeline constrains task categories to the active preference
configuration. A production system can replace the mock planner with a model,
but the parser and sanitizer should keep the same contract.
"""

from __future__ import annotations

import ast
import json
import re
from typing import Any, Dict, Iterable, List, Optional, Tuple


Task = Dict[str, Optional[str]]


def extract_json_list(text: str) -> Optional[str]:
    """Return the first bracketed JSON-like list from model text."""
    if not text:
        return None
    start = text.find("[")
    end = text.rfind("]")
    if start < 0 or end <= start:
        return None
    return text[start : end + 1]


def _parse_json_or_literal(text: str) -> Any:
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        normalized = re.sub(r"\bnull\b", "None", text, flags=re.IGNORECASE)
        normalized = re.sub(r"\btrue\b", "True", normalized, flags=re.IGNORECASE)
        normalized = re.sub(r"\bfalse\b", "False", normalized, flags=re.IGNORECASE)
        return ast.literal_eval(normalized)


def parse_task_plan(text: str, allowed_categories: Iterable[str]) -> Tuple[bool, List[Task], str]:
    """Parse and sanitize a task plan.

    The accepted schema is a list of dictionaries with exactly two keys:
    `task_category` and `task_prompt`. Categories outside `allowed_categories`
    are converted to null instead of being trusted.
    """
    extracted = extract_json_list(text)
    if extracted is None:
        return False, [], "no JSON list found"

    try:
        data = _parse_json_or_literal(extracted)
    except Exception as exc:  # pragma: no cover - exact parser message varies
        return False, [], f"parse error: {exc}"

    if not isinstance(data, list):
        return False, [], "parsed value is not a list"

    allowed = set(str(item) for item in allowed_categories)
    tasks: List[Task] = []
    for index, item in enumerate(data):
        if not isinstance(item, dict):
            return False, [], f"item {index} is not a dictionary"
        if set(item.keys()) != {"task_category", "task_prompt"}:
            return False, [], f"item {index} has invalid keys"
        category = item.get("task_category")
        if category is not None:
            category = str(category)
        if category not in allowed:
            category = None
        tasks.append(
            {
                "task_category": category,
                "task_prompt": str(item.get("task_prompt") or "").strip(),
            }
        )

    return True, tasks, "ok"


def attach_preferences(tasks: List[Task], preference_config: Dict[str, str]) -> List[Dict[str, Optional[str]]]:
    """Attach the selected service for each planned task."""
    enriched: List[Dict[str, Optional[str]]] = []
    for task in tasks:
        category = task.get("task_category")
        service = preference_config.get(category) if category else None
        enriched.append(
            {
                "task_category": category,
                "task_prompt": task.get("task_prompt") or "",
                "task_preference": service,
            }
        )
    return enriched


def plan_from_preference_config(prompt: str, preference_config: Dict[str, str]) -> List[Dict[str, Optional[str]]]:
    """A deterministic mock planner for release demos.

    It emits one task per configured scenario. This is intentionally simple: the
    goal is to show data flow without requiring a model or GPU.
    """
    tasks: List[Task] = []
    for scenario in preference_config:
        tasks.append(
            {
                "task_category": scenario,
                "task_prompt": f"Handle the {scenario} part of the request: {prompt}",
            }
        )
    return attach_preferences(tasks, preference_config)
