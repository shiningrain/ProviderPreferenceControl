# Motivation Cases

This directory contains sanitized qualitative examples used to motivate provider
preference control.

Files:

- `code_case(Motivation).json`: the Code case study used to illustrate how
  prompt-only baselines can activate distractor services in a multi-task code
  request.
- `text_case.json`: the Text case study used to illustrate high preference
  adherence together with high distractor activation under zero-shot prompting.
- `motivation_case_01.md`: a compact example contrasting a preference-leaking
  response with a preference-controlled response.

The JSON files contain one selected generation per method. They are not
repeated-run logs. Each file records the original prompt, the active preference
configuration, the response excerpt used for the case study, and which
preferences are satisfied, missed, or incorrectly activated as distractors.
