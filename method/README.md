# Method

This directory contains a sanitized public method-code snapshot. It is closer to
the paper implementation than the no-GPU demo in `../pipeline/`, but it still
keeps model calls behind clean interfaces.

Current modules:

- `task_planning.py`: preference-config-bounded planning prompt, parser,
  category sanitizer, preference attachment, and a deterministic surface-split
  fallback for ablations.
- `anchor_templates.py`: sanitized code-anchor and text-anchor templates based
  on the project anchor-skeleton and hybrid text-scaffold logic.
- `dlm_draft_interface.py`: public boundary for constrained diffusion drafts,
  including prompt and fixed-span preparation. It does not load model weights.
- `completion_interface.py`: completion prompt builder, output-format rules, and
  repair-condition checks.
- `pipeline_flow.py`: end-to-end method wiring with plug-in planner, draft, and
  completion model protocols.
- `__init__.py`: public imports.

The release copy exposes a small public API, for example:

```python
from method import MethodConfig, run_preference_control

result = run_preference_control(
    row={"prompt": "Write a Python script to store images.", "scenarios": ["Object Storage"]},
    preference_config={"Object Storage": "Amazon S3"},
    config=MethodConfig(disable_task_planning=True, disable_dlm_draft=True),
)
```

What was intentionally removed or abstracted:

- local model paths and checkpoint loading;
- GPU placement and scheduler behavior;
- raw-output resume logic and private run tags;
- API wrappers, proxy endpoints, keys, and cost accounting;
- LLM-as-judge code;
- raw experiment outputs and logs.

Run the method import check from the release root:

```bash
python scripts/check_method_imports.py
```

Do not copy private launch scripts, local absolute paths, API credentials, cache
files, or temporary experiment code into this directory.
