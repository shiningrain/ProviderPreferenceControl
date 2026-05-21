# Public Release Audit

This audit records the current public-artifact status.

## Structure Alignment

The artifact follows an InvisibleHand-style layout:

- `README.md`: TL;DR, structure, setup, pipeline, dataset, results, and citation.
- `requirements.txt`: minimal public dependencies.
- `figures/`: paper figures and result-table screenshots used by `README.md`.
- `dataset/`: compatibility alias for released datasets.
- `pipeline/`: no-GPU runnable demo skeleton.
- `motivation_cases/`: compatibility alias for sanitized cases.
- `experimental_results/`: RQ-style aggregate result folders.

Additional project-specific folders are retained:

- `data/`: tiny sanitized examples and schema documentation.
- `method/`: sanitized method-code interfaces closer to the paper pipeline.
- `configs/`: placeholder-only public configs.
- `scripts/`: release checks, demo runner, and offline evaluator.
- `results/`: demo outputs and metrics produced by the no-GPU smoke test.

## Anonymization Status

Current files are ASCII-only and contain no raw logs, raw generations from
experiments, private endpoints, API keys, proxy URLs, local absolute paths, or
machine-specific execution settings.

The aggregate result files contain table-level numbers only:

- `experimental_results/RQ1/main_results.csv`
- `experimental_results/RQ2/ablation_results.csv`
- `experimental_results/RQ3/dlm_sensitivity.csv`

## Deliberately Excluded

- raw model outputs;
- LLM-as-judge internals;
- API wrappers and cost accounting;
- scheduler, tmux, or cluster launch scripts;
- model checkpoints and local model paths;
- private run tags and logs.

## Remaining Work

- Add license text after the review policy is fixed.
- Add sanitized full dataset splits if they are approved for release.
- Replace tiny keyword templates with a sanitized full evaluator resource.
- Add fuller model adapters only after removing private paths and endpoints.
