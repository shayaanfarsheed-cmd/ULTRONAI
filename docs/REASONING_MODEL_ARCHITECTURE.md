# ULTRON Reasoning-Model Architecture

**Status:** architecture and implementation roadmap; no real training has been authorized or started.

## Objective

Build an independent, mathematics-focused model using the same broad engineering ideas found in modern reasoning systems: a learned language model, explicit test-time problem solving, specialist task execution, independent verification, and feedback-driven improvement.

This is an independent implementation. It does not reproduce private OpenAI weights, datasets, infrastructure, or proprietary training procedures.

## Existing implementation (verified in the main branch)

- `ultron_model.py`: randomly initialized decoder-only Transformer; current defaults are 5 layers, 256 hidden dimensions, 8 attention heads, 4x feed-forward width, 192-character context, and a character tokenizer.
- Current parameter count: **4,038,478 trainable parameters**, inside the 3–5 million target.
- `ultron_data.py`: deterministic, locally generated math examples.
- `ultron_verify.py`: independent answer verification for supported generated problem types.
- `ultron_training.py`: masked prompt/solution training, resumable batch stream, optimizer loop, greedy completion, topic evaluation, and a held-out mastery curriculum controller.
- Existing tests validate tensor mechanics, deterministic data generation, example verification, training updates, and curriculum state. They do not establish broad mathematical competence.

The current model is a small character-level baseline, not a GPT-scale general-purpose model. Its 192-character context is below the earlier 1024-token design target. That mismatch must be resolved deliberately before a full training run.

## Target architecture

### 1. Core model

Keep one compact, randomly initialized model in the 3–5 million parameter range for the first foundation release. Improve its tokenizer and context design only after measuring memory, throughput, and held-out accuracy. Do not silently increase the parameter budget.

### 2. Test-time reasoning controller

Add an explicit, bounded controller around model inference:

1. Parse the question and identify its topic.
2. Produce a short candidate solution plan.
3. Generate one or more candidate solutions within a fixed compute/token budget.
4. Check each candidate with deterministic tools where possible.
5. Rank candidates using verifier results and consistency checks.
6. Return the best verified answer, or clearly report that verification failed.

This is an external inference algorithm around the model, not a claim that the model has hidden human-like reasoning. Keep intermediate traces bounded and do not expose private chain-of-thought; return concise, user-facing solution steps.

### 3. Specialist task modules

Start with deterministic Python modules rather than multiple copies of the same small model. Each module has a narrow interface and a known test set:

- Arithmetic and number operations
- Fractions, ratios, percentages
- Algebra and equations
- Geometry and measurement
- Statistics and probability
- Later: trigonometry, logarithms, calculus, proofs

A router selects a specialist; the verifier checks its result; the controller may request another candidate when the first fails. Parallel execution is optional and must be justified by measured latency/resource cost.

### 4. Independent verification

Use exact arithmetic (fractions/integers) where possible. Add symbolic or numerical checks only with explicit tolerances and domain rules. Keep the verifier independent from the generator and model so that a shared bug cannot make incorrect answers appear correct.

### 5. Feedback-driven learning

Progress in this order:

1. Supervised training on independently generated and verified examples.
2. Held-out evaluation by topic and difficulty.
3. Error clustering to identify systematic weaknesses.
4. Regenerate targeted examples with new seeds and verify them independently.
5. Only then experiment with verifier-rewarded candidate selection or policy optimization.

Do not begin reinforcement learning merely because it is part of a modern-model recipe. For a small model and limited compute, first establish a reliable supervised baseline and a stable reward signal. Any policy-optimization experiment needs a frozen evaluation set, reward-hacking tests, checkpoint rollback, and a measured improvement over the supervised baseline.

### 6. Tool use

Introduce tools as explicit, typed local functions with strict input/output schemas, timeouts, and resource limits. Initial tools should be deterministic math operations and a sandboxed code evaluator. The model may propose a tool call; the controller validates arguments and executes only allowlisted tools. No arbitrary shell execution, remote computer control, device pairing, or dashboard-to-runtime commands.

### 7. Memory and checkpoints

Separate:
- Model weights and optimizer/training state
- Verified mathematical facts/rules
- Error examples and evaluation results
- Run metadata and checkpoint manifests

Only verified, versioned content may enter durable knowledge memory. Checkpoints must be atomic, integrity-checked, and recoverable to the last known-good state.

## Efficiency constraints

- $0 budget; no paid APIs or external inference services.
- No pretrained weights or external model.
- No externally generated training data; use ULTRON's own deterministic generators and independent verification.
- Begin with sequential, bounded inference. Add parallel specialist execution only after profiling.
- Use fixed maximum candidate counts, token budgets, timeouts, and batch sizes.
- Keep the 3–5M parameter target for the first model.
- Do not claim the browser RAM preference is an enforced operating-system memory cap.
- Do not claim a free hosted notebook will run continuously or retain state indefinitely.

## Safety and product boundaries

- No extra moderation/filter pipeline in the initial math-focused prototype, as requested.
- Essential engineering protections remain: strict input validation, bounded resource use, typed tool allowlists, checkpoint integrity, and dependency hygiene.
- Training controls remain local to the device/process running training.
- No device pairing, remote commands, remote start/stop, HTTP control listener, or dashboard training writes.
- Actual training remains disabled until the website/frontend priorities, local runtime validation, and a separate explicit training approval are complete.

## Implementation sequence

1. **Architecture baseline:** document the existing model/data/verifier/trainer and the gaps (this document).
2. **Inference controller:** bounded candidate generation, deterministic tool routing, independent verification, and regression tests.
3. **Specialist modules:** narrow mathematical solvers with exact arithmetic and test coverage.
4. **Tokenizer/context study:** benchmark candidate tokenizer/context changes without changing the parameter target; resolve 192-character versus 1024-token requirements.
5. **Evaluation harness:** frozen, non-overlapping held-out tests by topic/difficulty; report accuracy, exactness, latency, and memory.
6. **Supervised baseline:** only after frontend and local runtime gates are satisfied and training is explicitly approved.
7. **Feedback and RL experiments:** only if measured results justify the additional complexity.

## Completion criteria

ULTRON is not considered a reasoning system merely because it has a Transformer or can print solution-like text. Each milestone must include tests and measured results. Report exact-answer accuracy on unseen problems, verifier pass rate, failure/abstention rate, latency, peak memory, and reproducibility. Never infer learning from falling training loss alone.
