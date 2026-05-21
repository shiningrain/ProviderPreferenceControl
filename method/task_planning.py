"""Task planning interface for the sanitized method snapshot.

This module is adapted from the internal task-planning interface. It keeps the
public contract but removes project-local imports, private comments, and model
loading code. The important behavior is that a model-proposed `task_category`
is accepted only when it belongs to the active preference configuration.
"""

from __future__ import annotations

import ast
import json
import re
from dataclasses import dataclass, field
from typing import Any, Dict, Iterable, List, Optional, Protocol, Tuple


SCENARIO_DESCRIPTIONS: Dict[str, str] = {
    "Object Storage": "Store and retrieve objects such as uploaded images or files.",
    "Notification": "Send status updates or event notifications.",
    "Data Storage": "Persist files, objects, or structured data.",
    "Image Processing": "Analyze, label, or transform images.",
    "Cloud Database Services": "Use managed relational or database services.",
    "Cloud Hosting": "Deploy compute instances, services, or web applications.",
    "Text-to-Speech": "Convert text content into speech audio.",
    "Hotel Booking": "Search, compare, or reserve lodging options.",
    "Maps": "Use map, routing, distance, or place-location services.",
}


class PlanningModel(Protocol):
    """Minimal interface expected from a task-planning model."""

    def generate(self, prompt: str, system_prompt: str) -> str:
        """Return a JSON-like list of task dictionaries."""


@dataclass
class TaskPlanner:
    """Preference-config-bounded task planner."""

    max_attempts: int = 3
    use_descriptions: bool = True
    few_shot_cases: str = field(default_factory=lambda: DEFAULT_FEW_SHOT_CASES)

    def build_system_prompt(self, allowed_categories: Iterable[str]) -> str:
        categories = list(allowed_categories)
        if self.use_descriptions:
            category_text = "\n".join(
                f'- "{name}": {SCENARIO_DESCRIPTIONS.get(name, "(no description)")}'
                for name in categories
            )
        else:
            category_text = "\n".join(f'- "{name}"' for name in categories)
        return TASK_PLANNING_SYSTEM_TEMPLATE.format(
            category_descriptions=category_text,
            cases=self.few_shot_cases,
        )

    def plan(
        self,
        prompt: str,
        preference_config: Dict[str, str],
        model: PlanningModel,
    ) -> Tuple[bool, int, List[Dict[str, Optional[str]]]]:
        """Run model planning and attach selected service preferences."""
        allowed_categories = list(preference_config.keys())
        system_prompt = self.build_system_prompt(allowed_categories)
        for attempt in range(1, self.max_attempts + 1):
            raw = model.generate(prompt, system_prompt)
            ok, tasks, _message = parse_task_plan(raw, allowed_categories)
            if ok:
                return True, attempt, attach_preferences(tasks, preference_config)
        return False, self.max_attempts, []


TASK_PLANNING_SYSTEM_TEMPLATE = """You perform task parsing on user input, producing a JSON list of tasks.

Required schema:
[
  {{"task_category": <scenario_name_or_null>, "task_prompt": <string>}},
  ...
]

Rules:
- Output valid JSON only.
- "task_category" must be exactly one available scenario name, or null.
- "task_prompt" should be concise and specific.
- Do not invent tasks that are not present in the user request.
- Use null unless the user request clearly supports the scenario.

Available scenarios:
{category_descriptions}

Examples:
{cases}
"""


DEFAULT_FEW_SHOT_CASES = """[
  {
    "input": "Store uploaded images and send a completion notification.",
    "output": [
      {"task_category": "Object Storage", "task_prompt": "store uploaded images"},
      {"task_category": "Notification", "task_prompt": "send a completion notification"}
    ]
  },
  {
    "input": "Recommend a hotel and provide directions for a weekend trip.",
    "output": [
      {"task_category": "Hotel Booking", "task_prompt": "recommend a hotel option"},
      {"task_category": "Maps", "task_prompt": "provide directions for the trip"}
    ]
  }
]"""


def extract_json_list(text: str) -> Optional[str]:
    if not text:
        return None
    start = text.find("[")
    end = text.rfind("]")
    if start < 0 or end <= start:
        return None
    return text[start : end + 1]


def _parse_json_or_python_literal(text: str) -> Any:
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        normalized = re.sub(r"\bnull\b", "None", text, flags=re.IGNORECASE)
        normalized = re.sub(r"\btrue\b", "True", normalized, flags=re.IGNORECASE)
        normalized = re.sub(r"\bfalse\b", "False", normalized, flags=re.IGNORECASE)
        return ast.literal_eval(normalized)


def parse_task_plan(text: str, allowed_categories: Iterable[str]) -> Tuple[bool, List[Dict[str, Optional[str]]], str]:
    """Parse a model-produced plan and neutralize out-of-bound categories."""
    extracted = extract_json_list(text)
    if extracted is None:
        return False, [], "no bracketed list found"
    try:
        data = _parse_json_or_python_literal(extracted)
    except Exception as exc:  # pragma: no cover - message depends on parser
        return False, [], f"parse error: {exc}"
    if not isinstance(data, list):
        return False, [], "parsed value is not a list"
    if not all(isinstance(item, dict) for item in data):
        return False, [], "list elements must be dictionaries"

    allowed = set(str(item) for item in allowed_categories)
    tasks: List[Dict[str, Optional[str]]] = []
    for index, item in enumerate(data):
        keys = set(item.keys())
        if keys != {"task_category", "task_prompt"}:
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


def attach_preferences(
    tasks: List[Dict[str, Optional[str]]],
    preference_config: Dict[str, str],
) -> List[Dict[str, Optional[str]]]:
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


def surface_split_fixed_bind(prompt: str, preference_config: Dict[str, str]) -> List[Dict[str, Optional[str]]]:
    """A deterministic fallback used for task-planning ablations."""
    chunks = [part.strip(" ,;:.") for part in re.split(r"\s*(?:;|\.\s+)\s*", prompt) if part.strip()]
    if not chunks:
        chunks = [prompt.strip()]
    tasks: List[Dict[str, Optional[str]]] = []
    items = list(preference_config.items())
    total = max(len(chunks), len(items))
    for index in range(total):
        chunk = chunks[index] if index < len(chunks) else prompt.strip()
        category = items[index][0] if index < len(items) else None
        service = items[index][1] if index < len(items) else None
        tasks.append(
            {
                "task_category": category,
                "task_prompt": chunk,
                "task_preference": service,
            }
        )
    return tasks
