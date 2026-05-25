# Configs

This directory contains example configuration files with placeholders only.

Current contents:

- `example.yaml`: small pipeline configuration for `dataset/examples.jsonl`.
- `real_pipeline.template.yaml`: real COPILOT config with planner, DLM, target
  LLM, and resource fields.
- `baseline.template.yaml`: prompt-baseline config for zero-shot, grouped,
  step-wise, and constrained baselines.
- `eval.yaml`: keyword-metric evaluation configuration.
- `model_paths.template.yaml`: local checkpoint placeholders.
- `service_keywords.template.json`: tiny keyword map for the public examples.
- `provider_to_service.template.json`: tiny provider-to-service map for the public examples.
- `service_keywords_code.json` and `provider_to_service_code.json`: released
  Code-domain keyword and provider-service mappings.
- `service_keywords_text.json` and `provider_to_service_text.json`: released
  Text-domain keyword and provider-service mappings.

Configuration files use placeholders for model paths and credentials. They are
runnable after the user fills in local paths or local environment variables.
The tiny keyword templates cover only `dataset/examples.jsonl`; use the Code or
Text resource files for released benchmark splits.
