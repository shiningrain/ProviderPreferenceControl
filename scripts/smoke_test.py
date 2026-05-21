#!/usr/bin/env python3
"""Run the artifact demo pipeline and offline evaluator."""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path


def run(cmd, cwd: Path) -> None:
    display_cmd = ["python" if item == sys.executable else item for item in cmd]
    print("+ " + " ".join(display_cmd))
    subprocess.run(cmd, cwd=str(cwd), check=True)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default="configs/example.yaml")
    args = parser.parse_args()

    root = Path(__file__).resolve().parents[1]
    run(
        [
            sys.executable,
            "scripts/run_pipeline.py",
            "--config",
            args.config,
            "--input",
            "data/examples.jsonl",
            "--output",
            "results/demo_outputs.jsonl",
        ],
        cwd=root,
    )
    run(
        [
            sys.executable,
            "scripts/evaluate_outputs.py",
            "--input",
            "results/demo_outputs.jsonl",
            "--output",
            "results/demo_metrics.json",
        ],
        cwd=root,
    )
    run([sys.executable, "scripts/validate_jsonl.py", "results/demo_outputs.jsonl"], cwd=root)
    print("smoke-ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
