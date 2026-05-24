# Data Schema

Input files use JSON Lines. Each line is one user request with one or more
preference configurations.

## Input Fields

- `id`: stable integer or string identifier.
- `prompt`: natural-language user request.
- `scenarios`: list of main task scenarios in the request.
- `preference_config`: list of provider preference maps. Each map assigns a
  scenario name to the required service for that run.

Example:

```json
{
  "id": 1,
  "prompt": "Write a Python script that stores uploaded images and sends a notification when processing completes.",
  "scenarios": ["Object Storage", "Notification"],
  "preference_config": [
    {
      "Object Storage": "Amazon S3",
      "Notification": "Amazon SNS"
    }
  ]
}
```

## Generated Output Fields

Generation scripts should preserve the input identifiers and include:

- `id`
- `preference_config_index`
- `repeat_index`
- `preference_config`
- `scenario` or `scenarios`
- `task_planning`, when available
- `responses`

For baseline methods, the final text is expected at:

```json
{"responses": {"final_response": ["..."]}}
```

For the full method, the final text is expected at:

```json
{"responses": {"llm": {"responses": ["..."]}}}
```

This keeps the evaluation scripts independent of a single generator.
