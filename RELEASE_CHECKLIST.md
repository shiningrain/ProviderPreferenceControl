# Release Checklist

This checklist tracks what remains before the artifact can be made public.

## Already Started

- Root README follows an InvisibleHand-style presentation with TL;DR, structure,
  setup, pipeline, results, and citation placeholders.
- Sanitized sample data and schema notes live under `data/`.
- Configuration templates use placeholders only.
- Compatibility folders exist for `dataset/`, `pipeline/`,
  `motivation_cases/`, and `experimental_results/`.

## Must Sanitize Before Release

- Copy only cleaned method code into `method/` or `pipeline/`; never move files
  out of the working repository when assembling the artifact.
- Remove local absolute paths, private usernames, server names, GPU identifiers,
  cache paths, and temporary run tags from all copied files.
- Remove all API keys, proxy URLs, account identifiers, and private endpoints.
- Do not copy any judge or API helper that contains credentials.
- Do not copy raw internal logs or unsanitized JSONL generations.
- Confirm all text is ASCII-only.
- Confirm examples contain no private prompts, identities, or unpublished
  annotations that could identify the source environment.

## Candidate Files To Review Manually

- Task planning module.
- Core pipeline wrapper.
- Diffusion draft generator.
- Anchor construction helpers.
- Offline evaluation scripts.
- Table summarization scripts.

Each candidate file should be copied only after a line-by-line scrub.

## Pre-Release Checks

```bash
find . -type f -print | sort
grep -RInE "api[_-]?key|token|proxy|secret|credential|http://|https://" .
python scripts/check_ascii.py .
python scripts/check_method_imports.py
python scripts/check_no_symlinks.py .
python scripts/validate_jsonl.py data/examples.jsonl
python scripts/smoke_test.py
```

The commands above are available in this release skeleton and should be run from
the artifact root before packaging.
