# RQ2 Ablation Results

RQ2 studies module-level ablations on a 100-example Code subset. The released
aggregate file is `ablation_results.csv`.

The full method reaches 82.6 PA, 83.5 IA, 19.3 DR, and 6.0 QS. Removing scenario
planning produces the largest degradation, especially in distractor control.
Removing draft generation also reduces preference adherence, while removing
response completion weakens the final-answer stage.

Only aggregate values are released here. No raw model outputs, private run tags,
or judge traces are included.

## Sandbox Dry-Run Supplement

We also include a mocked sandbox dry-run sanity check for the same Code setting.
The harness executes extracted Python code with fake SDK, import, subprocess,
file, and network stubs, and it records provider-related runtime events. This
separates syntactic or mocked executability from provider control at runtime.

The prompt-only baselines can be highly runnable under this mocked harness, but
their runtime traces often activate distractor providers. Zero-shot reaches 92.3
sandbox success while its runtime DR is 53.3, and constrained reaches 91.0
sandbox success while its runtime DR is 49.7. By contrast, PROOFER-DLM reaches
84.3 sandbox success with 46.3 runtime PA, 62.0 runtime IA, and 18.3 runtime DR.

These results support the main ablation pattern from another angle. Runtime
provider-control evidence favors methods that introduce explicit
provider-bearing structure, while sandbox success alone is not sufficient to
show preference control.
