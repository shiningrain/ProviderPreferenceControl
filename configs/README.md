# Configs

This directory contains example configuration files with placeholders only.

Current contents:

- `example.yaml`: small pipeline configuration for `dataset/examples.jsonl`.
- `eval.yaml`: keyword-metric evaluation configuration.
- `model_paths.template.yaml`: local checkpoint placeholders.
- `service_keywords.template.json`: tiny keyword map for the public examples.
- `provider_to_service.template.json`: tiny provider-to-service map for the public examples.

Configuration files should use placeholders for model paths and API credentials. They should be runnable after the user fills in local paths.
The keyword templates cover only the tiny public examples. Replace them with
sanitized full keyword resources before reproducing paper-scale results.
