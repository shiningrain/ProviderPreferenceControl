"""Anchor templates for constrained draft generation.

This file is a sanitized, compact version of the code-anchor and text-anchor
logic used in the project. It avoids internal service metadata files and keeps a
small public mapping that can be extended by artifact users.
"""

from __future__ import annotations

import re
from typing import Dict, List


SERVICE_METADATA: Dict[str, Dict[str, object]] = {
    "Amazon S3": {
        "provider": "AWS",
        "category": "Object Storage",
        "keywords": ["boto3.client('s3')", "upload_file", "s3 bucket"],
    },
    "Amazon SNS": {
        "provider": "AWS",
        "category": "Notification",
        "keywords": ["boto3.client('sns')", "publish", "sns"],
    },
    "Google Cloud Storage": {
        "provider": "Google",
        "category": "Object Storage",
        "keywords": ["google.cloud.storage", "storage.Client", "bucket"],
    },
    "Azure Blob Storage": {
        "provider": "Azure",
        "category": "Object Storage",
        "keywords": ["BlobServiceClient", "azure.storage.blob"],
    },
    "Booking.com": {
        "provider": "Booking",
        "category": "Hotel Booking",
        "keywords": ["Booking.com", "hotel booking"],
    },
    "Google Maps": {
        "provider": "Google",
        "category": "Maps",
        "keywords": ["Google Maps", "route", "travel time"],
    },
}


ANCHOR_SKELETON_PROMPT = """You are generating a Python code skeleton for one subtask.

Rules:
- Return only a single fenced python code block.
- Include the required anchor lines exactly inside the code block.
- Keep unresolved details as <blank>.

Subtask:
{task_prompt}

Scene: {category}
Required service: {service_name}

Required anchor lines:
{anchors_text}

Output:
"""


HYBRID_TEXT_DRAFT_PROMPT = """You are generating a compact scaffold draft for one text-planning subtask.

Rules:
- Preserve every anchor line exactly as written.
- Keep the required preference explicit and visible.
- Do not introduce alternative brands or unrelated services.
- Leave unresolved details as <blank>.

Subtask:
{task_prompt}

Reference scaffold:
{scaffold_text}

Continue the draft:
"""


def _safe_text(value: object) -> str:
    return re.sub(r"\s+", " ", str(value or "").strip()).replace("```", "")


def _dedupe_keep_order(items: List[str]) -> List[str]:
    seen = set()
    output = []
    for item in items:
        item = str(item or "").strip()
        if not item or item in seen:
            continue
        seen.add(item)
        output.append(item)
    return output


def _service_token(service_name: str) -> str:
    token = re.sub(r"[^a-z0-9]+", "_", str(service_name or "").lower()).strip("_")
    return token or "preferred_service"


def build_code_anchor_lines(service_name: str, category: str = "") -> List[str]:
    """Build detector-visible code anchors for a service preference."""
    info = SERVICE_METADATA.get(service_name, {})
    provider = str(info.get("provider") or "")
    category = str(category or info.get("category") or "")
    keywords = [str(item) for item in info.get("keywords", [])]
    lines = [
        f"# scene: {_safe_text(category)}",
        f"# required_service: {_safe_text(service_name)}",
    ]

    if provider == "AWS" and service_name == "Amazon S3":
        lines.extend(["import boto3", "s3_client = boto3.client('s3')", "s3_client.upload_file(<blank>)"])
    elif provider == "AWS" and service_name == "Amazon SNS":
        lines.extend(["import boto3", "sns_client = boto3.client('sns')", "sns_client.publish(<blank>)"])
    elif provider == "Google" and "Storage" in service_name:
        lines.extend(["from google.cloud import storage", "storage_client = storage.Client()"])
    elif provider == "Azure":
        lines.extend(["from azure.storage.blob import BlobServiceClient", "blob_client = BlobServiceClient(<blank>)"])

    for keyword in keywords:
        if len(lines) >= 6:
            break
        lines.append(f"# detector-anchor: {_safe_text(keyword)}")
    return _dedupe_keep_order(lines)[:6]


def build_code_anchor_prompt(task: Dict[str, str]) -> Dict[str, object]:
    category = str(task.get("task_category") or "")
    service = str(task.get("task_preference") or "")
    task_prompt = str(task.get("task_prompt") or "")
    anchor_lines = build_code_anchor_lines(service, category)
    return {
        "prompt": ANCHOR_SKELETON_PROMPT.format(
            task_prompt=task_prompt,
            category=category,
            service_name=service,
            anchors_text="\n".join(anchor_lines),
        ),
        "anchor_lines": anchor_lines,
    }


def build_text_anchor_bundle(task: Dict[str, str], full_prompt: str, index: int = 1) -> Dict[str, object]:
    """Build a text scaffold similar to the hybrid semantic API anchors."""
    category = _safe_text(task.get("task_category") or "General")
    service = _safe_text(task.get("task_preference") or "No explicit preference")
    task_prompt = _safe_text(task.get("task_prompt") or "")
    deliverable_type = "travel_plan" if category in {"Hotel Booking", "Maps"} else "structured_text"
    token = _service_token(service)
    api_hints = [f"{service} -> use_service", f"{token}.use_service"]
    preserve_terms = _dedupe_keep_order([service, category, *api_hints])
    anchor_lines = [
        f"# scene: {category}",
        f"# required_preference: {service}",
        f"# do_not_replace: {service}",
        f"# deliverable_type: {deliverable_type}",
        f"Preferred scene: {category}",
        f"Preferred service: {service}",
        f"Preferred action hints: {', '.join(api_hints)}",
        f"Must preserve terms: {', '.join(preserve_terms)}",
        f"# evidence: {task_prompt[:120]}",
    ]
    scaffold = [
        *anchor_lines,
        "Plan Scaffold:",
        f"- scene: {category}",
        f"- required_preference: {service}",
        "- step_1: <blank>",
        "- step_2: <blank>",
    ]
    return {
        "index": index,
        "category": category,
        "service_name": service,
        "task_prompt": task_prompt,
        "deliverable_type": deliverable_type,
        "anchor_lines": anchor_lines,
        "reference_scaffold": scaffold,
        "draft_prompt": HYBRID_TEXT_DRAFT_PROMPT.format(
            task_prompt=task_prompt,
            scaffold_text="\n".join(scaffold),
        ),
        "full_prompt_excerpt": _safe_text(full_prompt)[:200],
    }
