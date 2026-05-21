"""Public method flow close to the paper implementation.

The function in this module wires together task planning, constrained draft
preparation, and completion prompt construction. It does not load local models,
launch jobs, resume raw outputs, or access private infrastructure.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Optional, Protocol

from .completion_interface import CompletionRequest, build_completion_prompt, infer_force_python_output
from .dlm_draft_interface import DraftModel, prepare_constrained_draft_inputs, render_draft_from_parts
from .task_planning import PlanningModel, TaskPlanner, surface_split_fixed_bind


class CompletionModel(Protocol):
    def generate(self, prompt: str) -> str:
        """Return a final response for a completion prompt."""


@dataclass
class MethodConfig:
    task_planning_allowed_categories_source: str = "preference_config"
    disable_task_planning: bool = False
    disable_dlm_draft: bool = False
    dlm_only_for_preference_tasks: bool = True
    dlm_gen_length: int = 128
    dlm_steps: int = 64
    force_python_output: Optional[bool] = None


def allowed_categories_for_run(
    config: MethodConfig,
    row: Dict[str, object],
    preference_config: Dict[str, str],
) -> Optional[List[str]]:
    source = config.task_planning_allowed_categories_source
    if source == "all":
        return None
    if source == "dataset_scenarios":
        scenarios = row.get("scenarios", row.get("scenario", []))
        if isinstance(scenarios, list):
            return [str(item) for item in scenarios]
        if isinstance(scenarios, str):
            return [scenarios]
    return list(preference_config.keys())


def run_preference_control(
    row: Dict[str, object],
    preference_config: Dict[str, str],
    planning_model: Optional[PlanningModel] = None,
    draft_model: Optional[DraftModel] = None,
    completion_model: Optional[CompletionModel] = None,
    config: Optional[MethodConfig] = None,
) -> Dict[str, object]:
    """Run the public method flow with plug-in model interfaces."""
    config = config or MethodConfig()
    prompt = str(row.get("prompt") or "")
    planner = TaskPlanner()

    if config.disable_task_planning or planning_model is None:
        task_list = surface_split_fixed_bind(prompt, preference_config)
        planning_result = {
            "task_planning_variant": "surface_split_fixed_bind",
            "task_planning_flag": True,
            "task_planning_times": 0,
            "allowed_categories": list(preference_config.keys()),
            "taskList": task_list,
        }
    else:
        ok, attempts, task_list = planner.plan(prompt, preference_config, planning_model)
        planning_result = {
            "task_planning_variant": "model_task_planning",
            "task_planning_flag": ok,
            "task_planning_times": attempts,
            "allowed_categories": allowed_categories_for_run(config, row, preference_config),
            "taskList": task_list,
        }

    response_info: Dict[str, object] = {"generate_type": "dlm+llm"}
    draft = ""
    if config.disable_dlm_draft or draft_model is None:
        response_info["dlm"] = {"skipped": True, "reason": "no public draft model supplied"}
    else:
        task_list_for_dlm = [task for task in task_list if task.get("task_preference")] if config.dlm_only_for_preference_tasks else task_list
        draft_request = prepare_constrained_draft_inputs(
            prompt=prompt,
            task_list=task_list_for_dlm,
            tokenizer=getattr(draft_model, "tokenizer", None),
            gen_length=config.dlm_gen_length,
            steps=config.dlm_steps,
        )
        generated_parts = draft_model.generate_with_constraints(
            draft_request.prompts,
            draft_request.constraints,
            steps=draft_request.steps,
            gen_len=draft_request.gen_length,
            block_len=draft_request.gen_length,
        )
        draft = render_draft_from_parts(task_list_for_dlm, generated_parts)
        response_info["dlm"] = {
            "skipped": False,
            "draft_batch_size": len(draft_request.prompts),
            "anchor_meta": draft_request.anchor_meta,
            "draft": draft,
        }

    force_python = config.force_python_output
    if force_python is None:
        force_python = infer_force_python_output(prompt)
    completion_request = CompletionRequest(
        user_prompt=prompt,
        task_list=task_list,
        draft=draft,
        force_python_output=bool(force_python),
    )
    completion_prompt = build_completion_prompt(completion_request)
    if completion_model is None:
        final_response = ""
        response_info["llm"] = {"skipped": True, "completion_prompt": completion_prompt, "responses": []}
    else:
        final_response = completion_model.generate(completion_prompt)
        response_info["llm"] = {"skipped": False, "completion_prompt": completion_prompt, "responses": [final_response]}

    return {
        "status": "success",
        "task_planning": planning_result,
        "responses": response_info,
    }
