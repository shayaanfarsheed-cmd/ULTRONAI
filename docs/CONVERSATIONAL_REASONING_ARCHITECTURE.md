# ULTRON conversational reasoning architecture

**Status:** design baseline; implementation is staged and training remains disabled.  
**Product scope:** a from-scratch, mathematics-first assistant with a natural conversational interface.  
**Non-goal:** cloning GPT, Astra, or Claude, reproducing their proprietary weights/data, or claiming equivalent general intelligence.

## 1. Product qualities to build

ULTRON should progressively combine useful interaction patterns associated with strong assistants:

| Quality | ULTRON implementation target | Evidence required |
|---|---|---|
| Natural conversation | Multi-turn chat, context-aware follow-up questions, clear explanations | Conversation regression tests and human review |
| Deliberate reasoning | Explicit problem representation, solution plan, intermediate steps and alternative methods | Step-level correctness tests |
| Reliability | Independent verification, contradiction detection, calibrated uncertainty and abstention | Adversarial and held-out evaluations |
| Learning | Diagnose errors, select targeted practice, revisit skills and track mastery | Before/after per-topic and delayed-retention metrics |
| Useful memory | User-visible session context and verified learning records with provenance | Retrieval relevance, deletion and privacy tests |
| Tool discipline | Bounded, allowlisted mathematical tools; no arbitrary code execution | Input-validation and security tests |

These are engineering goals, not claims that ULTRON will have human-like consciousness or frontier-model performance.

## 2. Current baseline (do not overstate it)

- `ultron_model.py` is a randomly initialized decoder-only transformer with 4,038,478 parameters, a 78-character tokenizer and a 192-token context.
- `ultron_agent.py` is a deterministic, rule-based solver for 14 foundation topics. It is not the transformer and does not update its weights.
- The browser Math Agent is also deterministic and supports restricted question formats.
- `ultron_verify.py` independently checks supported generated/solved examples; `ultron_evaluation.py` scores predictions against a frozen held-out pilot.
- Adaptive topic-weighted sampling exists in the training stream, but it does not itself make the neural model reason.
- The held-out pilot is small and cannot establish broad mathematical ability.
- No real training has started.

A 3–5 million parameter model is a constrained specialist target. It should not be represented as a drop-in equivalent to large proprietary general-purpose assistants. A small model may become useful on a carefully bounded mathematics curriculum if the data, tokenizer, context, training and evaluation are designed for that scope.

## 3. Target request-to-answer pipeline

Every user turn should pass through explicit, testable stages:

1. **Conversation manager** — maintain bounded session history, identify follow-ups, and ask for missing information instead of guessing.
2. **Intent and scope router** — classify the request as supported mathematics, explanation, hint, checking, study planning, or unsupported/out-of-scope.
3. **Problem parser** — convert supported natural-language questions into a typed representation (quantities, units, operators, constraints, unknowns and requested output).
4. **Planner** — select prerequisites and a sequence of solution operations; expose a concise plan, not hidden chain-of-thought.
5. **Candidate solver** — use the neural model for language and candidate generation, and approved exact mathematical tools where appropriate.
6. **Independent verifier** — recompute answers and validate each formal step using a separate implementation or trusted exact arithmetic. Never treat model confidence or self-critique as proof.
7. **Repair gate** — when a check fails, identify the failed step and allow a bounded correction attempt. If verification still fails, report uncertainty or abstain.
8. **Response renderer** — produce a direct answer, requested level of detail, worked explanation, assumptions and verification status.
9. **Learning recorder** — only with the applicable consent and retention rules, record the question category, verified outcome and diagnosed misconception. Do not silently turn every chat into training data.

The assistant must not reveal private internal reasoning traces. It can provide concise explanations, verifiable intermediate calculations, assumptions and a summary of the method.

## 4. Reasoning and learning subsystems

### A. Structured problem representation

Create typed representations for arithmetic, fractions, equations, inequalities, geometry, statistics and probability. Include validation for dimensions, units, domains, division by zero, extraneous roots and boundary conditions. Preserve the original question so the final response can be checked against the user's actual request.

### B. Step-level diagnosis

Represent a worked solution as a sequence of typed operations. When an answer fails, compare the submitted steps against independently computed constraints and label the first failing operation (for example: sign error, invalid transformation, arithmetic error, missing condition, or unsupported inference). A diagnosis must be supported by a reproducible check; do not guess a misconception from the final answer alone.

### C. Adaptive teaching

Track mastery by concept, not only by broad topic. Choose a next exercise using verified performance, difficulty and time since last successful recall. Revisit older concepts on a spaced schedule. Keep held-out evaluation data strictly outside training, curriculum selection and memory updates.

### D. Concept graph

Define prerequisite relationships, such as integer operations → fractions → ratios → percentages → algebra. Store graph version and provenance. Use the graph to explain dependencies and select remediation exercises; never treat a suggested prerequisite as proof that the learner lacks that skill.

### E. Memory and retrieval

Separate short-lived conversation context from durable learning records. Store provenance, verification status, timestamps and deletion metadata. Retrieved records are evidence candidates, not automatically true facts. Re-verify mathematical claims before relying on them.

### F. Neural model evolution

Before changing the model:
- benchmark the current random baseline and establish a reproducible training/evaluation protocol;
- replace or justify the character tokenizer for mathematical natural language;
- evaluate context length and parameter allocation against the $0 compute budget;
- create independently verified, diverse training examples from the project's own generator;
- keep train, validation and frozen test data isolated;
- measure exact answer accuracy, step validity, calibration, topic/difficulty performance and retention;
- compare every candidate checkpoint against the previous baseline and roll back regressions.

No pretrained model, pretrained weights, external AI API or externally generated training data may be introduced. The 3–5M parameter target remains a specialist constraint, not a promise of GPT/Claude-level breadth.

## 5. Conversation behavior contract

- Accept ordinary natural-language questions where supported; do not require the user to select a topic manually when it can be inferred safely.
- Ask one focused clarification when essential information is missing or ambiguous.
- Explain at the requested level: concise answer, hint, step-by-step teaching, or deeper proof-style explanation.
- Distinguish verified results, plausible suggestions and unknowns.
- State assumptions and units; never invent sources or pretend to have used a tool.
- For unsupported questions, say what is unsupported and what information or narrower question would be answerable.
- Preserve user control over memory and never use private conversation content as training data without explicit authorization.

## 6. Delivery gates

### Stage 0 — Architecture baseline (this document)
- Record the target behavior, current limitations, interfaces and evidence gates.
- No model, data, database or training changes.

### Stage 1 — Conversational mathematics shell
- Add a multi-turn chat interface that works on iPad-sized screens.
- Route supported questions to the existing deterministic solver.
- Add bounded session context, clarification, response modes and honest unsupported-input behavior.
- Do not call the neural model "trained" or imply it powers deterministic answers.

### Stage 2 — Structured reasoning kernel
- Add typed problem representations, explicit plans and step-level verifier results.
- Add independent tests for each supported operation and adversarial edge cases.
- Add bounded repair and abstention behavior.

### Stage 3 — Diagnosis and teaching
- Add evidence-based error categories, prerequisite links, adaptive difficulty and spaced review.
- Validate delayed retention and generalization on new held-out problems.

### Stage 4 — Neural language and reasoning capability
- Reassess tokenizer, context and model configuration.
- Train from random initialization only after the dataset, evaluation and recovery gates pass.
- Compare against the deterministic baseline; do not let generated fluent text substitute for mathematical correctness.

### Stage 5 — Broader assistant capabilities
- Consider broader non-mathematical conversation only after the math specialist demonstrates reliable results and the data/model budget is explicitly reassessed.

## 7. Safety, scope and release gates

- No real training is authorized by this design document.
- No paid services, external AI APIs, pretrained weights or external training data.
- No production Supabase schema, policy, secret or Edge Function changes.
- No automatic ingestion of chat logs into training.
- No arbitrary code execution from user input or uploaded content.
- Each implementation stage requires unit tests, regression tests, full required CI, code review and an updated README.
- Merge only after the owner explicitly approves the reviewed PR.
