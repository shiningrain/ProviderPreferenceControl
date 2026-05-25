"""Anchor construction for mock and real public pipeline runs."""

from __future__ import annotations

import re
from typing import Any, Dict, List, Optional


CODE_ANCHOR_HINTS: Dict[str, List[str]] = {
    "Amazon S3": [
        "import boto3",
        "s3_client = boto3.client('s3')",
        "s3_client.upload_file(<blank>)",
    ],
    "Amazon SNS": [
        "import boto3",
        "sns_client = boto3.client('sns')",
        "sns_client.publish(<blank>)",
    ],
    "Google Cloud Storage": [
        "from google.cloud import storage",
        "storage_client = storage.Client()",
        "bucket = storage_client.bucket(<blank>)",
    ],
    "Azure Blob Storage": [
        "from azure.storage.blob import BlobServiceClient",
        "blob_service_client = BlobServiceClient.from_connection_string(<blank>)",
    ],
}


TEXT_ACTION_HINTS: Dict[str, List[str]] = {
    "Booking.com": ["search lodging options", "compare guest constraints", "prepare booking recommendation"],
    "Google Maps": ["lookup route context", "estimate travel time", "present map-based directions"],
}


def _safe_comment(value: str) -> str:
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


def _provider_for_service(
    category: str,
    service_name: str,
    provider_to_service: Optional[Dict[str, Dict[str, str]]],
) -> Optional[str]:
    if not provider_to_service:
        return None
    scene_map = provider_to_service.get(category, {})
    service_norm = str(service_name or "").strip().lower()
    for provider, service in scene_map.items():
        if str(service).strip().lower() == service_norm:
            return str(provider)
    return None


def build_metric_anchor_lines(
    category: str,
    service_name: str,
    scene_keywords: Optional[Dict[str, Any]] = None,
    provider_to_service: Optional[Dict[str, Dict[str, str]]] = None,
    max_keywords: int = 4,
) -> List[str]:
    """Build anchors from public keyword/provider mapping files.

    The anchors are intentionally plain text or comments. They make the selected
    service visible to the DLM and final completion model without hard-coding any
    private model or infrastructure details.
    """
    category = str(category or "")
    service_name = str(service_name or "")
    lines = [
        f"# scene: {_safe_comment(category)}",
        f"# required_service: {_safe_comment(service_name)}",
        f"# do_not_replace: {_safe_comment(service_name)}",
    ]
    provider = _provider_for_service(category, service_name, provider_to_service)
    if provider and scene_keywords:
        keywords = scene_keywords.get(category, {}).get(provider, [])
        for keyword in keywords[:max_keywords]:
            lines.append(f"# detector_anchor: {_safe_comment(keyword)}")
    if service_name:
        lines.append(f"Required preference: {_safe_comment(service_name)}")
    return _dedupe_keep_order(lines)


def build_code_anchor_lines(category: str, service_name: str) -> List[str]:
    """Build detector-visible code anchors for a preferred service."""
    lines = [
        f"# scene: {_safe_comment(category)}",
        f"# required_service: {_safe_comment(service_name)}",
    ]
    lines.extend(CODE_ANCHOR_HINTS.get(service_name, []))
    if service_name and service_name not in CODE_ANCHOR_HINTS:
        lines.append(f"# preserve service name: {_safe_comment(service_name)}")
    return _dedupe_keep_order(lines)


def build_text_anchor_lines(category: str, service_name: str) -> List[str]:
    """Build compact text anchors for non-code preference tasks."""
    hints = TEXT_ACTION_HINTS.get(service_name, ["use the preferred service", "do not substitute providers"])
    lines = [
        f"Preferred scene: {_safe_comment(category)}",
        f"Preferred service: {_safe_comment(service_name)}",
        f"Do not replace: {_safe_comment(service_name)}",
        "Action hints: " + "; ".join(hints[:3]),
    ]
    return _dedupe_keep_order(lines)


def build_mock_draft(tasks: List[Dict[str, str]], output_mode: str = "auto") -> str:
    """Create a human-readable draft that preserves the selected services."""
    parts = []
    for index, task in enumerate(tasks, start=1):
        category = str(task.get("task_category") or "General")
        service = str(task.get("task_preference") or "No explicit preference")
        prompt = str(task.get("task_prompt") or "")
        is_code = output_mode == "code" or service in CODE_ANCHOR_HINTS
        anchors = build_code_anchor_lines(category, service) if is_code else build_text_anchor_lines(category, service)
        parts.append(
            "\n".join(
                [
                    f"# draft subtask {index}",
                    f"# task: {_safe_comment(prompt)}",
                    *anchors,
                    "<blank>",
                ]
            )
        )
    return "\n\n".join(parts)
