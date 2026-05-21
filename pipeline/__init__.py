"""Public skeleton pipeline for provider preference control."""

from .anchors import build_code_anchor_lines, build_text_anchor_lines
from .completion import build_completion_prompt, mock_complete
from .demo_runner import run_demo_pipeline
from .evaluation import evaluate_records
from .task_planning import parse_task_plan, plan_from_preference_config

__all__ = [
    "build_code_anchor_lines",
    "build_text_anchor_lines",
    "build_completion_prompt",
    "mock_complete",
    "run_demo_pipeline",
    "evaluate_records",
    "parse_task_plan",
    "plan_from_preference_config",
]
