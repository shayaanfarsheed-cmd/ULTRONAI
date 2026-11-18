# ULTRON Learning-System Architecture

**Status:** learning-system design; no real training has been authorized or started.

## Objective

Build ULTRON around how it acquires, tests, retains, and improves mathematical capability. The primary engineering focus is the learning lifecycle, not imitating the conversational behavior or inference interface of another model.

This is an independent implementation. It does not reproduce private OpenAI weights, datasets, infrastructure, or proprietary training procedures. Keep existing code; extend it incrementally.

## Existing foundation — preserve it

- `ultron_model.py`: randomly initialized decoder-only Transformer; 4,038,478 trainable parameters, 5 layers, 256 hidden dimensions, 8 heads, 4x feed-forward width, 192-character context, character tokenizer.
- `ultron_data.py`: deterministic local mathematical example generator.
- `ultron_verify.py`: independent verifier for supported generated math examples.
- `ultron_training.py`: supervised prompt/solution training mechanics, resumable batch stream, optimizer loop, completion generation, topic evaluation, and held-out mastery curriculum.
- Tests cover model mechanics, generated-data validity, independent verification, training updates, stream restoration, and curriculum behavior.

These components are the starting foundation, not proof of broad mathematical competence. The current context is 192 characters, below the earlier 1024-token target; tokenizer/context design must be measured and resolved before serious training.

## How ULTRON should learn

### 1. Learn from verified examples (supervised learning)

1. Generate examples internally using deterministic, versioned generators.
2. Verify each answer independently before it enters the training set.
3. Split data by seed and problem identity into train, validation, and frozen test sets.
4. Train the randomly initialized model to predict solution steps and answers.
5. Track loss and exact-answer accuracy separately.
6. Keep test data out of training and curriculum feedback.

The generator and verifier must not share the same implementation logic where that could hide a common error.

### 2. Measure what it knows

Build a repeatable evaluation harness that measures:
- Exact-answer accuracy by topic and difficulty
- Step/solution validity where it can be independently checked
- Invalid-answer and abstention rates
- Train-versus-validation gap
- Performance on held-out generated examples and separately authored challenge sets
- Reproducibility across fixed seeds

Training loss decreasing is not enough to claim learning. Promote a checkpoint only when held-out performance improves without regressions that exceed agreed thresholds.

### 3. Diagnose mistakes

For every failed evaluation example, store a structured record:
- Stable example ID and dataset version
- Topic, difficulty, and failure category
- Model/checkpoint version
- Expected answer and model answer
- Verifier result and concise diagnostic
- Training/evaluation split (never leak held-out test examples into training)

Cluster errors to identify weaknesses such as arithmetic slips, sign errors, fraction simplification, algebra transformations, or misunderstood instructions.

### 4. Build a targeted curriculum

Use the existing `CurriculumController` as the starting point. Extend it so that:
- Topics are introduced in prerequisite order.
- Difficulty rises only after repeated success on validation sets.
- Weak topics receive more newly generated, independently verified practice.
- Repeated examples are tracked to reduce memorization.
- Advancement requires held-out mastery, not just training-set accuracy.
- A regression in an earlier topic can pause advancement and trigger review.

Do not let the model grade itself. The independent verifier and frozen evaluation harness decide whether a skill has improved.

### 5. Improve through controlled feedback

After a training/evaluation cycle:
1. Compare topic metrics with the previous approved checkpoint.
2. Identify the largest statistically meaningful weaknesses.
3. Generate new targeted examples with fresh seeds.
4. Verify and deduplicate those examples.
5. Add them to a new versioned training set.
6. Train a candidate checkpoint.
7. Evaluate on validation and untouched test sets.
8. Promote only if the candidate meets the acceptance criteria; otherwise roll back.

This is a data-centric feedback loop first. It is more appropriate for ULTRON's small parameter budget and $0 compute constraint than immediately attempting large-scale reinforcement learning.

### 6. Later: verifier-rewarded learning experiments

Only after a reliable supervised baseline exists, investigate reinforcement-learning-style optimization:
- Define a reward from independent correctness, valid steps, and task constraints.
- Test the reward against deliberately wrong, malformed, and reward-hacking outputs.
- Use a frozen evaluation set and compare against the supervised baseline.
- Bound candidate count, compute, and training duration.
- Keep optimizer state and rollback checkpoints.
- Abandon the experiment if it does not improve held-out performance.

Do not assume a modern model's RL recipe is suitable or affordable for a 3–5M parameter model. RL is a later experiment, not a prerequisite.

### 7. Retain learning safely

Keep separate, versioned records for:
- Model weights and optimizer/scheduler state
- Dataset manifests, generator version, seeds, and splits
- Evaluation reports and checkpoint promotion decisions
- Error examples and targeted curriculum sets
- Training run metadata and integrity-checked checkpoints

Checkpoint writes must be atomic and validated. Resuming must restore model, optimizer, scheduler, random number generators, data-stream position, curriculum state, and dataset identity. Never mix incompatible dataset or model versions silently.

## Efficiency and scope

- $0 budget; no paid APIs or external inference services.
- No pretrained weights, external models, or externally generated training data.
- Keep the first model in the 3–5 million parameter range.
- Profile tokenizer/context and memory choices before changing architecture.
- Use small, measured batches and bounded evaluation/training steps.
- Do not claim the dashboard RAM preference is an enforced hard memory cap.
- Do not assume free hosted runtimes are continuous or persistent.
- Avoid premature multi-agent orchestration and expensive inference loops; prioritize the learning signal and evaluation quality.

## Product and security boundaries

- No extra moderation/filter pipeline in the initial math-learning prototype, as requested.
- Essential engineering protections remain: input validation, resource bounds, dependency hygiene, independent data verification, and checkpoint integrity.
- Training controls remain local to the device/process running training.
- No device pairing, remote commands, remote start/stop, public HTTP control listener, or dashboard training writes.
- The dashboard remains read-only for training operations.
- Actual training remains disabled until the frontend and local runtime gates are complete and the user separately approves starting training.

## Implementation sequence

1. Preserve existing model, data generator, verifier, trainer, and curriculum code.
2. Build dataset manifests, versioning, deterministic split enforcement, and deduplication.
3. Build the evaluation harness with frozen held-out tests and topic/difficulty metrics.
4. Build structured error logging and failure clustering.
5. Extend curriculum generation using validation weaknesses without test leakage.
6. Add candidate-checkpoint comparison, promotion, and rollback.
7. Validate full checkpoint/resume determinism, including optimizer, RNG, stream, and curriculum state.
8. Only after frontend/runtime gates and explicit approval, run a small supervised baseline.
9. Consider reward-based optimization only if measured evidence justifies it.

## Completion criteria

ULTRON's learning system is successful only when repeated controlled cycles produce measurable improvement on unseen mathematics problems, with reproducible evaluations, verified data, safe checkpoint recovery, and no test-set leakage. Report exact metrics and limitations; never infer learning from loss alone.
