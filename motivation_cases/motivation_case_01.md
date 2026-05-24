# Motivation Case 01

## User Request

Write a Python script that accepts uploaded images, stores them, and sends a
notification when processing completes.

## Preference Configuration

```json
{
  "Object Storage": "Amazon S3",
  "Notification": "Amazon SNS"
}
```

## Expected Behavior

The output should use the requested provider services for the relevant
scenarios. It should not switch to unrelated providers for storage or
notification unless the user explicitly asks for that behavior.

## Release Note

This is a synthetic sanitized case for package structure and smoke tests. Replace
or supplement it with paper case studies only after review.
