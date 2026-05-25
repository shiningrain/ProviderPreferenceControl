# Provider Preference Control

This repository contains the code and artifact materials for **COPILOT**, a
provider preference control method for generated code and text. The method
follows a three-stage pipeline: task planning, diffusion draft generation, and
final response completion.

## TL;DR

Provider preference control asks a model to satisfy a user request while using
the provider choices specified for the relevant task scenarios. The artifact is
organized to support four common checks:

1. inspect sanitized data examples and preference configurations;
2. run the method on a small example file;
3. evaluate generated outputs with keyword-based preference metrics;
4. reproduce table-ready result summaries after the release files are filled in.

## Structure

```
.
  README.md
  requirements.txt
  dataset/               Sanitized benchmark splits, examples, and schema.
  pipeline/              No-GPU runnable demo skeleton and evaluation utilities.
  experimental_results/  RQ1/RQ2/RQ3 aggregate result folders.
  motivation_cases/      Sanitized motivation and case-study materials.
  figures/               Paper figures and result-table screenshots for README display.
  configs/               Local-path-free configuration templates.
  scripts/               Reproduction and evaluation entry points.
```

## Motivation

Users and organizations often have provider preferences, such as using a
specific cloud provider, storage service, or travel platform. A standard LLM may
either ignore the relevant preference or apply unrelated preferences from the
same configuration to tasks that did not ask for them. The motivation example
below illustrates this failure mode and the preference-aware response produced
by COPILOT.
The fine-grained \textbf{provider preference} is behind many real-world requests, where users favor specific brands for online services and developers form path dependencies on particular languages, frameworks, and cloud platforms shaped by existing technology stacks, organizational norms, and cost considerations.
Unlike stable stylistic preferences, such provider preferences span multiple scenarios and candidate providers that evolve over time.
However, existing preference control methods have limitations when applied to the provider preference.
(i) Prompt-based methods may confound the preferences on different providers across different scenarios, leading to unstable and unreliable preference control (see the following figure).
(ii) Finetuning- and steer-based methods rely on heavy training and manually-constructed datasets, and are impractical for the dynamic and evolving provider preferences.

To fill this gap, we propose COPILOT, a training-free framework that leverages the collaboration of diffusion language model (DLM) and LLM to satisfy users' diverse and dynamic provider preferences.

<p align="center">
  <img src="figures/motivation.png" width="760" alt="Motivation example">
</p>

## Setup

Create a Python environment and install the required packages:

```bash
conda create -n artifact python=3.9
conda activate artifact
pip install -r requirements.txt
```

Large model checkpoints are not included. Put local or downloaded checkpoints
under paths you control and update `configs/model_paths.template.yaml` before
running generation.

## Quick Start

Run the main pipeline on a small sanitized example file:

```bash
python scripts/run_pipeline.py \
  --config configs/example.yaml \
  --input dataset/examples.jsonl \
  --output outputs/demo_outputs.jsonl
```

Evaluate generated outputs:

```bash
python scripts/evaluate_outputs.py \
  --input outputs/demo_outputs.jsonl \
  --config configs/eval.yaml \
  --output outputs/demo_metrics.json
```

Run the full no-GPU smoke test:

```bash
python scripts/smoke_test.py
```

## Pipeline and Dataset

The pipeline first decomposes an input request into sub-tasks and matches each
applicable sub-task to a provider preference. A diffusion language model then
produces a constrained draft with fixed service anchors. A completion model
turns the draft into the final answer while preserving the selected provider
choices.

<p align="center">
  <img src="figures/overview.png" width="900" alt="COPILOT pipeline overview">
</p>

This public package includes a no-GPU mock implementation under `pipeline/`.
It mirrors the release interfaces without loading model checkpoints:

- `task_planning.py`: preference-config-bounded task-plan parser and mock planner;
- `anchors.py`: code and text anchor construction templates;
- `completion.py`: completion prompt builder and deterministic mock completion;
- `evaluation.py`: offline keyword metrics for generated records;
- `demo_runner.py`: JSONL input expansion and end-to-end demo flow.

Input records use JSON Lines. Each row contains a natural-language `prompt`, a
list of main `scenarios`, and one or more `preference_config` objects mapping
scenario names to provider-specific services. See `dataset/schema.md`,
`dataset/manifest.json`, and the released Code/Text splits under `dataset/`.
The small `dataset/examples.jsonl` file is only for the no-GPU demo pipeline.

Generated records should include identifiers, the active preference
configuration, optional task-planning metadata, and the final response text.
Evaluation scripts should be able to read either `responses.final_response` or
`responses.llm.responses`.

## Analysis Results

The current release includes table-ready aggregate summaries:

- `experimental_results/RQ1/main_results.csv`: main comparison across Code and NLP;
- `experimental_results/RQ2/ablation_results.csv`: module ablations;
- `experimental_results/RQ2/sandbox_runtime_results.csv`: mocked runtime
  provider-control sanity check for Code outputs;
- `experimental_results/RQ3/dlm_sensitivity.csv`: DLM sensitivity panel.

Main comparison:

<p align="center">
  <img src="figures/table1.png" width="900" alt="Main comparison table">
</p>

Module ablation:

<p align="center">
  <img src="figures/table2.png" width="650" alt="Module ablation table">
</p>

Raw generations are omitted from this compact release. The included CSV, JSON,
and Markdown summaries are intended to make the reported aggregate results easy
to inspect without requiring access to private infrastructure. For the sandbox
supplement, we include only aggregate metrics and one sanitized event-trace
example rather than the full dry-run logs.
