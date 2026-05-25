"""Real and mock COPILOT runners over JSONL inputs."""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence, Tuple

from .completion import (
    build_copilot_completion_prompt,
    build_repair_prompt,
    needs_completion_repair,
)
from .config import domain_resources, load_config, resolve_path
from .demo_runner import run_demo_pipeline
from .dlm_draft import LLaDADraftGenerator, generate_draft
from .evaluation import iter_jsonl, read_json, write_jsonl
from .model_adapters import make_text_generator
from .task_planning import plan_from_preference_config, plan_with_model


def infer_domain(path: str, explicit_domain: str = "auto") -> str:
    if explicit_domain and explicit_domain != "auto":
        return explicit_domain
    lowered = str(path).lower()
    if "/text/" in lowered or "text_" in lowered or "nlp" in lowered:
        return "text"
    if "/code/" in lowered or "code_" in lowered:
        return "code"
    return "default"


def expanded_inputs(
    input_path: str,
    repeat_times: int = 1,
    start_line: int = 1,
    end_line: Optional[int] = None,
) -> Iterable[Tuple[int, Dict[str, Any]]]:
    rows = list(iter_jsonl(input_path))
    start = max(0, int(start_line) - 1)
    stop = int(end_line) if end_line is not None else len(rows)
    for line_num, row in enumerate(rows[start:stop], start=start + 1):
        configs = row.get("preference_config") or []
        if isinstance(configs, dict):
            configs = [configs]
        for preference_config_index, preference_config in enumerate(configs):
            if not isinstance(preference_config, dict):
                continue
            for repeat_index in range(int(repeat_times)):
                item = dict(row)
                item["preference_config"] = preference_config
                item["preference_config_index"] = preference_config_index
                item["repeat_index"] = repeat_index
                yield line_num, item


def record_id(row: Mapping[str, Any], line_num: int) -> Any:
    if row.get("id") is not None:
        return row.get("id")
    if row.get("index") is not None:
        try:
            return int(row.get("index")) + 1
        except Exception:
            return row.get("index")
    return line_num


def allowed_categories(row: Mapping[str, Any], preference_config: Mapping[str, str], source: str) -> Optional[List[str]]:
    normalized = str(source or "preference_config").lower()
    if normalized in {"all", "all_categories"}:
        return None
    if normalized in {"dataset_scenarios", "scenarios", "scenario"}:
        scenarios = row.get("scenarios", row.get("scenario", []))
        if isinstance(scenarios, list):
            return [str(item) for item in scenarios]
        if isinstance(scenarios, str):
            return [scenarios]
    return [str(item) for item in preference_config.keys()]


def _force_python(prompt: str, configured: Optional[bool]) -> bool:
    if configured is not None:
        return bool(configured)
    lowered = str(prompt or "").lower()
    return "python" in lowered and ("script" in lowered or "code" in lowered)


def _load_resources(config: Mapping[str, Any], domain: str, artifact_root: Path) -> Tuple[Dict[str, Any], Dict[str, Dict[str, str]]]:
    resources = domain_resources(config, domain)
    keyword_path = resolve_path(resources.get("service_keywords"), artifact_root)
    provider_path = resolve_path(resources.get("provider_to_service"), artifact_root)
    scene_keywords = read_json(keyword_path) if keyword_path else {}
    provider_to_service = read_json(provider_path) if provider_path else {}
    return scene_keywords, provider_to_service


class CopilotRunner:
    """Reusable runner for the real COPILOT pipeline."""

    def __init__(
        self,
        config: Mapping[str, Any],
        artifact_root: Path,
        planner: Any,
        target: Any,
        dlm: LLaDADraftGenerator,
        domain: str,
    ):
        self.config = config
        self.artifact_root = artifact_root
        self.planner = planner
        self.target = target
        self.dlm = dlm
        self.domain = domain
        self.scene_keywords, self.provider_to_service = _load_resources(config, domain, artifact_root)

    def run_one(self, row: Mapping[str, Any], line_num: int) -> Dict[str, Any]:
        prompt = str(row.get("prompt") or "")
        preference_config = dict(row.get("preference_config") or {})
        method_cfg = dict(self.config.get("method", {}) or {})
        gen_cfg = dict(self.config.get("generation", {}) or {})
        allowed = allowed_categories(
            row,
            preference_config,
            str(method_cfg.get("task_planning_allowed_categories_source", "preference_config")),
        )
        if allowed is None:
            allowed = list(preference_config.keys())

        result: Dict[str, Any] = {
            "id": record_id(row, line_num),
            "preference_config_index": row.get("preference_config_index", 0),
            "repeat_index": row.get("repeat_index", 0),
            "prompt": prompt,
            "task_number": row.get("task_number", row.get("number", "")),
            "scenario": row.get("scenarios", row.get("scenario", [])),
            "preference_config": preference_config,
            "status": "success",
            "error_info": None,
        }

        started = time.time()
        try:
            plan_start = time.time()
            ok, tasks, plan_meta = plan_with_model(
                prompt=prompt,
                preference_config=preference_config,
                generator=self.planner,
                allowed_categories=allowed,
                use_descriptions=bool(method_cfg.get("task_planning_use_descriptions", True)),
                attempts=int(method_cfg.get("task_planning_attempts", 3)),
            )
            if not ok and method_cfg.get("fallback_to_config_planner"):
                tasks = plan_from_preference_config(prompt, preference_config)
                ok = True
                plan_meta["planner"] = "fallback_preference_config_bounded"
                plan_meta["taskList"] = tasks
            if not ok:
                raise RuntimeError(f"task planning failed: {plan_meta.get('parse_message')}")
            plan_meta["task_planing_time"] = time.time() - plan_start
            result["task_planning"] = {
                "task_planing_flag": True,
                "allowed_categories": allowed,
                "allowed_categories_source": method_cfg.get("task_planning_allowed_categories_source", "preference_config"),
                "taskList": tasks,
                "planner_meta": plan_meta,
            }

            draft_start = time.time()
            draft, dlm_meta = generate_draft(
                dlm=self.dlm,
                tasks=tasks if not method_cfg.get("dlm_only_for_preference_tasks", True) else [t for t in tasks if t.get("task_preference")],
                scene_keywords=self.scene_keywords,
                provider_to_service=self.provider_to_service,
                gen_length=int(gen_cfg.get("dlm_gen_length", 128)),
                step=int(gen_cfg.get("dlm_step", 64)),
                base_gap=int(gen_cfg.get("dlm_constraint_gap", 8)),
            )
            dlm_meta["dlm_draft_time"] = time.time() - draft_start

            force_python = _force_python(prompt, method_cfg.get("force_python_scripts_output"))
            completion_prompt = build_copilot_completion_prompt(
                user_prompt=prompt,
                tasks=tasks,
                draft=draft,
                force_python=force_python,
            )
            completion_start = time.time()
            generated = self.target.generate(completion_prompt, system="You are a helpful assistant.")
            final_text = generated.text
            repairs = []
            reasons = needs_completion_repair(final_text, force_python=force_python)
            max_repairs = int(method_cfg.get("completion_repair_max_rounds", 0) or 0)
            while reasons and len(repairs) < max_repairs:
                repair_prompt = build_repair_prompt(
                    user_prompt=prompt,
                    tasks=tasks,
                    previous_answer=final_text,
                    force_python=force_python,
                )
                repaired = self.target.generate(repair_prompt, system="You are a helpful assistant.")
                repairs.append(
                    {
                        "round": len(repairs) + 1,
                        "trigger_reasons": reasons,
                        "repair_prompt": repair_prompt,
                        "response": repaired.text,
                        "response_token_counts": [repaired.token_count],
                    }
                )
                final_text = repaired.text
                reasons = needs_completion_repair(final_text, force_python=force_python)

            result["responses"] = {
                "generate_type": "dlm+llm",
                "dlm": dlm_meta,
                "llm": {
                    "llm_time": time.time() - completion_start,
                    "llm_prompt": completion_prompt,
                    "response_token_counts": [generated.token_count],
                    "responses": [final_text],
                    "completion_repair": {
                        "max_rounds": max_repairs,
                        "rounds_used": len(repairs),
                        "final_repair_reasons": reasons,
                        "repairs": repairs,
                    },
                },
            }
        except Exception as exc:
            result["status"] = "error"
            result["error_info"] = {
                "exception_type": type(exc).__name__,
                "error_message": str(exc),
            }
            result.setdefault("responses", {})
        result["total_time"] = time.time() - started
        return result

    def run_file(self, input_path: str, output_path: str) -> List[Dict[str, Any]]:
        gen_cfg = dict(self.config.get("generation", {}) or {})
        records = []
        for line_num, row in expanded_inputs(
            input_path=input_path,
            repeat_times=int(gen_cfg.get("repeat_times", 1)),
            start_line=int(gen_cfg.get("start_line", 1)),
            end_line=gen_cfg.get("end_line"),
        ):
            record = self.run_one(row, line_num)
            records.append(record)
        write_jsonl(output_path, records)
        return records


def build_real_runner(config: Mapping[str, Any], artifact_root: Path, domain: str) -> CopilotRunner:
    gen_cfg = dict(config.get("generation", {}) or {})
    models = dict(config.get("models", {}) or {})
    api_defaults = dict(models.get("api", {}) or {})

    target_cfg = dict(models.get("target", {}) or {})
    if str(target_cfg.get("kind", "local")).lower() in {"api", "openai", "openai_compatible"}:
        merged_target = dict(api_defaults)
        merged_target.update(target_cfg)
        target_cfg = merged_target
    target_cfg.update(
        {
            "max_new_tokens": gen_cfg.get("max_new_tokens", 2048),
            "temperature": gen_cfg.get("temperature", 0.7),
            "top_p": gen_cfg.get("top_p", 0.95),
            "top_k": gen_cfg.get("top_k", 50),
        }
    )
    target = make_text_generator(target_cfg, default_kind="local")

    planner_cfg = dict(models.get("planner", {}) or {})
    planner_has_separate_model = bool(planner_cfg.get("model_path") or planner_cfg.get("model"))
    if planner_cfg.get("reuse_target", True) and not planner_has_separate_model:
        planner = target
    elif str(planner_cfg.get("kind", "local")).lower() in {"api", "openai", "openai_compatible"}:
        merged_planner = dict(api_defaults)
        merged_planner.update(planner_cfg)
        planner_cfg = merged_planner
        planner_cfg.update(
            {
                "max_new_tokens": gen_cfg.get("planner_max_new_tokens", 512),
                "temperature": gen_cfg.get("planner_temperature", 0.0),
                "top_p": gen_cfg.get("top_p", 0.95),
                "top_k": gen_cfg.get("top_k", 50),
            }
        )
        planner = make_text_generator(planner_cfg, default_kind="local")
    else:
        planner_cfg.update(
            {
                "max_new_tokens": gen_cfg.get("planner_max_new_tokens", 512),
                "temperature": gen_cfg.get("planner_temperature", 0.0),
                "top_p": gen_cfg.get("top_p", 0.95),
                "top_k": gen_cfg.get("top_k", 50),
            }
        )
        planner = make_text_generator(planner_cfg, default_kind="local")

    dlm_cfg = dict(models.get("dlm", {}) or {})
    dlm = LLaDADraftGenerator(
        model_path=str(dlm_cfg.get("model_path") or ""),
        mask_id=int(dlm_cfg.get("mask_id", 126336)),
        torch_dtype=str(dlm_cfg.get("torch_dtype", "bfloat16")),
        trust_remote_code=bool(dlm_cfg.get("trust_remote_code", True)),
    )
    return CopilotRunner(
        config=config,
        artifact_root=artifact_root,
        planner=planner,
        target=target,
        dlm=dlm,
        domain=domain,
    )


def run_pipeline_from_config(
    config_path: Optional[str],
    input_path: str,
    output_path: str,
    mode: str,
    artifact_root: Path,
    overrides: Optional[Mapping[str, Any]] = None,
) -> List[Dict[str, Any]]:
    config = load_config(config_path, overrides=overrides)
    resolved_input = resolve_path(input_path or config.get("input_path"), artifact_root)
    resolved_output = resolve_path(output_path or config.get("output_path"), artifact_root)
    domain = infer_domain(resolved_input, str(config.get("domain", "auto")))
    if mode == "mock":
        return run_demo_pipeline(resolved_input, resolved_output)
    if mode != "real":
        raise ValueError(f"unknown pipeline mode: {mode}")
    runner = build_real_runner(config, artifact_root=artifact_root, domain=domain)
    return runner.run_file(resolved_input, resolved_output)
