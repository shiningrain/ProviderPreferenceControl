# Sandbox Dry-Run Code Sanity Check

This supplement checks whether generated Code outputs expose provider choices
through executable structure rather than only through comments or surrounding
prose. We run extracted Python code in an isolated dry-run harness with fake
SDK, import, subprocess, file, and network stubs. The harness drops non-Python
subfiles from generated multi-file snippets, isolates top-level failures, and
then invokes generated functions with dummy arguments so that useful provider
events can still be observed.

This check should be read as mocked structural executability, not as a
live-service correctness benchmark. The main question is whether provider
choices appear in runtime calls without activating unrelated providers.

| Method | N | Sandbox Success | R-PA | R-IA | R-DR |
|---|---:|---:|---:|---:|---:|
| COPILOT-DLM | 300 | 84.3 | 46.3 | 62.0 | 18.3 |
| Plan+Direct | 300 | 76.7 | 21.0 | 41.5 | 12.0 |
| Plan+Template Anchor | 300 | 81.0 | 43.7 | 58.5 | 15.0 |
| zero_shot | 300 | 92.3 | 19.7 | 43.2 | 53.3 |
| grouped | 300 | 84.7 | 18.7 | 40.3 | 41.0 |
| step_wise | 300 | 51.3 | 9.7 | 21.3 | 19.7 |
| constrained | 300 | 91.0 | 19.0 | 42.0 | 49.7 |

The prompt-only baselines often look runnable under the mocked harness, but
their runtime call traces frequently contain distractor providers. For example,
zero-shot and constrained reach 92.3 and 91.0 sandbox success, respectively,
while their runtime distractor rates are 53.3 and 49.7. This indicates that
syntactic executability alone does not imply provider control.

COPILOT-DLM is not the top method on sandbox success alone. Its runtime
provider-control profile is much stronger, however, with 46.3 runtime PA, 62.0
runtime IA, and 18.3 runtime DR. The Plan+Template Anchor variant reaches a
similar runtime margin, which supports the broader conclusion that explicit
provider-bearing structure is important. The DLM draft remains the complete
method instance because it integrates this structure through the planned
drafting interface rather than through a static template alone.

The file `sandbox_runtime_results.csv` contains the aggregate values. The file
`sandbox_event_example.jsonl` contains one sanitized dry-run event trace that
shows the format of import, call, subprocess, and file-write events observed by
the harness.
