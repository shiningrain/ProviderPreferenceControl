#!/usr/bin/env python3
"""Run public prompt baselines over released or user-provided JSONL data."""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, Optional, Tuple


ARTIFACT_ROOT = Path(__file__).resolve().parents[1]
if str(ARTIFACT_ROOT) not in sys.path:
    sys.path.insert(0, str(ARTIFACT_ROOT))
if str(Path(__file__).resolve().parent) not in sys.path:
    sys.path.insert(0, str(Path(__file__).resolve().parent))

from pipeline.config import load_config, resolve_path  # noqa: E402
from pipeline.evaluation import iter_jsonl, write_jsonl  # noqa: E402
from pipeline.model_adapters import MockTextGenerator, make_text_generator  # noqa: E402
from baseline_utils import (  # noqa: E402
    build_constrained_prompt,
    build_grouped_prompt,
    build_stepwise_plan_prompt,
    build_stepwise_response_prompt,
    build_token_bias,
    build_zero_shot_prompt,
)


def _expanded_inputs(input_path: str, repeat_times: int, start_line: int, end_line: Optional[int]) -> Iterable[Tuple[int, Dict[str, Any]]]:
    rows = list(iter_jsonl(input_path))
    start = max(0, int(start_line) - 1)
    stop = int(end_line) if end_line is not None else len(rows)
    for line_num, row in enumerate(rows[start:stop], start=start + 1):
        configs = row.get("preference_config") or []
        if isinstance(configs, dict):
            configs = [configs]
        for pref_index, preference_config in enumerate(configs):
            if not isinstance(preference_config, dict):
                continue
            for repeat_index in range(int(repeat_times)):
                item = dict(row)
                item["preference_config"] = preference_config
                item["preference_config_index"] = pref_index
                item["repeat_index"] = repeat_index
                yield line_num, item


def _record_id(row: Mapping[str, Any], line_num: int) -> Any:
    if row.get("id") is not None:
        return row.get("id")
    if row.get("index") is not None:
        try:
            return int(row.get("index")) + 1
        except Exception:
            return row.get("index")
    return line_num


def _normalize_method(method: str) -> str:
    return method.strip().replace("-", "_").lower()


def _generate(generator: Any, prompt: str, token_bias: Optional[Mapping[int, float]] = None) -> Tuple[str, Optional[int]]:
    result = generator.generate(prompt, system="You are a helpful assistant.", token_bias=token_bias)
    return str(result.text), result.token_count


def run_method(method: str, row: Mapping[str, Any], generator: Any, generator_kind: str) -> Dict[str, Any]:
    normalized = _normalize_method(method)
    prompt = str(row.get("prompt") or "")
    preference_config = dict(row.get("preference_config") or {})
    responses: Dict[str, Any] = {"method": normalized}
    started = time.time()

    if normalized == "zero_shot":
        final_prompt = build_zero_shot_prompt(prompt, preference_config)
        text, token_count = _generate(generator, final_prompt)
        responses.update({"prompt": final_prompt, "response_token_counts": [token_count], "final_response": [text]})
    elif normalized == "grouped":
        final_prompt = build_grouped_prompt(prompt, preference_config)
        text, token_count = _generate(generator, final_prompt)
        responses.update({"prompt": final_prompt, "response_token_counts": [token_count], "final_response": [text]})
    elif normalized == "step_wise":
        plan_prompt = build_stepwise_plan_prompt(prompt, preference_config)
        plan, plan_tokens = _generate(generator, plan_prompt)
        final_prompt = build_stepwise_response_prompt(prompt, preference_config, plan)
        text, token_count = _generate(generator, final_prompt)
        responses.update(
            {
                "plan_prompt": plan_prompt,
                "stage_1_plan": [plan],
                "stage1_response_token_counts": [plan_tokens],
                "prompt": final_prompt,
                "response_token_counts": [token_count],
                "final_response": [text],
            }
        )
    elif normalized == "constrained":
        if generator_kind != "local" or not getattr(generator, "tokenizer", None):
            responses.update(
                {
                    "status": "skipped",
                    "reason": "constrained baseline requires a local tokenizer/model for token-level bias",
                    "final_response": [""],
                }
            )
        else:
            final_prompt = build_constrained_prompt(prompt, preference_config)
            token_bias = build_token_bias(preference_config, generator.tokenizer)
            text, token_count = _generate(generator, final_prompt, token_bias=token_bias)
            responses.update(
                {
                    "prompt": final_prompt,
                    "response_token_counts": [token_count],
                    "final_response": [text],
                    "boosted_token_count": len(token_bias),
                }
            )
    else:
        raise ValueError(f"unknown baseline method: {method}")

    responses["llm_time"] = time.time() - started
    return responses


def main() -> int:
    parser = argparse.ArgumentParser(description="Run public prompt baselines.")
    parser.add_argument("--config", default="configs/baseline.template.yaml")
    parser.add_argument("--input", default="dataset/examples.jsonl")
    parser.add_argument("--output", default="outputs/baseline_outputs.jsonl")
    parser.add_argument("--methods", default="zero_shot,grouped,step_wise,constrained")
    parser.add_argument("--generator-kind", choices=["mock", "local", "api"], default=None)
    parser.add_argument("--model", default=None, help="Local model path or API model name.")
    parser.add_argument("--api-base", default=None)
    parser.add_argument("--credential-env", default=None)
    parser.add_argument("--repeat-times", type=int, default=None)
    parser.add_argument("--start-line", type=int, default=None)
    parser.add_argument("--end-line", type=int, default=None)
    args = parser.parse_args()

    config = load_config(resolve_path(args.config, ARTIFACT_ROOT))
    baseline_cfg = dict(config.get("baseline", {}) or {})
    gen_cfg = dict(config.get("generation", {}) or {})
    model_cfg = dict(config.get("models", {}).get("target", {}) or {})
    api_cfg = dict(config.get("models", {}).get("api", {}) or {})

    generator_kind = args.generator_kind or str(baseline_cfg.get("generator_kind", "mock"))
    if generator_kind == "mock":
        generator = MockTextGenerator(label="baseline")
    else:
        if generator_kind == "api":
            model_cfg = {
                "kind": "api",
                "base_url": args.api_base or api_cfg.get("base_url"),
                "credential_env": args.credential_env or api_cfg.get("credential_env", "PROVIDER_KEY"),
                "model": args.model or api_cfg.get("model"),
                "max_new_tokens": gen_cfg.get("max_new_tokens", 2048),
                "temperature": gen_cfg.get("temperature", 0.7),
            }
        else:
            model_cfg.update(
                {
                    "kind": "local",
                    "model_path": args.model or model_cfg.get("model_path"),
                    "max_new_tokens": gen_cfg.get("max_new_tokens", 2048),
                    "temperature": gen_cfg.get("temperature", 0.7),
                    "top_p": gen_cfg.get("top_p", 0.95),
                    "top_k": gen_cfg.get("top_k", 50),
                }
            )
        generator = make_text_generator(model_cfg, default_kind=generator_kind)

    input_path = resolve_path(args.input, ARTIFACT_ROOT)
    output_path = resolve_path(args.output, ARTIFACT_ROOT)
    repeat_times = args.repeat_times if args.repeat_times is not None else int(gen_cfg.get("repeat_times", 1))
    start_line = args.start_line if args.start_line is not None else int(gen_cfg.get("start_line", 1))
    end_line = args.end_line if args.end_line is not None else gen_cfg.get("end_line")
    methods = [_normalize_method(item) for item in args.methods.split(",") if item.strip()]

    records: List[Dict[str, Any]] = []
    for line_num, row in _expanded_inputs(input_path, repeat_times, start_line, end_line):
        for method in methods:
            record = {
                "id": _record_id(row, line_num),
                "preference_config_index": row.get("preference_config_index", 0),
                "repeat_index": row.get("repeat_index", 0),
                "task_number": row.get("task_number", row.get("number", "")),
                "method": method,
                "prompt": row.get("prompt", ""),
                "scenario": row.get("scenarios", row.get("scenario", [])),
                "preference_config": row.get("preference_config", {}),
                "status": "success",
                "error_info": None,
            }
            try:
                responses = run_method(method, row, generator, generator_kind)
                if responses.get("status") == "skipped":
                    record["status"] = "skipped"
                    record["skip_reason"] = responses.get("reason")
                record["responses"] = responses
            except Exception as exc:
                record["status"] = "error"
                record["error_info"] = {"exception_type": type(exc).__name__, "error_message": str(exc)}
                record["responses"] = {}
            records.append(record)

    write_jsonl(output_path, records)
    print(f"wrote {len(records)} baseline records to {output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
