# Dataset

This directory contains sanitized benchmark splits and small demo examples for
the public artifact.

Files:

- `manifest.json`: split manifest for the released benchmark files.
- `code/single_task.jsonl`, `code/multi_task_2.jsonl`, and
  `code/multi_task_3.jsonl`: Code-domain benchmark splits.
- `text/single_task.jsonl`, `text/multi_task_2.jsonl`, and
  `text/multi_task_3.jsonl`: Text recommendation benchmark splits.
- `code/subsets/multi_task_3_rq2_100.jsonl`: 100-example Code subset used by
  the module-ablation and sandbox supplements.
- `examples.jsonl`: small JSONL examples for the no-GPU demo pipeline.
- `schema.md`: released data-field documentation.

The released main benchmark splits contain 942 Code prompts and 855 Text
prompts. Each prompt has three preference configurations, and generation
experiments expand these configurations with repeated decoding when needed.

If additional public splits are released, place them here with a short manifest
that records:

- split name;
- number of input prompts;
- number of preference configurations;
- domains covered;
- checksum;
- license or data-use note.

Do not include private raw data or internal annotations.
