# Pipeline

This directory contains the public COPILOT implementation plus the no-model
mock path used for installation checks.

The release pipeline should be organized around these stages:

1. task planning: split the request into sub-tasks and match relevant scenarios;
2. draft generation: create a constrained diffusion draft with service anchors;
3. completion: produce the final response while preserving selected services;
4. evaluation: compute full-text and code-only preference metrics.

Current public modules:

- `task_planning.py`: parser and sanitizer for model-produced task plans,
  deterministic mock planner, and model-backed planner adapter.
- `dlm_draft.py`: local LLaDA-style constrained masked-denoising draft wrapper.
- `anchors.py`: code and text anchor builders that preserve matched services in
  drafts.
- `completion.py`: target-LLM completion prompt builders and a no-model mock
  completion path.
- `model_adapters.py`: local HuggingFace and OpenAI-compatible API adapters.
- `runner.py`: real COPILOT runner over JSONL records.
- `evaluation.py`: offline main-vs-distractor metrics over generated JSONL
  records.
- `demo_runner.py`: end-to-end no-GPU demo over `dataset/examples.jsonl`.

Run from the release root:

```bash
python scripts/run_pipeline.py \
  --mode mock \
  --input dataset/examples.jsonl \
  --output outputs/demo_outputs.jsonl
python scripts/evaluate_outputs.py \
  --input outputs/demo_outputs.jsonl \
  --output outputs/demo_metrics.json
```

Run the real pipeline after filling model paths:

```bash
python scripts/run_pipeline.py \
  --mode real \
  --config configs/real_pipeline.template.yaml \
  --input dataset/code/multi_task_3.jsonl \
  --output outputs/copilot_code_m3.jsonl \
  --domain code \
  --dlm-model /path/to/LLaDA-1.5 \
  --target-llm /path/to/target-llm
```

The mock mode is only a schema and installation check. It validates JSONL
expansion, task-plan shape, anchor formatting, output schema, and evaluator
compatibility without loading any model. The real mode loads the local DLM
checkpoint and the target LLM, reusing the target LLM for planning unless a
separate planner is specified. Keep local launchers, scheduler scripts, private
API wrappers, and raw logs out of the artifact.
