#!/usr/bin/env python3
"""Run the public COPILOT pipeline."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path


ARTIFACT_ROOT = Path(__file__).resolve().parents[1]
if str(ARTIFACT_ROOT) not in sys.path:
    sys.path.insert(0, str(ARTIFACT_ROOT))

from pipeline.runner import run_pipeline_from_config  # noqa: E402


def resolve_input(path: str) -> str:
    candidate = Path(path)
    if candidate.is_absolute() or candidate.exists():
        return str(candidate)
    artifact_candidate = ARTIFACT_ROOT / path
    return str(artifact_candidate)


def resolve_output(path: str) -> str:
    candidate = Path(path)
    if candidate.is_absolute() or candidate.parent.exists():
        return str(candidate)
    return str(ARTIFACT_ROOT / path)


def main() -> int:
    parser = argparse.ArgumentParser(description="Run COPILOT in real or mock mode.")
    parser.add_argument("--mode", choices=["mock", "real"], default="mock")
    parser.add_argument("--config", default="configs/example.yaml")
    parser.add_argument("--input", default="dataset/examples.jsonl")
    parser.add_argument("--output", default="outputs/demo_outputs.jsonl")
    parser.add_argument("--domain", choices=["auto", "code", "text", "default"], default=None)
    parser.add_argument("--planner-model", default=None, help="Optional local planner model path.")
    parser.add_argument("--dlm-model", default=None, help="Local LLaDA-style DLM checkpoint path.")
    parser.add_argument("--target-llm", default=None, help="Local target completion model path.")
    parser.add_argument("--planner-kind", choices=["local", "api", "mock"], default=None)
    parser.add_argument("--target-kind", choices=["local", "api", "mock"], default=None)
    parser.add_argument("--api-base", default=None, help="OpenAI-compatible base URL for API planner/target.")
    parser.add_argument("--api-model", default=None, help="OpenAI-compatible model name for API planner/target.")
    parser.add_argument("--credential-env", default=None, help="Environment variable that stores the API credential.")
    parser.add_argument("--repeat-times", type=int, default=None)
    parser.add_argument("--start-line", type=int, default=None)
    parser.add_argument("--end-line", type=int, default=None)
    args = parser.parse_args()

    overrides = {"models": {"planner": {}, "target": {}, "dlm": {}, "api": {}}, "generation": {}, "method": {}}
    if args.domain is not None:
        overrides["domain"] = args.domain
    if args.repeat_times is not None:
        overrides["generation"]["repeat_times"] = args.repeat_times
    if args.start_line is not None:
        overrides["generation"]["start_line"] = args.start_line
    if args.end_line is not None:
        overrides["generation"]["end_line"] = args.end_line
    if args.planner_model:
        overrides["models"]["planner"]["model_path"] = args.planner_model
        overrides["models"]["planner"]["reuse_target"] = False
    if args.dlm_model:
        overrides["models"]["dlm"]["model_path"] = args.dlm_model
    if args.target_llm:
        overrides["models"]["target"]["model_path"] = args.target_llm
    if args.planner_kind:
        overrides["models"]["planner"]["kind"] = args.planner_kind
        if args.planner_kind == "api":
            overrides["models"]["planner"]["reuse_target"] = False
    if args.target_kind:
        overrides["models"]["target"]["kind"] = args.target_kind
    if args.api_base:
        overrides["models"]["api"]["base_url"] = args.api_base
        overrides["models"]["planner"]["base_url"] = args.api_base
        overrides["models"]["target"]["base_url"] = args.api_base
    if args.api_model:
        overrides["models"]["api"]["model"] = args.api_model
        overrides["models"]["planner"]["model"] = args.api_model
        overrides["models"]["target"]["model"] = args.api_model
    if args.credential_env:
        overrides["models"]["api"]["credential_env"] = args.credential_env
        overrides["models"]["planner"]["credential_env"] = args.credential_env
        overrides["models"]["target"]["credential_env"] = args.credential_env

    input_path = resolve_input(args.input)
    output_path = resolve_output(args.output)
    records = run_pipeline_from_config(
        config_path=resolve_input(args.config),
        input_path=input_path,
        output_path=output_path,
        mode=args.mode,
        artifact_root=ARTIFACT_ROOT,
        overrides=overrides,
    )
    print(f"wrote {len(records)} records to {output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
