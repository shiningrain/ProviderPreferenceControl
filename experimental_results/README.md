# Experimental Results

This directory follows an RQ-style layout for table-ready summaries.

- `RQ1/`: main method comparison across domains and model families.
- `RQ2/`: module ablations and prompt or planning variants.
- `RQ3/`: sensitivity, transfer, or robustness analyses.

Current aggregate files:

- `RQ1/main_results.csv`: main comparison table.
- `RQ2/ablation_results.csv`: module ablation table.
- `RQ3/dlm_sensitivity.csv`: DLM sensitivity panel.

Only sanitized aggregate summaries should be placed here. Raw generations, logs,
API accounting files, and private run metadata should stay out of the public
artifact unless they have been explicitly scrubbed.
