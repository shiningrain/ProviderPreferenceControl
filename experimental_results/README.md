# Experimental Results

This directory follows an RQ-style layout for table-ready summaries.

- `RQ1/`: main method comparison across domains and model families.
- `RQ2/`: module ablations and prompt or planning variants.
- `RQ3/`: sensitivity, transfer, or robustness analyses.

Current aggregate files:

- `RQ1/main_results.csv`: main comparison table.
- `RQ2/ablation_results.csv`: module ablation table.
- `RQ2/sandbox_runtime_results.csv`: mocked runtime provider-control sanity check.
- `RQ3/dlm_sensitivity.csv`: DLM sensitivity panel.

This release keeps the directory mostly aggregate-only. Raw generations, full
logs, API accounting files, and private run metadata are intentionally omitted.
The sandbox supplement includes one small sanitized event trace to document the
event schema used by the dry-run harness.
