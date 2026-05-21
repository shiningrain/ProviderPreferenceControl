# RQ1 Main Results

RQ1 compares COPILOT with prompt-only and constrained-decoding baselines across
Code and NLP settings. The released aggregate file is `main_results.csv`.

Key observations:

- On Code, COPILOT improves preference adherence while keeping distractor use
  low across the evaluated model families.
- On NLP, most methods preserve high instruction adherence, while COPILOT mainly
  reduces distractor activation.
- Closed-source results are released only as aggregate table values; no API
  traces, cost accounting, prompts with private metadata, or raw model outputs
  are included.

Metrics:

- PA: preference adherence percentage; higher is better.
- IA: instruction adherence percentage; higher is better.
- DR: distractor rate percentage; lower is better.
- QS: quality score; higher is better.
