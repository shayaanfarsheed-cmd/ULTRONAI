# ULTRON held-out evaluation

## Purpose

This stage establishes a reproducible baseline for the randomly initialized ULTRON model before any training is allowed.

## Fixed evaluation set

- File: `ultron_evaluation.py`.
- 28 hand-authored mathematics questions across all 14 supported topics.
- Each topic has a difficulty-1 and difficulty-3 question.
- Questions use wording distinct from the synthetic generator's emitted templates.
- Expected answers are fixed in source control; they are not generated at evaluation time.
- The evaluation set has a stable SHA-256 fingerprint so reports can identify the exact test version.
- Every record is marked `evaluation_only=True` and `split="held_out"`.

This is a small initial smoke benchmark, not a statistically strong estimate of broad mathematical ability. It should be expanded with independently authored questions and more examples per topic before making strong claims.

## Metrics

The evaluator reports:
- exact-answer overall accuracy;
- macro-average topic accuracy;
- per-topic accuracy and sample counts;
- per-difficulty accuracy and sample counts;
- answer parse failures;
- expected and generated answers for each question;
- model parameter count and evaluation-set fingerprint.

No fuzzy matching is used. A prediction is correct only when the parsed `Answer:` line exactly matches the expected answer after trimming whitespace.

## Leakage protection

- Evaluation examples are not imported by the data generator or curriculum.
- The training dataset wrapper rejects records marked as held-out/evaluation-only.
- Tests assert that evaluation does not alter model weights, use an optimizer, or change the model's original train/eval mode.
- Do not use final held-out scores to repeatedly tune hyperparameters. Use validation data for iteration and reserve a final untouched test set for a final comparison.
- Future training-data import paths must preserve the evaluation-only marker and must not strip it before training.

The generated train/validation/test data splits remain useful for development, but they are not a substitute for this separately authored evaluation set.

## Run

Install the project's pinned/runtime dependencies, then run:

```bash
python evaluate.py --device cpu
```

For a quick diagnostic subset:

```bash
python evaluate.py --device cpu --limit 4 --max-new-tokens 16
```

The CLI initializes a fresh model from random weights using a fixed seed. It does not load a checkpoint, invoke a trainer, or change model weights. It prints a JSON report. The full 4-million-parameter CPU run may be slow; use a free supported compute runtime if available, without enabling training.

## Interpretation

The initial model is randomly initialized. Its baseline accuracy is expected to be low and does not indicate a broken training system. It establishes the starting point against which a future, explicitly approved training run can be compared.

A successful evaluation run means only that the benchmark executed and produced metrics. It does not prove that ULTRON has learned mathematics.
