"""Completion-stage interface and prompt builder."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List


@dataclass
class CompletionRequest:
    user_prompt: str
    task_list: List[Dict[str, str]]
    draft: str
    force_python_output: bool = False
    forbid_code_fences: bool = False
    forbid_anchor_leakage: bool = False


def infer_force_python_output(prompt: str) -> bool:
    lowered = str(prompt or "").lower()
    return "python" in lowered and any(term in lowered for term in ["script", "code", "code block"])


def format_preference_lines(task_list: List[Dict[str, str]]) -> str:
    lines = []
    for task in task_list:
        category = task.get("task_category")
        service = task.get("task_preference")
        if category and service:
            lines.append(f"- {category}: use {service}")
    return "\n".join(lines) if lines else "- No explicit provider preference"


def format_subtask_checklist(task_list: List[Dict[str, str]]) -> str:
    lines = []
    for task in task_list:
        task_prompt = str(task.get("task_prompt") or "").strip()
        if not task_prompt:
            continue
        category = task.get("task_category")
        service = task.get("task_preference")
        if service:
            lines.append(f"- [PREFERENCE-BOUND] {task_prompt} (scene={category}, service={service})")
        else:
            lines.append(f"- [NO-PREFERENCE] {task_prompt} (scene={category})")
    return "\n".join(lines) if lines else "- (none)"


def build_completion_prompt(request: CompletionRequest) -> str:
    force_python = request.force_python_output or infer_force_python_output(request.user_prompt)
    output_rules = []
    if force_python:
        output_rules.extend(
            [
                "Output format:",
                "- Return a single fenced python code block and nothing else.",
                "- Keep credentials, account ids, and environment-specific values as placeholders.",
            ]
        )
    if request.forbid_code_fences:
        output_rules.extend(["Output format:", "- Return plain natural language, not fenced code."])
    if request.forbid_anchor_leakage:
        output_rules.append("- Rewrite draft scaffold markers into clean user-facing text.")

    return "\n".join(
        [
            "You are the final completion model in a provider preference control pipeline.",
            "",
            "Required provider choices:",
            format_preference_lines(request.task_list),
            "",
            "Subtasks to cover:",
            format_subtask_checklist(request.task_list),
            "",
            *output_rules,
            "",
            "User request:",
            request.user_prompt,
            "",
            "Draft from the constrained generator:",
            request.draft or "(no draft)",
            "",
            "Instructions:",
            "- Preserve the listed provider choices exactly where they apply.",
            "- Do not replace a matched service with a competing provider.",
            "- Complete unresolved <blank> placeholders with reasonable generic values.",
            "- Do not include private credentials or deployment-specific paths.",
            "",
            "Final answer:",
        ]
    )


def needs_completion_repair(
    text: str,
    force_python_output: bool = False,
    forbid_code_fences: bool = False,
    forbid_anchor_leakage: bool = False,
) -> List[str]:
    reasons: List[str] = []
    if not text or not str(text).strip():
        return ["empty_output"]
    lowered = str(text).lower()
    if "<blank>" in lowered:
        reasons.append("contains_blank_placeholder")
    if force_python_output:
        if "```" not in lowered:
            reasons.append("missing_code_fence")
        elif "```python" not in lowered:
            reasons.append("missing_python_code_fence")
    if forbid_code_fences and "```" in lowered:
        reasons.append("contains_code_fence")
    if forbid_anchor_leakage:
        leaked_markers = [
            "# ===",
            "# anchor-note:",
            "preferred action hints:",
            "preferred scene:",
            "preferred service:",
            "required_preference:",
            "do_not_replace:",
        ]
        if any(marker in lowered for marker in leaked_markers):
            reasons.append("contains_anchor_leakage")
    return reasons
