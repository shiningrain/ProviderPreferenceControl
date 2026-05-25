# Scripts

This directory contains release-quality scripts.

Expected entry points:

- `run_pipeline.py`: run COPILOT in `mock` or `real` mode on a JSONL input file.
- `run_baselines.py`: run zero-shot, grouped, step-wise, and constrained
  baselines on the same JSONL format.
- `evaluate_outputs.py`: compute preference adherence summaries.
- `baseline_utils.py`: build zero-shot, grouped, step-wise, and lightweight
  constrained baseline prompts, plus lexical preference-token boost helpers.
- `check_ascii.py`: verify release text and code are ASCII-only.
- `check_pipeline_imports.py`: import and lightly exercise public pipeline modules.
- `check_no_symlinks.py`: verify the release tree contains no symbolic links.
- `validate_jsonl.py`: verify that released JSONL files parse cleanly.
- `smoke_test.py`: run a local no-network smoke test.

Scripts should accept relative paths or config files. They should not contain hard coded local paths, API keys, user names, private proxy URLs, or server specific GPU IDs.

Smoke-test commands from the release root:

```bash
python scripts/check_ascii.py .
python scripts/check_pipeline_imports.py
python scripts/check_no_symlinks.py .
python scripts/validate_jsonl.py dataset/examples.jsonl
python scripts/smoke_test.py
```

Real pipeline example:

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

Baseline example:

```bash
python scripts/run_baselines.py \
  --input dataset/code/multi_task_3.jsonl \
  --output outputs/baseline_code_m3.jsonl \
  --methods zero_shot,grouped,step_wise,constrained \
  --generator-kind local \
  --model /path/to/target-llm
```
