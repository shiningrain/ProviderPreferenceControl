# RQ2 Ablation Results

RQ2 studies module-level ablations on a 100-example Code subset. The released
aggregate file is `ablation_results.csv`.

The full method reaches 82.6 PA, 83.5 IA, 19.3 DR, and 6.0 QS. Removing scenario
planning produces the largest degradation, especially in distractor control.
Removing draft generation also reduces preference adherence, while removing
response completion weakens the final-answer stage.

Only aggregate values are released here. No raw model outputs, private run tags,
or judge traces are included.
