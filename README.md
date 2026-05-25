# Provider Preference Control

This repository contains the code and artifact materials for **COPILOT**, a
provider preference control method for generated code and text. The method
follows a three-stage pipeline: task planning, diffusion draft generation, and
final response completion.

## TL;DR

Provider preference control asks a model to satisfy a user request while using
the provider choices specified for the relevant task scenarios. This release is
organized to support five common checks:

1. inspect sanitized data examples and preference configurations;
2. run a no-model mock path to check installation and JSONL schemas;
3. run the real COPILOT pipeline with local checkpoints or configured API
   endpoints;
4. run prompt baselines on the same JSONL format;
5. evaluate generated outputs with keyword-based preference metrics.

## Structure

```
.
  README.md
  requirements.txt
  dataset/               Sanitized benchmark splits, examples, and schema.
  pipeline/              COPILOT implementation, mock path, and evaluation utilities.
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
under paths you control and update `configs/real_pipeline.template.yaml` or pass
model paths on the command line before running real generation. API credentials,
when used, should be supplied through a local environment variable such as
`PROVIDER_KEY`; no credential value is included in this repository.

## Quick Start

Run the no-model mock path on a small sanitized example file:

```bash
python scripts/run_pipeline.py \
  --mode mock \
  --config configs/example.yaml \
  --input dataset/examples.jsonl \
  --output outputs/demo_outputs.jsonl
```

The mock path is only an installation and schema check. It validates that the
JSONL reader, task-plan schema, anchor formatting, output schema, and evaluator
entry points work in a no-model environment. It does not load LLaDA, does not
call a planner LLM, and does not reproduce the paper method.

## Running COPILOT with Your Models

To run the actual COPILOT method, provide two model roles:

- DLM draft model: a local LLaDA-style checkpoint used for constrained draft
  generation. Specify it with `--dlm-model` or `models.dlm.model_path`.
- Target LLM: the model that performs final response completion. Specify it
  with `--target-llm` or `models.target.model_path`.

By default, the task planner reuses the target LLM. This is the common setup
for running COPILOT as a baseline. If you want a separate planner model, pass
`--planner-model` or set `models.planner.model_path`.

Run the real COPILOT pipeline after filling in local model paths:

```bash
python scripts/run_pipeline.py \
  --mode real \
  --config configs/real_pipeline.template.yaml \
  --input dataset/code/multi_task_3.jsonl \
  --output outputs/copilot_code_m3.jsonl \
  --domain code \
  --dlm-model /path/to/LLaDA-1.5 \
  --target-llm /path/to/target-llm
```

Optional separate planner:

```bash
python scripts/run_pipeline.py \
  --mode real \
  --config configs/real_pipeline.template.yaml \
  --input dataset/code/multi_task_3.jsonl \
  --output outputs/copilot_code_m3.jsonl \
  --domain code \
  --planner-model /path/to/planner-llm \
  --dlm-model /path/to/LLaDA-1.5 \
  --target-llm /path/to/target-llm
```

Run prompt baselines:

```bash
python scripts/run_baselines.py \
  --config configs/baseline.template.yaml \
  --input dataset/code/multi_task_3.jsonl \
  --output outputs/baseline_code_m3.jsonl \
  --methods zero_shot,grouped,step_wise,constrained \
  --generator-kind local \
  --model /path/to/target-llm
```

The constrained baseline is a lightweight lexical preference-token boost for
local decoding. It is inspired by constrained decoding, but it is not a full
NeuroLogic beam-search reproduction. API-only targets can run the prompt
baselines; constrained decoding is skipped unless local token-level generation
is available.

Evaluate generated outputs:

```bash
python scripts/evaluate_outputs.py \
  --input outputs/copilot_code_m3.jsonl \
  --domain code \
  --config configs/eval.yaml \
  --output outputs/copilot_code_m3_metrics.json
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

This public package includes the runnable COPILOT pipeline under `pipeline/`:

- `task_planning.py`: preference-config-bounded task-plan parser, mock planner,
  and model-backed planner adapter;
- `dlm_draft.py`: local LLaDA-style constrained masked-denoising draft wrapper;
- `anchors.py`: code and text anchor construction templates;
- `completion.py`: final-completion prompt builders and deterministic mock completion;
- `model_adapters.py`: HuggingFace local generation and key-free API adapter;
- `runner.py`: real COPILOT runner over JSONL inputs;
- `evaluation.py`: offline keyword metrics for generated records;
- `demo_runner.py`: no-model mock flow used by smoke tests.

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
