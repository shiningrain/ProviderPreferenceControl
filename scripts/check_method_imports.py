#!/usr/bin/env python3
"""Import and lightly exercise sanitized method modules."""

from __future__ import annotations

import sys
from pathlib import Path


ARTIFACT_ROOT = Path(__file__).resolve().parents[1]
if str(ARTIFACT_ROOT) not in sys.path:
    sys.path.insert(0, str(ARTIFACT_ROOT))


def main() -> int:
    from method import (  # noqa: WPS433
        CompletionRequest,
        MethodConfig,
        TaskPlanner,
        build_code_anchor_lines,
        build_completion_prompt,
        parse_task_plan,
        prepare_constrained_draft_inputs,
        run_preference_control,
    )

    ok, tasks, message = parse_task_plan(
        '[{"task_category": "Object Storage", "task_prompt": "store images"}]',
        ["Object Storage"],
    )
    assert ok, message
    assert tasks[0]["task_category"] == "Object Storage"

    anchors = build_code_anchor_lines("Amazon S3", "Object Storage")
    assert any("boto3.client('s3')" in line for line in anchors)

    draft_request = prepare_constrained_draft_inputs(
        "Store images.",
        [{"task_category": "Object Storage", "task_prompt": "store images", "task_preference": "Amazon S3"}],
    )
    assert draft_request.prompts
    assert draft_request.constraints

    completion_prompt = build_completion_prompt(
        CompletionRequest(
            user_prompt="Write a Python script to store images.",
            task_list=[{"task_category": "Object Storage", "task_prompt": "store images", "task_preference": "Amazon S3"}],
            draft="# draft",
        )
    )
    assert "Amazon S3" in completion_prompt

    result = run_preference_control(
        row={"prompt": "Write a Python script to store images.", "scenarios": ["Object Storage"]},
        preference_config={"Object Storage": "Amazon S3"},
        config=MethodConfig(disable_task_planning=True, disable_dlm_draft=True),
    )
    assert result["status"] == "success"
    assert TaskPlanner
    print("method-imports-ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
