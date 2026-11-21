# ULTRON

**ULTRON is an independently developed, mathematics-focused learning system.** Its long-term goal is to train a small transformer from random initialization using project-generated, independently checked mathematics data. The project also contains a browser-based mathematics tutor and a deterministic formal proof checker.

> **Current status (21 November 2026):** The website, deterministic mathematics tools and a growing formal proof kernel are implemented. The neural model exists but is **untrained**. Real model training has not started.

- **Live dashboard:** [Open ULTRON Training Control](https://shayaanfarsheed-cmd.github.io/ULTRONAI/)
- **Repository:** [shayaanfarsheed-cmd/ULTRONAI](https://github.com/shayaanfarsheed-cmd/ULTRONAI)
- **Formal proof-kernel specification:** [docs/FORMAL_PROOF_KERNEL.md](docs/FORMAL_PROOF_KERNEL.md)
- **Reasoning architecture:** [docs/CONVERSATIONAL_REASONING_ARCHITECTURE.md](docs/CONVERSATIONAL_REASONING_ARCHITECTURE.md)
- **Axiom Bank research:** [docs/AXIOM_BANK_RESEARCH.md](docs/AXIOM_BANK_RESEARCH.md)

## What works today

### Browser dashboard and mathematics tutor

The GitHub Pages site is designed for desktop, mobile and iPad-sized screens. Public dashboard browsing does not require an account. Private operations remain owner-gated.

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

The kernel checks typed expressions, exact axiom identifiers, formal-system boundaries, inference rules, proof dependencies and schema use. It rejects malformed proof structures and unsupported derivations.

Implemented foundations include:
- Peano successor arithmetic and a dedicated induction schema.
- The nine researched real-field axiom entries.
- Euclidean construction and parallel-postulate relations.
- Probability non-negativity, sample-space normalization and countable additivity.
- ZFC finite axioms currently represented in the kernel, plus dedicated separation and replacement schema rules.

The ZFC choice axiom is not yet implemented as an executable rule. The ordered-field and complete-real contexts are declared but do not yet have their own executable axiom systems. See the formal-kernel specification for exact coverage and limitations.

The proof kernel is **not** a general theorem prover, does not establish consistency of its axioms, and does not prove that the neural model has learned mathematics.

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
- Do not start real training until readiness checks pass and the owner explicitly authorizes it.

The dashboard's RAM slider is a **browser-local preference**. It does not set the memory limit of a remote runner or control GPU VRAM. Device/browser memory monitoring is not equivalent to enforced training-process limits.

Public visitors can browse the dashboard. Owner authentication is required for private training operations and private records. Browser-side checks are not a substitute for server-side authorization.

## Current development priorities

Work should proceed in small, independently testable increments:

1. Finish and verify the website experience on physical iPad and mobile devices, in addition to automated Chromium and WebKit tests.
2. Complete the live security checks for owner-only operations, invalid/expired authentication, non-owner denial and secret non-disclosure.
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

**Next task:** continue the formal proof-kernel work in small chunks. First inspect the current open pull request and its exact diff, then address one review or validation issue at a time. Preserve existing ZFC separation/replacement work and the typed probability-order change; do not recreate or overwrite already merged work.

**Training state:** not started. No training run is authorized by this README update.
