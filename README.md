# ULTRON

**ULTRON is an independently developed, mathematics-focused learning system.** Its long-term goal is to train a small transformer from random initialization using project-generated, independently checked mathematics data. The project also contains a browser-based mathematics tutor and a deterministic formal proof checker.

> **Current status (21 November 2026):** The website, deterministic mathematics tools and a growing formal proof kernel are implemented. The neural model exists but is **untrained**. Real model training has not started.

- **Live dashboard:** [Open ULTRON Training Control](https://shayaanfarsheed-cmd.github.io/ULTRONAI/)
- **Repository:** [shayaanfarsheed-cmd/ULTRONAI](https://github.com/shayaanfarsheed-cmd/ULTRONAI)
- **Formal proof-kernel specification:** [docs/FORMAL_PROOF_KERNEL.md](docs/FORMAL_PROOF_KERNEL.md)
- **Reasoning architecture:** [docs/CONVERSATIONAL_REASONING_ARCHITECTURE.md](docs/CONVERSATIONAL_REASONING_ARCHITECTURE.md)
- **Axiom Bank research:** [docs/AXIOM_BANK_RESEARCH.md](docs/AXIOM_BANK_RESEARCH.md)


## Latest verified status — preserved deployment and control evidence

The following is historical deployment evidence retained from the previous README. It is not a substitute for rechecking the live service during a new deployment.

- PR [#96](https://github.com/shayaanfarsheed-cmd/ULTRONAI/pull/96) merged at 397199389a1c829ff3107cff5560a2c27516fd9a.
- At that milestone, **236 unit tests** passed, and browser smoke tests passed in **Chromium and WebKit**.
- The **GitHub Pages build and deployment succeeded** for the recorded merge commit. Dashboard: https://shayaanfarsheed-cmd.github.io/ULTRONAI/.
- The dashboard had 11 views. This is historical deployment evidence; the current product direction is an account-free public website with no login/sign-up or account-specific controls.
- The RAM slider was a browser-local preference, not a remote runner RAM or GPU-VRAM limit.
- Production Supabase training-control was recorded as ACTIVE, **version 6**, with verify_jwt=true; the deployment record says the deployed source matches exactly the checked-in function source.
- Historical note: the former owner-only **Refresh status** flow depended on a signed-in browser and is not part of the current account-free product requirement. Do not restore it without an explicit product decision and security review. The preflight includes a Deno type-check for the Supabase function.
- Remaining manual checks recorded at that time included a physical iPad/phone check and production security tests for invalid/expired JWTs, non-owner denial, public dispatch denial and secret non-disclosure. Reassess these against the current account-free architecture rather than assuming owner authentication remains required.
- Earlier deployment evidence: PR #80 ([pull request](https://github.com/shayaanfarsheed-cmd/ULTRONAI/pull/80)) merged with all three then-required checks passing. The production training-control function was recorded as ACTIVE, **version 5**, with verify_jwt=true.
- The launch adapter used GitHub Actions workflow_dispatch for the CPU diagnostic workflow. The deployed function source was fetched after deployment and matched the GitHub main source exactly.
- No diagnostic was launched and no model training was started. No weights or persistent checkpoints were modified during that recorded work.

## Authoritative model baseline correction

Model architecture, parameter count, tokenizer, dataset state and training readiness must be verified from current source files and manifests. Historical README statements are not authoritative when they conflict with executable code. The model remains untrained until the roadmap readiness gates pass and the owner separately authorizes a real run.

## Latest verified status — current code and deployment evidence

- PR [#96] and its deployment details above are preserved for compatibility with existing repository documentation checks.
- The recorded deployed function source was required to **source matches exactly** the checked-in function source; the current deployment must be rechecked before any privileged diagnostic.
- Run the Deno type-check for the Supabase function as part of preflight.
- The current account-free product direction excludes owner-only **Refresh status** and other account-bound dashboard controls. Keep remote execution unavailable from the public UI until a separately reviewed control design is approved.
- No diagnostic was launched and no model training was started.

## Latest verified engineering status — 2026-11-21

**Conservative whole-project completion estimate: 35%.** This is a milestone-based estimate across the website, security, mathematics interface, proof kernel, data pipeline, model/evaluation, free compute and release readiness. The browser tutor and formal reasoning foundations are substantially implemented, but physical-device verification, complete frontend acceptance, remaining mathematical/formal coverage, diagnosis integration, independent corpus validation, model evaluation and training-readiness gates remain incomplete.

Merged proof-kernel milestones on current `main`:
- PR #121 — typed non-strict probability order; PROB-01 is stated directly as (0 \leq \mu(A)).
- PR #122 — ZFC separation and replacement schema-instance rules with capture-safe binder checks.
- PR #125 — ordered-field axioms ORDER-01 through ORDER-04 and COMPLETE-01 least-upper-bound property.
- PR #129 — COMPLETE-01 non-strict comparisons are tied to ORDER-01 trichotomy through negated reverse strict comparisons.
- PR #132 — ZFC-10 expanded into quantified set-membership formulas using Kuratowski ordered pairs and exact-domain function graphs.
- PR #133 — prototype-safe binder environments and rejection of empty variable/sort names.
- PR #134 — iterative proof-input validation and explicit step, assumption, node, depth, array, object and string limits.

The five required validation groups passed for the listed code milestones: Test Suite, preflight, Training Prototype Validation, Chromium and WebKit. Check current Actions state before relying on historical results.

**Training status: NOT STARTED.** No real training run has been authorized. No pretrained weights or external AI APIs are used. Do not change this status until an owner-authorized run actually starts and its artifacts are verified.

## What works today

### Browser dashboard and mathematics tutor

The GitHub Pages site is designed for desktop, mobile and iPad-sized screens. The intended experience is fully account-free: no login/sign-up, no account-specific history, and no pairing controls. Remote execution and real training remain unavailable from the public website.

The dashboard includes:
- System overview and learning information.
- Ask ULTRON conversation view.
- Deterministic Math Agent and structured reasoning views.
- Data Library, activity and training-control views.
- Server, checkpoint and settings views.
- Light/dark theme and responsive navigation.

The conversation shell supports simple arithmetic and explicitly registered foundation topics. It asks for clarification when a question is unsupported and independently verifies supported answers. Conversation history is temporary in-memory session state; it is not automatically added to training data.

**Important:** The current browser tutor and Math Agent use deterministic, bounded code. They do not run the neural transformer.

### Structured reasoning and verification

The reasoning layer represents supported problems with typed data, builds explicit solution plans and checks supported final answers with independent verifiers. Replay checks detect tampering with structured reports.

This is not yet a general natural-language mathematics parser. Explanatory steps are not automatically formal proofs unless the formal proof checker validates a structured derivation.

### Formal proof kernel

`dashboard/proof-kernel.js` implements a deterministic proof replayer with seven isolated contexts:

- Peano arithmetic (`PEANO_N`)
- Real fields (`REAL_FIELD`)
- Ordered fields (`ORDERED_FIELD`)
- Complete real fields (`COMPLETE_REAL`)
- Euclidean geometry (`EUCLID_GEOMETRY`)
- Kolmogorov probability (`KOLMOGOROV`)
- Zermelo–Fraenkel set theory (`ZFC`)

The kernel checks typed expressions, exact axiom identifiers, formal-system boundaries, inference rules, proof dependencies and schema use. It rejects malformed proof structures, unsupported derivations, unsafe binder environments and oversized/cyclic proof inputs.

Implemented foundations include:
- Peano successor arithmetic and a dedicated induction schema.
- All nine researched real-field axioms, explicitly available in the ordered-field and complete-real contexts.
- ORDER-01 through ORDER-04: trichotomy, strict-order transitivity, translation invariance and multiplication by a positive factor.
- COMPLETE-01: the least-upper-bound property over nonempty, bounded-above `RealSet` subsets of the ordered field. Non-strict comparisons are expanded as the negation of the reverse strict comparison, relying on ORDER-01 trichotomy.
- Euclidean incidence/construction and parallel-postulate relations.
- Probability non-negativity, sample-space normalization and countable additivity.
- ZFC finite axioms, separation/replacement schema-instance rules, and ZFC-10 choice expanded through Kuratowski ordered pairs and function graphs with exact domain and unique outputs.
- Binder-environment hardening for prototype-sensitive variable names and iterative proof-input limits: 4,096 steps, 4,096 assumptions, 100,000 object/array nodes and depth 256.

The ZFC-10 formula defines indexed families of nonempty sets and choice functions using ordinary quantified Set-membership formulas. The checker validates the axiom statement; it does not compute or construct a choice function for arbitrary families. The `RealSet` domain is a formal subset domain, not a general set-construction evaluator or numerical supremum engine.

The proof kernel is **not** a general theorem prover, does not establish consistency of its axioms, and does not prove that the neural model has learned mathematics. Consult `docs/FORMAL_PROOF_KERNEL.md` for exact executable coverage and limitations.

### Model and data pipeline

The repository contains an independently implemented decoder-only transformer:

| Property | Current baseline |
|---|---:|
| Initialization | Random |
| Architecture | Decoder-only transformer |
| Parameters | 4,039,504 |
| Tokenizer | Character-level |
| Vocabulary | 80 characters |
| Context length | 192 tokens |

The model implementation is in `ultron_model.py`. The deterministic mathematics agent is separate (`ultron_agent.py`).

Project code includes mathematics-data generation, quality checks, verification, checkpoint/recovery utilities, evaluation and training orchestration. The held-out foundation evaluation set contains 18 examples across 18 topics. It is reserved for evaluation and must not be used as training data. The evaluation scorer is read-only and is not yet a complete transformer-inference benchmark.

**The model has not been trained.** The parameter count describes the current architecture, not learned capability or performance.

## Project principles and safety boundaries

These are project requirements, not optional optimizations:

- No external AI APIs.
- No pretrained model or pretrained weights.
- Initialize the model from random weights.
- Generate training examples with ULTRON's own code and independently verify them.
- Keep held-out evaluation data separate from training and curriculum selection.
- Use free compute only; do not add paid services or payment methods.
- Never commit secrets or expose backend credentials in browser code.
- Respect provider quotas, usage limits and terms; do not evade limits.
- Keep actual training disabled. Do not start a real training run until every readiness gate passes and the owner gives separate, explicit authorization for that specific run.

The dashboard's RAM slider is a **browser-local preference**. It does not set the memory limit of a remote runner or control GPU VRAM. Device/browser memory monitoring is not equivalent to enforced training-process limits.

The intended website experience is account-free: no login, sign-up, account-specific training history, or account-pairing controls. Keep real training and remote execution unavailable from the public website until a separately reviewed, safe control design exists. Do not add account-based features without an explicit product decision.

## Current development priorities

Work should proceed in small, independently testable increments:

1. Finish and verify the account-free website experience on physical iPad and mobile devices, in addition to automated Chromium and WebKit tests.
2. Verify that no login/sign-up, account-specific history, pairing controls or privileged training actions are exposed in the public frontend; verify that secrets and backend credentials are never exposed.
3. Continue adversarial review and expansion of the formal proof kernel. Add a rule only when its mathematical side conditions can be checked.
4. Connect validated proof traces to step-level mistake diagnosis without treating unverified work as evidence.
5. Complete model, dataset, evaluation, checkpoint recovery and compute-readiness audits.
6. Keep real training disabled until every readiness gate passes and separate owner authorization is given.

Do not use a project-wide percentage as a substitute for reporting which components are implemented, tested, deployed or still blocked.

## Repository map

| Path | Purpose |
|---|---|
| `dashboard/` | GitHub Pages dashboard, browser tutor, reasoning layer and proof kernel |
| `ultron_model.py` | Randomly initialized transformer architecture |
| `ultron_agent.py` | Deterministic mathematics solver |
| `ultron_data.py`, `ultron_seed_dataset.py` | Mathematics data generation |
| `ultron_verify.py`, `ultron_dataset_quality.py` | Independent answer and dataset checks |
| `ultron_evaluation.py`, `evaluation/` | Read-only held-out evaluation |
| `train.py`, `train.ipynb`, `compute_provider_diagnostic.ipynb` | Training and compute workflows (training remains gated) |
| `ultron_checkpoint.py`, `ultron_storage.py`, `ultron_recovery_test.py` | Checkpoint, storage and recovery code |
| `config.json`, `servers.json` | Project and compute-provider configuration |
| `supabase/` | Backend functions and database-related source |
| `tests/` | Automated regression and validation tests |
| `docs/` | Architecture, formal-system and research documentation |
| `.github/workflows/` | CI, browser checks and controlled workflow automation |

## Running and testing

### Open the website

Use the [deployed GitHub Pages dashboard](https://shayaanfarsheed-cmd.github.io/ULTRONAI/). The repository root redirects to `dashboard/`.

To preview locally, serve the repository root with any static HTTP server and open the resulting local URL. Do not open the HTML file directly if browser module or origin restrictions interfere.

### Python dependencies

Use a supported Python environment and install the pinned/ranged project dependencies:

```bash
python -m pip install -r requirements.txt
```

### Validation

The repository's GitHub Actions workflows are the authoritative project validation. Relevant workflows include:

- `test-suite.yml` — automated test suite.
- `preflight-tests.yml` — project preflight checks.
- `training-prototype.yml` — bounded training-prototype validation; this is not authorization for real training.
- `dashboard-browser-smoke.yml` — browser smoke tests, including Chromium and WebKit coverage.

For proof-kernel work, the focused regression suite is `tests/proof_kernel.test.js`. Run the full required CI checks for a proposed change; a focused local test alone is not sufficient for merge.

## Contribution and change-control rules

1. Start new work from the latest `main`.
2. Make one focused change per small patch or pull request.
3. Add positive and adversarial regression tests for behavior changes.
4. Update this README when the user-facing project status, architecture or next steps materially change. Keep detailed technical specifications in `docs/`.
5. Review the exact diff and require all applicable CI checks to pass before merging.
6. Never weaken or bypass a failing test to make a check green.
7. Do not start training, alter model weights or mutate persistent checkpoints without the separate readiness and authorization gates.

## Current handoff

**Next task:** continue the formal-kernel soundness audit from current `main`, starting with rule-specific side conditions, schema freshness and adversarial proof cases. Then return to Stage 1 and finish the GitHub Pages frontend against the account-free, iPad/mobile/desktop requirements. Do not start training while website, data, evaluation, recovery and readiness gates remain incomplete.

**Training state:** not started. This README does not authorize a training run. A separate, explicit owner approval is required after every readiness gate passes.



# Full development roadmap — from current state to the first real training run

This is the execution plan for future development chats. Follow it in order. The goal is to finish and validate the website-controlled ULTRON system, mathematical foundations, independently generated training corpus, model/evaluation pipeline and recoverable compute workflow **before** starting the first real training run.

Work incrementally. Complete one focused work unit, test it, inspect the exact diff, update this README when a milestone changes, and report the result before beginning another unit. Do not combine unrelated stages into one large patch.

## How the next chat must work

At the start of every continuation:

1. Read this README and the linked architecture/specification documents.
2. Inspect the current default branch commit, open pull requests, recent commits and active CI runs. Do not assume an old PR or branch is current.
3. Inspect the exact code and tests for the stage being continued. The repository is the source of truth, not an old chat summary.
4. Identify the smallest incomplete task with a clear acceptance test.
5. State the intended change and files before editing. Keep one logical change per branch/PR.
6. Add positive, negative/adversarial and regression tests where applicable.
7. Run focused tests first, then all applicable CI checks. Review the complete diff for unrelated changes.
8. Merge only after the exact reviewed commit has all required checks passing and no unresolved review or merge conflicts. Never bypass a failing check.
9. Update this README with verified outcomes, remaining work and the next exact task. Do not mark code complete merely because it was written.
10. Report what changed, the commit/PR, actual test results, what remains, and whether the deployed website was verified.

If a test cannot be run, mark it **not run** or **blocked** and explain why. Never report a skipped test as passed. Avoid invented percentages; use statuses such as implemented, tested, merged, deployed, incomplete and blocked.

## Non-negotiable project boundaries

- Build ULTRON's model, tokenizer, mathematics data generation, training and evaluation code independently.
- Do not call external AI APIs. Do not download or use pretrained models, pretrained weights or third-party model checkpoints.
- Initialize the neural model from random weights.
- Generate training examples using project-owned generators and verify them independently. Do not use externally generated synthetic training data.
- Keep the held-out evaluation set isolated. Never train on it, tune curriculum against it, or leak its answers into training examples.
- Keep the project within the approved free-compute budget. Do not add paid services, payment methods or surprise costs. Respect provider terms, quotas, idle limits and session limits; never evade restrictions or create accounts to bypass limits.
- The website is the control surface and must remain usable on iPad, mobile and desktop browsers. Do not make the owner depend on a laptop for ordinary project control. The public experience is account-free; do not add login, sign-up, account-specific history or pairing.
- The public website must remain account-free: no login/sign-up, account-specific training history or pairing controls. Do not expose remote execution or training actions through the public UI while training is disabled. Any future remote execution capability requires a separately reviewed server-side authorization design.
- The RAM/resource slider must be labelled honestly. A browser preference is not a remote process memory limit or GPU-VRAM control. Show actual runner limits only when the runner reports them.
- Do not start real training, update model weights, mutate production checkpoints or launch a long-running training job until the final readiness gate passes and the owner separately authorizes the run.

## Stage 0 — establish the true baseline

**Purpose:** prevent work from being based on stale PRs, inaccurate documentation or assumptions from earlier chats.

Tasks:
- Inspect the current default branch and record its commit SHA.
- List open, closed and merged PRs relevant to the roadmap. Identify stale branches and superseded patches; preserve useful changes without merging obsolete history.
- Confirm which dashboard, security, proof-kernel, data, evaluation, training and recovery features actually exist in the current default branch.
- Inspect the GitHub Pages workflow and deployment target. Confirm which directory is published and whether the live site corresponds to the current commit.
- Inspect every workflow referenced in this README. Correct workflow names if they changed.
- Run existing preflight and test workflows; record baseline failures.
- Check README links and referenced paths.

Acceptance criteria: a baseline report identifies the current commit, open PRs, CI state, live deployment state and next verified task. No application code, model weights, datasets or checkpoints are changed during this inventory.

## Stage 1 — finish the website and device experience

**Purpose:** make the browser control surface reliable before connecting it to real training.

Tasks:
1. Audit every route, navigation item, button, modal, form, status card and settings control. Remove dead controls or implement their stated behavior.
2. Verify the user journey: open dashboard, inspect system state, use the mathematics tutor, inspect reasoning/proof results, inspect data/evaluation status, and inspect training readiness without starting training.
3. Verify responsive layout at narrow mobile widths, common iPad/tablet widths, portrait and landscape orientations, and desktop sizes.
4. Run automated Chromium and WebKit tests. Add regression coverage for overflow, keyboard focus, touch targets, navigation state, empty/error/loading states and refresh behavior.
5. Perform a physical-device check when available. Automated emulation is not proof of every iPad browser behavior.
6. Make every status display distinguish live server data from cached, local, estimated or unavailable data.
7. Make the RAM slider's scope explicit. If it is only a local preference, do not display it as an enforced runner limit.
8. Verify that every public website route works without login/sign-up and that no account-specific history or pairing controls remain.
9. Verify that no privileged training or remote-execution controls are exposed; stale account/session UI from the former design must not remain.
10. Test accessibility basics: semantic controls, labels, contrast, focus order, keyboard operation and screen-reader names.

Acceptance criteria: all visible controls have defined tested behavior; no horizontal overflow at supported viewport sizes; Chromium and WebKit checks pass; physical iPad status is separately recorded; account-free behavior and absence of privileged public controls are tested.

## Stage 2 — harden public service boundaries and future remote-execution safeguards

**Purpose:** ensure that an account-free public website cannot accidentally or deliberately operate remote training resources.

Tasks:
- Inventory every backend endpoint and any remaining privileged operation. Confirm that the public website has no account-specific control surface.
- Keep remote execution and training endpoints disabled or unavailable to the public frontend until a separately reviewed control architecture is approved.
- If a future privileged service is approved, define and test its authorization boundary before exposing it; do not reintroduce login/account features by assumption.
- Confirm public responses never contain secrets, privileged provider metadata, private logs, checkpoint locations or owner-only data.
- Review CORS, request methods, input schemas, payload sizes, rate limits and error messages.
- Store credentials only in approved secret storage; never bundle them into GitHub Pages assets or client-side JavaScript.
- Review workflow permissions and token scopes using least privilege.
- Keep destructive operations and training launch unavailable until the final readiness gate and separate owner authorization.
- Add audit events for any future privileged service without logging secrets or sensitive payloads.
- Test repeated submissions, malformed requests, delayed responses and fail-closed behavior for any future remote control endpoint.

Acceptance criteria: the public frontend exposes no privileged training/remote-execution actions; no browser bundle or public API response leaks secrets; future privileged endpoints (if approved) have a documented authorization test matrix and fail-closed behavior.

## Stage 3 — complete the mathematical expression and problem interface

**Purpose:** establish a typed mathematical language between questions, deterministic solvers, formal proofs and future model outputs.

Tasks:
1. Define a versioned expression AST for supported constants, variables, arithmetic operations, relations, functions, sets, sequences, quantifiers and domain-specific objects.
2. Define explicit sorts and type rules. Reject invalid operations and incompatible formal contexts.
3. Define a typed formula AST separately from terms. Include equality, order, predicates, logical connectives and quantifiers only when their semantics and checking rules are specified.
4. Build a conservative parser for supported written notation and natural-language patterns. Ambiguous or unsupported input must trigger clarification, not a guessed parse.
5. Preserve the original question and structured parse so users can inspect what ULTRON understood.
6. Add canonical serialization, stable identifiers and strict schema validation. Reject unknown fields, malformed nodes, sparse arrays, excessive depth and oversized input.
7. Keep parsing separate from proof validation: a plausible parse is not a proof.
8. Test precedence, parentheses, negative values, fractions, exponents, variables, malformed syntax, ambiguous notation, type errors and adversarial payloads.

Acceptance criteria: every accepted expression has a deterministic typed representation; invalid/ambiguous expressions are rejected or clarified; serialization/replay is deterministic; parser output is never automatically trusted as a verified result.

## Stage 4 — finish and audit the formal proof kernel

**Verified recent formal-kernel milestones:** PR #121, #122, #125, #129, #132, #133 and #134 are merged. Current code includes explicit ordered-field/completeness axioms, ZFC separation/replacement and a ZFC-10 choice statement expanded through Kuratowski pair/function-graph formulas, plus binder and resource hardening. The checker does not construct an actual choice function, evaluate suprema or act as a general theorem prover. Consult `docs/FORMAL_PROOF_KERNEL.md` before claiming broader support. Recheck current main and CI before extending this work.


**Purpose:** make proof traces trustworthy enough to support later mistake diagnosis and verified training examples.

The current proof kernel has isolated contexts for Peano arithmetic, real fields, ordered fields, complete real fields, Euclidean geometry, Kolmogorov probability and ZFC. It already contains typed syntax, strict proof-object validation, dependency tracking, quantifier rules, Peano induction, field axioms, Euclidean relations, probability relations and ZFC separation/replacement schemas. **Always verify exact executable coverage in current code and the formal-kernel specification.** A declared context or Axiom Bank entry does not automatically mean an inference rule is executable.

Work in small domain-specific increments:

### 4A. Kernel soundness audit
- Completed: implication-discharge dependency checks, universal/existential eigenvariable and witness-scope checks, capture-aware substitution, prototype-safe binder environments and bounded proof/trace input validation.
- Continue adversarial review of assumption introduction/discharge, dependency propagation, quantifier scope, schema freshness, premise arity and every rule-specific side condition.
- Confirm every rule checks all mathematical side conditions.
- Reject forged conclusions, forged axiom IDs, cross-context premises, duplicate IDs, forward references, unknown properties and malformed envelopes.
- Ensure replay is deterministic and cannot execute arbitrary user code.
- Add a positive example and adversarial negative examples for every enabled rule.

### 4B. Peano arithmetic
- Audit zero/successor representation, equality, induction schema and natural-number typing.
- Expand addition, multiplication, order and elementary number theory incrementally, only when each rule is checkable.
- Test base cases, recursive cases, boundary values, forged induction instances and variable capture.

### 4C. Field and ordered-field reasoning
- Preserve exact real-field axiom identifiers and statement mappings.
- Implemented: FIELD-01 through FIELD-09 plus ORDER-01 through ORDER-04 are explicitly enabled in ORDERED_FIELD and COMPLETE_REAL.
- Next: audit derived inequality properties and ensure every future order rule states all premises and side conditions explicitly.
- Keep field, ordered-field and complete-real contexts isolated.

### 4D. Completeness of the real numbers
- Implemented: COMPLETE-01 states the least-upper-bound property over nonempty, bounded-above RealSet subsets of Field, with non-strict comparisons derived from ORDER-01 trichotomy.
- Limitation: RealSet is a typed subset domain, not a full power-set/set-construction evaluator; the checker does not compute numerical suprema.
- Next: adversarially test empty sets, unbounded sets, missing upper bounds and invalid least-upper-bound claims; extend only when the representation supports the side conditions.

### 4E. Euclidean geometry
- Audit typed point, line, circle, segment and angle representations already added.
- Add construction/incidence rules only with explicit existence, uniqueness and non-degeneracy conditions.
- Add a small library of derived geometric theorems with machine-checkable traces.
- Test degenerate configurations, inconsistent incidence and invalid construction premises.

### 4F. Probability
- Preserve typed measure and non-negativity, normalization and countable-additivity representations.
- Specify measurable spaces, events, event sequences, disjointness and measure values precisely.
- Add finite additivity, complement, monotonicity and derived rules only when provable from enabled axioms.
- Do not claim numerical probability evaluation, convergence or infinite-series computation from primitive syntax alone.
- Test invalid events, non-disjoint sequences, incorrect normalization and malformed sequence objects.

### 4G. Set theory
- Audit ZFC axiom mappings and separation/replacement schema-instance rules.
- ZFC-10 is expanded into quantified Set-membership formulas using Kuratowski ordered pairs. The formula defines function graphs with domain exactly I and unique outputs, nonempty indexed family values, and a choice graph selecting an element from each corresponding set. This formalizes the axiom statement but does not construct a choice function or provide a choice algorithm.
- Keep schema parameters explicit in proof traces.
- Test capture, variable collisions, invalid source sets, forged schema IDs and cross-context inference.
- State which axioms are executable, represented only in the Axiom Bank, or unsupported.

### 4H. Derived theorem library
- Build a small, versioned library of reusable lemmas with proof objects checked by the same kernel.
- Every theorem cites dependencies and exact axiom/schema identifiers.
- Accept a theorem only if replay succeeds from a clean process in its declared context.
- Never hard-code a theorem conclusion as if it were an inference rule.

Acceptance criteria: specification matches implementation; every enabled rule has positive, negative and adversarial tests; every proof replays from typed premises and exact axiom references; cross-system inference and forged traces are rejected; unsupported mathematics is reported as unsupported. Do not claim a general-purpose theorem prover.

## Stage 5 — connect verified work to mistake diagnosis

**Purpose:** diagnose the mathematical step where a learner went wrong, rather than guessing from an incorrect final answer.

Tasks:
1. Define a structured working-trace format with problem ID, formal context, ordered steps, each step's input/output expression, claimed rule and dependencies.
2. Parse only notation and transformations covered by the typed expression language.
3. Replay each accepted step through the proof kernel or a separately specified deterministic checker.
4. Compare each learner step with valid alternatives and identify the earliest invalid transformation.
5. Define error classes only when the observed step supports them: sign error, invalid distribution, invalid cancellation, domain violation, quantifier-scope error and similar precisely defined categories.
6. Distinguish confirmed errors from ambiguous/unparseable steps. Abstain when evidence is insufficient.
7. Explain the exact invalid step and provide a corrected derivation.
8. Keep learner work, proof evidence and training examples as separate data types. A failed proof must not become a positive training example.
9. Test misleading final answers, multiple errors, equivalent transformations, missing steps and forged trace metadata.

Acceptance criteria: diagnosis is tied to a validated trace and exact step; the system can abstain; no misconception is inferred solely from a wrong final answer; diagnoses are reproducible from structured evidence.

## Stage 6 — build the curriculum and tutoring progression

**Purpose:** teach in a controlled, measurable sequence rather than merely return answers.

Tasks:
- Define the foundation curriculum and prerequisite graph, with exact topic scope and learning objectives.
- Define mastery criteria from verified exercises, not unverified self-reports.
- Add difficulty levels only when each has a clear specification and calibrated exercise set.
- Generate progressive hints: conceptual cue, relevant definition/axiom, partial step, then full worked solution.
- Use verified learner traces to select remediation exercises.
- Add spaced review and topic selection with transparent reasons.
- Track mastery and uncertainty separately; a few correct answers must not imply mastery.
- Keep learner-state storage consistent with the no-account public-browsing design. Do not introduce accounts or cross-device identity without an explicit product decision.
- Make reset, export and deletion behavior explicit if learner state becomes persistent.
- Test cold starts, incomplete histories, contradictory evidence, repeated guesses and curriculum dead ends.

Acceptance criteria: every topic has prerequisites, objectives and a measurable mastery rule; adaptive recommendations are explainable; unverified answers do not count as proof of mastery.

## Stage 7 — generate and validate ULTRON's own mathematics corpus

**Purpose:** create reliable, diverse, traceable training data from project-owned generators.

Tasks:
1. Inventory each generator and map it to topic, difficulty, expression type and verification method.
2. Use deterministic seeds and versioned generator configurations so examples are reproducible.
3. Store problem, expected answer, solution trace, generator/version and formal context as separate structured fields.
4. Independently verify answers with a verifier that does not merely repeat the generator's calculation.
5. Replay formal proof traces where possible. Label numeric checking honestly; do not call it a formal proof.
6. Add duplicate/near-duplicate detection, invalid-value filters, domain checks, distribution checks and difficulty checks.
7. Reject ambiguous, malformed, contradictory or unverifiable examples.
8. Maintain provenance and immutable dataset-version manifests.
9. Split train/validation/test by problem family or generator seed to reduce leakage, not by randomly splitting near-duplicates.
10. Keep the frozen held-out foundation evaluation set separate from generation, training, curriculum selection and tuning.
11. Add poisoning and contamination checks, including forged proof metadata and incorrect answers.
12. Produce dataset review reports before approving a corpus version.

Acceptance criteria: every approved example has reproducible provenance and passes independent quality checks; splits are versioned and leakage-audited; held-out evaluation data is isolated and unchanged; dataset size, topic balance, rejection rates and verifier coverage are reported.

## Stage 8 — audit tokenizer, model architecture and resource requirements

**Purpose:** ensure the randomly initialized model can represent the corpus and fit realistic free-compute limits.

Re-check the documented model baseline against source before changing it.

Tasks:
- Audit tokenizer coverage for mathematical symbols, operators, Unicode variants, whitespace and structured delimiters.
- Measure sequence-length distributions and truncation. Decide whether the current character-level tokenizer is sufficient or a project-owned tokenizer is needed.
- Define versioned serialization for problems, reasoning steps, proof traces and answers.
- Audit transformer implementation, parameter count, initialization, attention masks, loss masking, padding, numerical stability and deterministic seed handling.
- Add shape, gradient, tiny-batch overfit and save/reload tests.
- Profile parameter memory, optimizer state, activations, batch size and context length. Distinguish CPU RAM from accelerator memory.
- Do not increase model size merely to appear more capable. Keep the agreed 3–5 million parameter target unless measured evidence justifies a reviewed change.
- Version architecture and tokenizer so checkpoints cannot silently load under incompatible configurations.

Acceptance criteria: architecture and parameter report comes from source; tokenizer round-trip and corpus coverage pass; a tiny test batch can be overfit in a test-only environment; save/reload preserves outputs/configuration; resource estimates are measured and documented.

## Stage 9 — integrate inference with the frozen evaluation suite

**Purpose:** measure the actual neural model, not the deterministic tutor or hand-entered predictions.

Tasks:
1. Implement a versioned inference adapter that loads only ULTRON-owned model configurations and checkpoints.
2. Keep inference separate from scoring and training. The evaluation scorer remains read-only.
3. Convert model output into the exact prediction schema expected by the held-out scorer.
4. Freeze decoding parameters per evaluation run.
5. Add deterministic smoke tests using a tiny test checkpoint created only for tests.
6. Test missing/corrupt checkpoints, incompatible tokenizer versions, invalid output, timeouts and non-finite values.
7. Report exact-match, numeric accuracy, proof validity where applicable, topic-level results, abstention and failure categories.
8. Compare against simple deterministic baselines. Tutor answers are not evidence of neural-model performance.
9. Never tune directly against held-out results; use a separate validation set for iteration.
10. Store reports with model, tokenizer, dataset and configuration hashes.

Acceptance criteria: scorer receives actual model predictions through a tested adapter; evaluation is reproducible and read-only; baselines and model results are separate; no evaluation data enters training.

## Stage 10 — build the resumable training pipeline (not a training launch)

**Purpose:** prove orchestration and recovery before using real compute.

Tasks:
- Audit training scripts/notebooks, checkpoint, storage, recovery and provider-diagnostic code.
- Separate dry-run, smoke-test, prototype-validation and real-training modes. Real training is disabled by default.
- Define an immutable run manifest: model/config/tokenizer/dataset versions, seed, optimizer, scheduler, batch size, sequence length, precision and code revision.
- Define checkpoint contents: model and optimizer state, scheduler state, step/epoch, RNG state, data sampler position, manifest and integrity hashes.
- Make checkpoint writes atomic and validate before marking a save complete.
- Test interruption/resume, interruption during save, corruption, partial upload, incompatible manifests and duplicate resume requests.
- Make retries idempotent so they cannot start concurrent jobs for one run.
- Ensure dashboard states distinguish queued, starting, running, saving, paused, failed, completed and unknown.
- Make server handoff explicit: a new runner verifies its environment, retrieves the latest valid checkpoint, checks hashes/config compatibility and resumes from the recorded step.
- Test portability between compatible CPU/GPU environments where supported.
- Add timeouts, cancellation, graceful shutdown and disk-space checks.
- Do not claim cross-provider recovery until an end-to-end recovery test proves it.
- Keep provider credentials server-side with least privilege.

Acceptance criteria: prototype validation cannot silently enter real-training mode; checkpoint integrity/atomic-save/resume tests pass; duplicate-run prevention and cancellation are tested; a controlled interrupted/resumed test succeeds without changing production weights.

## Stage 11 — validate free compute providers and dashboard control

**Purpose:** make remote execution realistic and compatible with the $0 constraint.

Tasks:
- Inventory only providers currently available under published free tiers and terms. Do not assume historical quotas still exist.
- Exclude providers or setup paths the owner rejected. Do not require a phone number or verification method the owner has said they will not use.
- Record accelerator/CPU, RAM/VRAM, storage, session duration, idle timeout, network restrictions, runtime support and checkpoint-transfer method.
- Run bounded environment diagnostics that report actual resources; do not infer them from a UI slider.
- Confirm a small validation workload runs without payment, card entry or quota circumvention.
- Implement an adapter only for a provider that passes review.
- Show availability, last successful check, measured resources, constraints and next action in the dashboard. Label stale/unavailable information.
- Implement safe queueing and handoff. Provider failure must not corrupt the last good checkpoint.
- Test expired sessions, quota exhaustion, disconnections, storage failures and provider unavailability.
- Do not promise continuous or simultaneous use of all free servers. Provider quotas and terms govern availability.

Acceptance criteria: at least one approved free execution path passes an end-to-end bounded test; measured resource limits are timestamped; no paid resource is enabled; provider failure preserves the last verified checkpoint.

## Stage 12 — final pre-training readiness review

**Purpose:** prevent an unrepeatable first run or damage to the only valid checkpoint.

Every gate must pass:

| Gate | Required evidence |
|---|---|
| Website | Required dashboard flows pass; mobile/iPad and Chromium/WebKit status documented |
| Security | Account-free public UI exposes no privileged controls; no public secret exposure; any future privileged endpoint has a separately reviewed fail-closed boundary |
| Math correctness | Typed parser and supported deterministic solvers pass regression/adversarial tests |
| Proof kernel | Enabled rules and axiom mappings are documented and tested; limitations are explicit |
| Diagnosis | Only validated steps produce confirmed error classifications |
| Data | Approved, versioned corpus passes independent validation and leakage checks |
| Evaluation | Frozen held-out set is isolated; inference adapter and scorer are reproducible |
| Model | Architecture, tokenizer, parameter count, initialization and resource profile are verified |
| Training code | Dry-run, tiny smoke test, checkpoint integrity and resume tests pass |
| Compute | At least one approved free runner passes bounded environment and recovery tests |
| Operations | Monitoring, cancellation, failure handling and logs work; any future remote controls remain disabled until separately reviewed and authorized |
| Cost and policy | $0 path verified; provider terms and quotas respected |
| Documentation | README, runbook, model card and dataset manifest match exact code/config versions |

Produce a readiness report tied to exact commit and artifact hashes. Any failed or unknown gate blocks launch. Passing the gates does **not** itself authorize training.

## Stage 13 — final stage: first real ULTRON training run

**This is the final pre-training milestone.** It begins only after Stage 12 is fully green and the owner gives explicit, separate authorization for a specific run.

Execution sequence:
1. Freeze the reviewed code revision, model configuration, tokenizer, approved dataset version, evaluation version and run manifest.
2. Verify that the model is freshly initialized from random weights. Confirm no pretrained weights or external checkpoints are loaded.
3. Verify that training excludes validation and held-out evaluation data.
4. Run a final dry-run that prints the exact planned configuration, data source, output destination, compute provider, resource limits and stopping conditions.
5. Present the run summary for owner approval. Do not infer approval from approval of a code PR, readiness report or earlier discussion.
6. After approval, start one bounded run with explicit maximum steps/time/resource limits and frequent safe checkpoints.
7. Monitor loss, throughput, memory, gradient health, checkpoint integrity, runner status and data-loader errors. Stop safely on NaN/Inf, corrupted data, repeated OOM, unexpected cost, unauthorized configuration drift or loss of checkpoint integrity.
8. On interruption, use the tested recovery path and verify restored manifest/checkpoint hashes before resuming.
9. Save the final checkpoint atomically and record run manifest, logs, metrics and code/data/config hashes.
10. Evaluate the checkpoint on the frozen held-out suite using the read-only inference adapter. Compare with the pre-training baseline and report topic-level performance and failure modes.
11. Do not claim ULTRON is capable or complete merely because the training loop finished. Report actual metrics, limitations, regressions and whether another iteration is justified.
12. Update the model card, training record, README status and next-step handoff. Preserve traceability to the random initialization and pre-training artifacts.

**Definition of “first training run complete”:** an owner-authorized run executed on an approved free runner, saved a verifiable checkpoint, passed integrity/recovery checks and produced a reproducible held-out evaluation report. A dashboard mock state, dry-run, prototype test, generated dataset or successful notebook launch does not meet this definition.

## After the first run — measured improvement cycle

The first run is not proof that the project is finished. Use held-out results to identify weaknesses, but use only separate training/validation data to make changes. Improve one measured weakness at a time: data coverage, tokenizer representation, curriculum, optimization, model architecture or inference. Version every change, repeat relevant gates and preserve prior checkpoints/reports. Every subsequent real training run also requires explicit owner authorization.

## Current next-chat starting point

1. Start at **Stage 0** and inspect the latest repository state and open PRs. Do not assume the earlier README PR is still mergeable.
2. Reconcile this roadmap with current code and technical documentation.
3. Choose one small, verifiable task from the earliest incomplete stage. Website, security, proof and data readiness take priority over training.
4. Do not jump to Stage 13. The neural model remains untrained until every readiness gate passes and the owner explicitly authorizes the first real run.
