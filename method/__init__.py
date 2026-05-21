"""Sanitized method-code interfaces for provider preference control."""

from .anchor_templates import build_code_anchor_lines, build_text_anchor_bundle
from .completion_interface import CompletionRequest, build_completion_prompt, needs_completion_repair
from .dlm_draft_interface import DraftRequest, prepare_constrained_draft_inputs
from .pipeline_flow import MethodConfig, run_preference_control
from .task_planning import TaskPlanner, parse_task_plan

__all__ = [
    "CompletionRequest",
    "DraftRequest",
    "MethodConfig",
    "TaskPlanner",
    "build_code_anchor_lines",
    "build_text_anchor_bundle",
    "build_completion_prompt",
    "needs_completion_repair",
    "parse_task_plan",
    "prepare_constrained_draft_inputs",
    "run_preference_control",
]
