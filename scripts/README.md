# Scripts

This directory will contain release-quality scripts.

Expected entry points:

- `run_pipeline.py`: run the full method on a JSONL input file.
- `evaluate_outputs.py`: compute preference adherence summaries.
- `check_ascii.py`: verify release text and code are ASCII-only.
- `check_pipeline_imports.py`: import and lightly exercise public pipeline modules.
- `check_no_symlinks.py`: verify the release tree contains no symbolic links.
- `validate_jsonl.py`: verify that released JSONL files parse cleanly.
- `smoke_test.py`: run a local no-network smoke test.

Planned later entry points:

- `run_baselines.py`: run prompt-only comparison methods.
- `summarize_results.py`: build compact table-ready summaries.
- `reproduce_tables.sh`: reproduce released table artifacts.

Scripts should accept relative paths or config files. They should not contain hard coded local paths, API keys, user names, private proxy URLs, or server specific GPU IDs.

Smoke-test commands from the release root:

```bash
python scripts/check_ascii.py .
python scripts/check_pipeline_imports.py
python scripts/check_no_symlinks.py .
python scripts/validate_jsonl.py dataset/examples.jsonl
python scripts/smoke_test.py
```
