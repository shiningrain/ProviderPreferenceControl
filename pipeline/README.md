# Pipeline

This directory contains the no-GPU runnable demo skeleton for the public
artifact. For method-code interfaces closer to the paper implementation, see
`../method/`.

The release pipeline should be organized around these stages:

1. task planning: split the request into sub-tasks and match relevant scenarios;
2. draft generation: create a constrained diffusion draft with service anchors;
3. completion: produce the final response while preserving selected services;
4. evaluation: compute full-text and code-only preference metrics.

Current public modules:

- `task_planning.py`: parser and sanitizer for model-produced task plans, plus a
  deterministic preference-config-bounded mock planner.
- `anchors.py`: code anchor and text anchor builders that preserve matched
  services in drafts.
- `completion.py`: target-LLM completion prompt builder and a no-model mock
  completion path.
- `evaluation.py`: offline main-vs-distractor metrics over generated JSONL
  records.
- `demo_runner.py`: end-to-end no-GPU demo over `data/examples.jsonl`.

Run from the release root:

```bash
python scripts/run_pipeline.py \
  --input data/examples.jsonl \
  --output results/demo_outputs.jsonl
python scripts/evaluate_outputs.py \
  --input results/demo_outputs.jsonl \
  --output results/demo_metrics.json
```

The production implementation should still be copied here only after
sanitization. Keep local launchers, scheduler scripts, private API wrappers, and
raw logs out of the artifact.
