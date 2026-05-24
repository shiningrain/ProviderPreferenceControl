# RQ2 Results

This folder contains table-ready aggregate ablation results and a mocked
runtime sanity check for Code outputs.

Files:

- `ablation_results.csv`: module ablation table.
- `../../dataset/code/subsets/multi_task_3_rq2_100.jsonl`: released 100-example
  Code subset used by the ablation supplement.
- `sandbox_runtime_results.csv`: sandbox dry-run aggregate table.
- `sandbox_runtime_summary.json`: compact metadata and headline sandbox values.
- `sandbox_runtime.md`: paper-facing interpretation of the sandbox check.
- `sandbox_event_example.jsonl`: one sanitized dry-run event trace.
- `summary.json`: compact metadata and headline values.
- `summary.md`: paper-facing interpretation.

Each summary should state which module was changed and which evaluation split
was used. The sandbox check uses fake SDK, import, subprocess, file, and network
stubs, so it should be interpreted as structural runtime evidence rather than
as live cloud-service execution.
