#!/usr/bin/env python3
"""Import and lightly exercise public pipeline modules."""

from __future__ import annotations

import tempfile
import sys
from pathlib import Path


ARTIFACT_ROOT = Path(__file__).resolve().parents[1]
if str(ARTIFACT_ROOT) not in sys.path:
    sys.path.insert(0, str(ARTIFACT_ROOT))


def main() -> int:
    from pipeline import (  # noqa: WPS433
        build_code_anchor_lines,
        build_completion_prompt,
        evaluate_records,
        mock_complete,
        parse_task_plan,
        plan_from_preference_config,
        run_demo_pipeline,
    )

    ok, tasks, message = parse_task_plan(
        '[{"task_category": "Object Storage", "task_prompt": "store images"}]',
        ["Object Storage"],
    )
    assert ok, message
    assert tasks[0]["task_category"] == "Object Storage"

    anchors = build_code_anchor_lines("Object Storage", "Amazon S3")
    assert any("boto3.client('s3')" in line for line in anchors)

    preference_config = {"Object Storage": "Amazon S3"}
    planned = plan_from_preference_config("Write a Python script to store images.", preference_config)
    completion_prompt = build_completion_prompt("Write a Python script.", planned, "# draft")
    final = mock_complete("Write a Python script.", planned, "# draft")
    assert "Amazon S3" in completion_prompt
    assert "boto3" in final

    metrics = evaluate_records(
        [
            {
                "scenario": ["Object Storage"],
                "preference_config": preference_config,
                "responses": {"final_response": [final]},
            }
        ],
        scene_keywords={"Object Storage": {"AWS": ["boto3", "s3_client"]}},
        provider_to_service={"Object Storage": {"AWS": "Amazon S3"}},
    )
    assert metrics["n_records"] == 1

    with tempfile.TemporaryDirectory() as tmpdir:
        output_path = str(Path(tmpdir) / "demo_outputs.jsonl")
        records = run_demo_pipeline(str(ARTIFACT_ROOT / "dataset" / "examples.jsonl"), output_path)
        assert records
        assert Path(output_path).exists()

    print("pipeline-imports-ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
