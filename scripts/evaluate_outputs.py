#!/usr/bin/env python3
"""Evaluate generated outputs with offline keyword metrics."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


ARTIFACT_ROOT = Path(__file__).resolve().parents[1]
if str(ARTIFACT_ROOT) not in sys.path:
    sys.path.insert(0, str(ARTIFACT_ROOT))

from pipeline.evaluation import evaluate_records, iter_jsonl, read_json  # noqa: E402


def resolve_input(path: str) -> str:
    candidate = Path(path)
    if candidate.is_absolute() or candidate.exists():
        return str(candidate)
    return str(ARTIFACT_ROOT / path)


def resolve_output(path: str) -> str:
    candidate = Path(path)
    if candidate.is_absolute() or candidate.parent.exists():
        return str(candidate)
    return str(ARTIFACT_ROOT / path)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", default="results/demo_outputs.jsonl")
    parser.add_argument("--config", default="configs/eval.yaml", help="Accepted for interface compatibility.")
    parser.add_argument("--service-keywords", default="configs/service_keywords.template.json")
    parser.add_argument("--provider-to-service", default="configs/provider_to_service.template.json")
    parser.add_argument("--output", default="results/demo_metrics.json")
    args = parser.parse_args()

    input_path = resolve_input(args.input)
    keyword_path = resolve_input(args.service_keywords)
    provider_path = resolve_input(args.provider_to_service)
    output_path = resolve_output(args.output)
    records = list(iter_jsonl(input_path))
    metrics = evaluate_records(
        records=records,
        scene_keywords=read_json(keyword_path),
        provider_to_service=read_json(provider_path),
    )
    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(metrics, indent=2, sort_keys=True) + "\n", encoding="ascii")
    print(f"wrote metrics for {metrics['n_records']} records to {output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
