#!/usr/bin/env python3
"""Run the public no-GPU demo pipeline."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path


ARTIFACT_ROOT = Path(__file__).resolve().parents[1]
if str(ARTIFACT_ROOT) not in sys.path:
    sys.path.insert(0, str(ARTIFACT_ROOT))

from pipeline.demo_runner import run_demo_pipeline  # noqa: E402


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
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default="configs/example.yaml", help="Accepted for interface compatibility.")
    parser.add_argument("--input", default="data/examples.jsonl")
    parser.add_argument("--output", default="results/demo_outputs.jsonl")
    args = parser.parse_args()

    input_path = resolve_input(args.input)
    output_path = resolve_output(args.output)
    records = run_demo_pipeline(input_path, output_path)
    print(f"wrote {len(records)} records to {output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
