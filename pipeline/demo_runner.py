"""No-GPU demo runner for the public artifact."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Dict, Iterable, List

from .anchors import build_mock_draft
from .completion import build_completion_prompt, mock_complete
from .evaluation import iter_jsonl, write_jsonl
from .task_planning import plan_from_preference_config


def _iter_expanded_inputs(path: str) -> Iterable[Dict[str, Any]]:
    for row in iter_jsonl(path):
        configs = row.get("preference_config") or []
        if isinstance(configs, dict):
            configs = [configs]
        for index, preference_config in enumerate(configs):
            if not isinstance(preference_config, dict):
                continue
            expanded = dict(row)
            expanded["preference_config_index"] = index
            expanded["repeat_index"] = 0
            expanded["preference_config"] = preference_config
            yield expanded


def run_demo_pipeline(input_path: str, output_path: str) -> List[Dict[str, Any]]:
    """Run the mock public pipeline on a JSONL file."""
    records = []
    for row in _iter_expanded_inputs(input_path):
        prompt = str(row.get("prompt") or "")
        preference_config = row["preference_config"]
        tasks = plan_from_preference_config(prompt, preference_config)
        draft = build_mock_draft(tasks)
        completion_prompt = build_completion_prompt(prompt, tasks, draft)
        final_response = mock_complete(prompt, tasks, draft)
        records.append(
            {
                "id": row.get("id"),
                "preference_config_index": row.get("preference_config_index", 0),
                "repeat_index": row.get("repeat_index", 0),
                "prompt": prompt,
                "scenario": row.get("scenarios", row.get("scenario", [])),
                "preference_config": preference_config,
                "task_planning": {
                    "planner": "mock_preference_config_bounded",
                    "taskList": tasks,
                },
                "responses": {
                    "generate_type": "mock_dlm_llm",
                    "draft": draft,
                    "completion_prompt": completion_prompt,
                    "final_response": [final_response],
                },
            }
        )
    write_jsonl(output_path, records)
    return records


def main() -> int:
    parser = argparse.ArgumentParser(description="Run the no-GPU artifact demo pipeline.")
    parser.add_argument("--input", default="dataset/examples.jsonl")
    parser.add_argument("--output", default="outputs/demo_outputs.jsonl")
    args = parser.parse_args()

    records = run_demo_pipeline(args.input, args.output)
    print(f"wrote {len(records)} records to {Path(args.output)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
