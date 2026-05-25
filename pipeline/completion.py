"""Completion prompt builders and mock completion path."""

from __future__ import annotations

from typing import Any, Dict, List, Mapping, Sequence


COMPLETION_SYSTEM = """You are the completion model in a provider preference control pipeline.

Rules:
- Preserve every matched service from the task plan.
- Do not replace a matched service with another provider.
- Cover every planned subtask.
- If producing code, return a single fenced python code block.
- Leave private credentials, keys, and account-specific values as placeholders.
"""


def build_completion_prompt(user_prompt: str, tasks: List[Dict[str, str]], draft: str) -> str:
    """Build a target-LLM prompt from planned tasks and a draft."""
    lines = [
        COMPLETION_SYSTEM.strip(),
        "",
        "User request:",
        user_prompt,
        "",
        "Matched preferences:",
    ]
    for task in tasks:
        category = task.get("task_category") or "None"
        service = task.get("task_preference") or "No explicit preference"
        task_prompt = task.get("task_prompt") or ""
        lines.append(f"- {category}: {service} | {task_prompt}")
    lines.extend(["", "Draft to preserve:", draft, "", "Final answer:"])
    return "\n".join(lines)


def build_copilot_completion_prompt(
    user_prompt: str,
    tasks: Sequence[Mapping[str, Any]],
    draft: str,
    force_python: bool = False,
    forbid_anchor_leakage: bool = True,
) -> str:
    """Build the real COPILOT final-completion prompt."""
    preference_lines = []
    checklist_lines = []
    services = []
    for task in tasks:
        category = task.get("task_category") or "None"
        service = task.get("task_preference")
        task_prompt = str(task.get("task_prompt") or "").strip()
        if service:
            preference_lines.append(f"- {category}: use {service}")
            services.append(str(service))
            checklist_lines.append(f"- [PREFERENCE-BOUND] {task_prompt} (scene={category}, service={service})")
        else:
            checklist_lines.append(f"- [NO-PREFERENCE] {task_prompt} (scene={category})")

    preference_block = "\n".join(preference_lines) if preference_lines else "(none)"
    checklist_block = "\n".join(checklist_lines) if checklist_lines else "(none)"
    service_block = ", ".join(dict.fromkeys(services)) if services else "the specified services"
    output_rules = []
    if force_python:
        output_rules.extend(
            [
                "- Return a single fenced ```python``` code block and nothing else.",
                "- If manifests or commands are needed, embed them as Python strings or helper functions.",
            ]
        )
    if forbid_anchor_leakage:
        output_rules.append("- Remove draft-only scaffold markers and do not copy anchor headers verbatim.")
    output_rules.extend(
        [
            "- Remove all <blank>, TODO, and unfinished placeholder text.",
            "- Do not replace required services with alternatives.",
            "- Do not introduce unrelated providers for no-preference subtasks.",
        ]
    )

    return f"""You are the final completion model in COPILOT, a provider preference control pipeline.

Task description:
{user_prompt}

Required services matched by task planning:
{preference_block}

Planned subtasks to cover:
{checklist_block}

DLM draft with preference anchors:
{draft}

Output requirements:
{chr(10).join(output_rules)}

Preserve these required service choices exactly when they are used: {service_block}.

Return only the final user-facing answer."""


def needs_completion_repair(text: str, force_python: bool = False) -> List[str]:
    """Return repair trigger reasons for a final completion."""
    reasons = []
    if not str(text or "").strip():
        return ["empty_output"]
    if "<blank>" in str(text):
        reasons.append("contains_blank_placeholder")
    lowered = str(text).lower()
    if force_python and "```python" not in lowered:
        reasons.append("missing_python_code_fence")
    return reasons


def build_repair_prompt(
    user_prompt: str,
    tasks: Sequence[Mapping[str, Any]],
    previous_answer: str,
    force_python: bool = False,
) -> str:
    preference_lines = []
    checklist_lines = []
    services = []
    for task in tasks:
        category = task.get("task_category") or "None"
        service = task.get("task_preference")
        task_prompt = str(task.get("task_prompt") or "").strip()
        if service:
            services.append(str(service))
            preference_lines.append(f"- {category}: use {service}")
        checklist_lines.append(f"- {task_prompt} (scene={category})")
    python_rule = "- Return a single fenced ```python``` code block and nothing else." if force_python else ""
    return f"""Repair the previous answer for the same provider preference control task.

Task description:
{user_prompt}

Required services:
{chr(10).join(preference_lines) if preference_lines else "(none)"}

Subtasks to cover:
{chr(10).join(checklist_lines) if checklist_lines else "(none)"}

Previous answer:
{previous_answer}

Repair rules:
- Preserve required services exactly: {", ".join(dict.fromkeys(services)) if services else "none"}.
- Do not add unrelated providers.
- Remove <blank>, TODO, unfinished fragments, and draft-only scaffold markers.
{python_rule}

Return only the repaired final answer."""


def mock_complete(user_prompt: str, tasks: List[Dict[str, str]], draft: str) -> str:
    """A deterministic no-model completion used by the demo runner."""
    code_lines = []
    text_lines = []
    for task in tasks:
        category = str(task.get("task_category") or "General")
        service = str(task.get("task_preference") or "No explicit preference")
        if service.startswith("Amazon "):
            code_lines.append(f"# {category}: use {service}")
            if service == "Amazon S3":
                code_lines.extend(
                    [
                        "import boto3",
                        "s3_client = boto3.client('s3')",
                        "s3_client.upload_file('<local_file>', '<bucket>', '<key>')",
                    ]
                )
            elif service == "Amazon SNS":
                code_lines.extend(
                    [
                        "import boto3",
                        "sns_client = boto3.client('sns')",
                        "sns_client.publish(TopicArn='<topic_arn>', Message='processing complete')",
                    ]
                )
            else:
                code_lines.append(f"# preserve required service: {service}")
        else:
            text_lines.append(f"- For {category}, use {service} and do not substitute another provider.")

    if code_lines:
        unique_code_lines = []
        for line in code_lines:
            if line not in unique_code_lines:
                unique_code_lines.append(line)
        return "```python\n" + "\n".join(unique_code_lines) + "\n```"

    return "\n".join(["Preference-controlled response:", *text_lines])
