"""Public COPILOT pipeline for provider preference control."""

from .anchors import build_code_anchor_lines, build_metric_anchor_lines, build_text_anchor_lines
from .completion import build_completion_prompt, build_copilot_completion_prompt, mock_complete
from .demo_runner import run_demo_pipeline
from .dlm_draft import LLaDADraftGenerator, generate_draft
from .evaluation import evaluate_records
from .runner import CopilotRunner, run_pipeline_from_config
from .task_planning import parse_task_plan, plan_from_preference_config, plan_with_model

__all__ = [
    "build_code_anchor_lines",
    "build_metric_anchor_lines",
    "build_text_anchor_lines",
    "build_completion_prompt",
    "build_copilot_completion_prompt",
    "mock_complete",
    "LLaDADraftGenerator",
    "generate_draft",
    "CopilotRunner",
    "run_pipeline_from_config",
    "run_demo_pipeline",
    "evaluate_records",
    "parse_task_plan",
    "plan_from_preference_config",
    "plan_with_model",
]
