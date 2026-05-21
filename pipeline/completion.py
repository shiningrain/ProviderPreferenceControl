"""Completion prompt builder and mock completion path."""

from __future__ import annotations

from typing import Dict, List


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
