# ULTRON self-learning architecture

## Objective

Build a from-scratch mathematics system that improves through measurable, verified experience. The learning loop must optimize for correctness and retained capability, not raw generated-example volume.

## Core mechanisms

### 1. Verifiable environment feedback

- Every generated exercise has a topic, difficulty, seed, expected answer and verification result.
- Use an independent verifier where possible; do not treat the generator or model's confidence as proof.
- Record pass/fail outcomes, error categories and evaluation metrics.
- Keep verifier failures and ambiguous examples out of the training set.
- Add property-based and adversarial edge cases for supported topics.

### 2. Curated synthetic data

- Generate targeted examples for underperforming topics and boundary cases.
- Deduplicate semantically or structurally similar questions; do not reward volume or repetition.
- Track provenance: generator version, seed, topic, difficulty, verifier version and verification result.
- Maintain a fixed held-out evaluation set that is never used for training or curriculum selection.
- Synthetic examples are useful practice, not independent evidence of broad mathematical competence.

### 3. Targeted model updates

- First establish a reproducible baseline for the randomly initialized model.
- Compare candidate training runs against that baseline and retain only validated improvements.
- Use bounded updates, checkpoints and rollback.
- Consider parameter-efficient methods such as LoRA only after the base model is trained and the architecture supports adapters. LoRA is not a substitute for establishing the initial from-scratch model.
- Never start a real training run without explicit owner approval.

### 4. Persistent memory and retrieval

Keep external memory separate from model weights so new experience can be stored immediately without changing the model.

Suggested record groups:
- verified knowledge and worked examples;
- episodic experiences and outcomes;
- mistakes, corrections and unresolved questions;
- source/provenance and verifier metadata;
- model checkpoints and evaluation reports.

Retrieval must return relevant evidence and provenance. Memory contents are not automatically trusted as truth; verify them before using them in training or high-confidence answers. Provide owner-controlled deletion for uploaded or stored records.

### 5. Test-time compute and self-verification

For supported questions:
1. Parse the question and identify the applicable topic.
2. Produce one or more candidate solution paths.
3. Check arithmetic and intermediate steps independently.
4. Compare candidate answers and flag disagreement.
5. Revise or abstain when verification fails.
6. Present the answer with a concise explanation and an honest confidence signal.

The verifier must not simply repeat the same computation or trust the model's own critique.

## Guardrails

### Avoid catastrophic forgetting

- Preserve a fixed core regression suite across all previously supported topics.
- Mix representative prior verified examples into training batches when training begins.
- Compare per-topic metrics before and after every candidate update.
- Reject or roll back a checkpoint when important existing capabilities regress beyond defined tolerances.

### Prevent reward hacking and model collapse

- Keep the evaluator and held-out tests isolated from training.
- Use independently implemented checks and adversarial tests.
- Detect repeated templates, duplicates, suspiciously easy examples and answer leakage.
- Do not let the model grade itself or recursively certify its own generated labels.
- Include varied problem structures and independently authored test cases.
- Track diversity, verifier disagreement, and performance on unseen examples.

### Operational safety

- Dry-run generation and verification before enabling training.
- Bound batch sizes, attempts, memory and runtime.
- Make pause/stop and checkpoint recovery explicit.
- Do not execute uploaded files.
- Do not use external AI APIs, pretrained weights or paid services.
- Be transparent about browser/iPad resource limits; never imply that a dashboard slider guarantees a hard device memory cap.

## Delivery stages

1. **Verified data pipeline:** deterministic generation, independent verification, rejection reporting, provenance and split isolation. No training.
2. **Evaluation foundation:** fixed held-out tests, baseline metrics, per-topic/difficulty reporting and regression thresholds.
3. **Memory and retrieval:** persistent, inspectable experience records with provenance, verification and deletion.
4. **Answer-time verification:** candidate solutions, independent checks, revision and abstention.
5. **Controlled training:** only after the owner approves; bounded updates, replay of core skills, checkpointing and rollback.
6. **Autonomous curriculum:** choose practice topics based on measured weaknesses, then evaluate on held-out tests before increasing difficulty.

A stage is complete only when its tests and evidence pass. Generating data or reducing training loss alone does not prove learning.
