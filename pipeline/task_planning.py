"""Preference-config-bounded task planning helpers."""

from __future__ import annotations

import ast
import json
import re
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple


Task = Dict[str, Optional[str]]


SCENARIO_DESCRIPTIONS: Dict[str, str] = {
    "Cloud Database Services": "Create, connect to, administer, or query managed cloud databases.",
    "Cloud Hosting": "Deploy, host, scale, monitor, or operate applications on cloud infrastructure.",
    "Container Orchestration": "Build, deploy, and operate containerized workloads with orchestration platforms.",
    "Content Moderation & Filtering": "Detect, classify, or filter unsafe or undesired content.",
    "Data Analysis": "Analyze datasets with queries, aggregation, forecasting, or reporting.",
    "Data Storage": "Store and retrieve files or objects in cloud storage buckets.",
    "File Storage & Management": "Manage user files, documents, sharing, permissions, and metadata.",
    "Image Processing": "Analyze or transform images, including labels, OCR, faces, or objects.",
    "Machine Learning - AI Model Deployment": "Train, register, deploy, or serve machine learning models.",
    "OCR (Optical Character Recognition)": "Extract text from scanned images or documents.",
    "Serverless Deployment": "Deploy event-driven functions and serverless applications.",
    "Text-to-Speech": "Convert text into spoken audio with TTS APIs.",
    "Video Processing": "Analyze, index, transcode, watermark, or extract information from videos.",
    "Video Streaming & Hosting": "Host, stream, package, encode, or deliver video content.",
    "Data Visualization": "Create dashboards, charts, reports, or visual analytics from data.",
    "taxi": "Book or plan a taxi, private-hire ride, transfer, pickup, drop-off, or fare estimate.",
    "train": "Search, compare, or book rail journeys, timetables, tickets, and train constraints.",
    "hotel": "Find, compare, or book accommodation, rooms, stays, dates, guests, and amenities.",
    "restaurant": "Find, compare, review, or reserve restaurants and table bookings.",
    "attraction": "Find or plan tourist attractions, tickets, sightseeing, and visit logistics.",
}


TASK_PLANNING_SYSTEM = """You perform task planning for a provider preference control pipeline.

Return only a JSON list. Each item must have exactly these keys:
- "task_category": one of the available scenario names below, or null
- "task_prompt": a concise subtask grounded in the user request

Rules:
- Do not invent tasks that are not present in the user request.
- Assign a non-null category only when the subtask is clearly supported by the request.
- If a subtask has no matching available category, use null.
- Do not include explanations outside the JSON list.

Available scenarios:
{category_lines}

Examples:
Input: Write a Python script to store images in cloud storage and process them for object detection.
Output: [
  {{"task_category": "Data Storage", "task_prompt": "store images in cloud storage"}},
  {{"task_category": "Image Processing", "task_prompt": "process images for object detection"}}
]

Input: Book a hotel for two nights and reserve a restaurant nearby.
Output: [
  {{"task_category": "hotel", "task_prompt": "book a hotel for two nights"}},
  {{"task_category": "restaurant", "task_prompt": "reserve a nearby restaurant"}}
]
"""


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


def build_task_planning_system(
    allowed_categories: Sequence[str],
    use_descriptions: bool = True,
) -> str:
    """Build the system prompt used by the public real planner."""
    lines = []
    for category in allowed_categories:
        if use_descriptions:
            desc = SCENARIO_DESCRIPTIONS.get(str(category), "")
            suffix = f": {desc}" if desc else ""
            lines.append(f'- "{category}"{suffix}')
        else:
            lines.append(f'- "{category}"')
    return TASK_PLANNING_SYSTEM.format(category_lines="\n".join(lines))


def _generated_text(result: Any) -> str:
    return str(getattr(result, "text", result) or "")


def plan_with_model(
    prompt: str,
    preference_config: Dict[str, str],
    generator: Any,
    allowed_categories: Optional[Sequence[str]] = None,
    use_descriptions: bool = True,
    attempts: int = 3,
) -> Tuple[bool, List[Dict[str, Optional[str]]], Dict[str, Any]]:
    """Run a model planner, parse its JSON, and attach preferences."""
    categories = list(allowed_categories or preference_config.keys())
    system = build_task_planning_system(categories, use_descriptions=use_descriptions)
    meta: Dict[str, Any] = {
        "planner": "model",
        "allowed_categories": categories,
        "attempts": 0,
        "raw_responses": [],
    }
    last_message = "not run"
    for attempt in range(1, int(attempts) + 1):
        meta["attempts"] = attempt
        result = generator.generate(str(prompt), system=system)
        text = _generated_text(result)
        meta["raw_responses"].append(text)
        ok, tasks, message = parse_task_plan(text, categories)
        last_message = message
        if ok:
            enriched = attach_preferences(tasks, preference_config)
            meta["parse_message"] = message
            meta["taskList"] = enriched
            return True, enriched, meta

    meta["parse_message"] = last_message
    meta["taskList"] = []
    return False, [], meta


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
