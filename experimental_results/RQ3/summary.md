# RQ3 Sensitivity Results

This folder currently releases an aggregate DLM sensitivity panel rather than a
new headline reproduction result. The file `dlm_sensitivity.csv` reports point
estimates for anchor gap, generated-region length, and denoising-step settings
on Code and Text subsets.

The main Code operating point is gap 8, length 128, and 64 denoising steps. The
main Text operating point is gap 6, length 192, and 96 denoising steps. The
panel shows nearby settings remain viable, but it is diagnostic and should not
be read as an exhaustive tuning sweep.

Expected future additions include sanitized transfer or robustness summaries if
they become part of the public artifact.
