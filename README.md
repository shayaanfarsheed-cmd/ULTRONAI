# ULTRON Training Control

ULTRON is an independently implemented mathematics Transformer training project. It starts from random weights, generates its own deterministic mathematics data, verifies examples independently, and does not use pretrained models, pretrained weights, AI APIs, or paid compute.

## Online website-controlled local training

The selected hosting is GitHub Pages. The intended workflow is an online dashboard on GitHub Pages, Supabase for authenticated control and coordination, and a Windows local agent that makes outbound HTTPS connections and starts the fixed ULTRON training entry point only after local preflight and lease checks. This allows an iPad browser to control a paired Windows computer without exposing an inbound port.

The architecture and security contract is documented in [`docs/LOCAL_AGENT_ARCHITECTURE.md`](docs/LOCAL_AGENT_ARCHITECTURE.md). This is a design specification only: the Windows agent and Run/Pause/Resume/Stop integration have not yet been implemented, and training has not started.

## Local RAM budget control

The dashboard Settings page now includes a 2–10 GB RAM budget slider (0.5 GB increments), defaulting to 6 GB for the 16 GB Windows laptop. The selected value is currently saved only in the browser where it is changed. It is a preference preview, **not an enforced process limit yet**. The Windows agent must be implemented to receive the setting and enforce it with a Windows Job Object before training can start. See [the local-agent architecture](docs/LOCAL_AGENT_ARCHITECTURE.md).

## Browser dashboard

The static dashboard is in `dashboard/`. The repository root redirects to it.

## Current status — 2026-11-18 (PR #8 handoff)

**This section supersedes older operational and handoff notes below wherever they conflict.**

- **Repository:** `shayaanfarsheed-cmd/ULTRONAI`
- **Active branch:** `ui/public-dashboard-no-personal-history`
- **Pull request:** [#8 — Remove public read-only messaging and personal training history](https://github.com/shayaanfarsheed-cmd/ULTRONAI/pull/8)
- **PR head before this fix:** `cf76192bb030cb55e53a8aacc7c260790f5eb5ed`
- **Frontend cleanup commit:** `207b3331dd300583fd6adbe5c9bd7206ad181e09` — removes the obsolete history renderer and owner-ID DOM reference.
- **PR state:** open and unmerged. Do not merge without the user's explicit approval.

### User-facing dashboard requirements

- The dashboard is public; no login or sign-up is required.
- Do not collect, load, cache, or display account-specific training history.
- Do not display a public-read-only-mode label or warning.
- Checkpoint access, device pairing, and training controls remain unavailable/locked. Do not enable them as part of this UI cleanup.
- No live training or provider jobs have been started. No backend schema or secrets were changed.

### PR #8 CI failure diagnosis

GitHub Actions runs reported failing on 2026-11-18:

- Preflight: run `44213979810`, job `134499064277`
- Test suite: run `44213979643`, job `134499063447`
- Training prototype validation: run `44213979639`, job `134499063456`

All three failed at the same unit test, `test_all_static_javascript_id_references_exist`. The dashboard HTML had removed the personal history and owner-ID elements while `dashboard/app.js` still contained unused references to `switchCount`, `sessionCount`, `switchHistoryBody`, `sessionHistoryBody`, and `ownerIdText`. This was a stale frontend reference issue; later smoke steps were skipped. The first fix removes the obsolete history renderer and owner-ID DOM reference rather than restoring the removed UI.

**Validation status:** the original three runs failed on the stale DOM references. The frontend cleanup commit above is now on the PR branch. Fresh workflows triggered for that commit: test suite run `44214532032`, prototype validation run `44214532537`, and preflight run `44214531838`; all were `in_progress` at the last check. A README handoff-only follow-up commit is also being made and may trigger another CI set. Fetch the latest PR head and confirm its checks before calling this fixed. Do not claim success until all latest-head runs complete green.

### Exact next steps for the next chat

1. Read this current-status section first. Fetch the latest PR #8 head SHA; the README-only handoff commit may have advanced it beyond the frontend cleanup commit recorded above.
2. Inspect `dashboard/app.js` and ensure public mode never queries, stores, or renders account-specific logs, switch requests, owner IDs, or personal checkpoint history. Remove obsolete unreachable account/history code where safe; preserve public system/server information.
3. Run `node --check dashboard/app.js`, the dashboard static tests, and the complete Python unit suite locally or through CI.
4. Verify checkpoint verification, device pairing, automatic starts, and all training controls remain disabled in the public dashboard.
5. Inspect fresh CI runs for the updated PR head. Fix failures and rerun; do not bypass tests.
6. Keep PR #8 open and unmerged until the user explicitly approves merging.
7. Before ending any future chat/context handoff, update this README again with the actual branch, latest commit SHA, PR state, CI results, and next exact actions.



Before the dashboard can sign in, edit `dashboard/config.js` and replace `sb_publishable_REPLACE_WITH_YOUR_KEY` with the Supabase publishable/anon key for the `ultron-memory` project. This key is public by design. Never put an `sb_secret_...` key in this file.

To publish with GitHub Pages:

1. Open the repository **Settings → Pages**.
2. Choose **Deploy from a branch**.
3. Select branch `main` and folder `/(root)`.
4. Save and wait for the Pages deployment.
5. Open `https://shayaanfarsheed-cmd.github.io/ULTRONAI/`.

The dashboard requires `training_api` to be the only exposed Data API schema. Follow `supabase/SETUP.md` before signing in.

## Provider secrets

Add these values to each provider's secret manager, never to source files or notebook cells:

- `SUPABASE_URL`
- `SUPABASE_SECRET_KEY` (current `sb_secret_...` key)
- `SUPABASE_OWNER_ID` (your Supabase Auth user UUID)

The dashboard uses only the publishable/anon key and the signed-in user's JWT. The notebook and switcher use the backend secret.

## Training entry points

- `train.ipynb`: browser notebook launcher for Kaggle, Colab and other notebook platforms.
- `train.py`: shared training entry point.
- `ultron_model.py`: model architecture.
- `ultron_data.py` and `ultron_verify.py`: deterministic mathematics generation and independent verification.
- `ultron_checkpoint.py`: local atomic checkpoint creation and verification.
- `ultron_storage.py`: private Supabase checkpoint upload and recovery.
- `ultron_supabase.py`: status, lease, heartbeat and checkpoint database client.
- `ultron_session.py`: training session orchestration.
- `ultron_switcher.py`: guided and allowlisted automatic server selection.

## Current operational limits

- The database-side lease functions and private bucket are installed in Supabase.
- The dashboard source is committed, but GitHub Pages still needs to be enabled and the publishable key added to `dashboard/config.js`.
- A Supabase Auth user must be created before the notebook can create a run.
- The notebook has not yet been run on the user's live Kaggle, Colab or Lightning accounts.
- Secondary Hugging Face checkpoint backup and ONNX release are not yet complete.
- Provider account quota and GPU availability must be checked in each provider account.

## Automated tests

The repository test workflow runs on pushes and pull requests. It checks the Python modules, deterministic data generator, model, checkpoint recovery, Supabase lease client, dashboard JavaScript, JSON configuration and notebook structure.

For a browser-free local validation environment with Python 3.11 and CPU PyTorch installed:

```bash
python -m pip install -r requirements.txt
python -m unittest discover -s tests -v
python train.py --preflight --model-summary --data-smoke-test --checkpoint-smoke-test --training-smoke-test
node --check dashboard/app.js
node --check dashboard/config.js
```

## Current development status and next-chat handoff

**Last updated:** 2026-11-17 13:35 UTC  
**Repository:** `shayaanfarsheed-cmd/ULTRONAI`  
**Working branch:** `main`  
**Latest commit at handoff:** `7950a9b2eab54fe3584dd8c2a3823011d232b357` — "Add verified secondary backup fallback and retry pending primary commits"

This section is the source of truth for continuing work in a new ChatGPT conversation. Read it before editing files. Continue from the existing code; do not rebuild the project or repeat completed work.

### Overall objective and non-negotiable rules

Build ULTRON as a 3–5 million parameter mathematics Transformer trained from random initialization, using only its own deterministic math-data generator and independent verifier. No pretrained models, pretrained weights, AI APIs, paid compute, or user's laptop. The user works from an iPad/browser. Keep the training workflow resumable across free cloud providers, with a browser dashboard and Supabase coordination.

Work in small stages. Inspect files before editing. After every change, run the relevant tests and then the full suite. Never say a test passed unless its result was actually observed. Do not start live model training or ask the user to paste secrets into chat.

### What already exists

- `servers.json`: editable provider order, links, hardware and provider-limit metadata.
- `config.json`: editable training, model, checkpoint, heartbeat, quota, coordination and dashboard settings.
- `train.py` and `train.ipynb`: common training entry points.
- `ultron_model.py`: from-scratch Transformer; configured and measured at 4,038,478 parameters.
- `ultron_data.py` and `ultron_verify.py`: deterministic math generation and separate verification.
- `ultron_checkpoint.py`: local checkpoint creation, checksums and recovery.
- `ultron_storage.py`: Supabase checkpoint storage plus the newly added private Hugging Face backup store.
- `ultron_supabase.py`: Supabase status, heartbeat, lease/fencing and checkpoint coordination.
- `ultron_session.py`: training loop and session orchestration.
- `ultron_switcher.py`: server selection and switching logic.
- `dashboard/`: static browser dashboard.
- `supabase/`: SQL/setup material and backend configuration.
- `tests/`: automated tests.
- GitHub Actions workflow: runs repository checks on supported pushes and pull requests.

The Supabase database-side lease functions and private checkpoint bucket were previously installed. Confirm live schema, policies and bucket settings before changing them.

### Work completed immediately before this handoff

The current task is **secondary checkpoint backup and recovery**. The following changes have been committed to `main`:

1. Added `huggingface_hub` to `requirements.txt`.
2. Added `HuggingFaceCheckpointStore` to `ultron_storage.py`. It requires an existing private Hugging Face model repository, uploads immutable checkpoint folders, stores a manifest receipt, and verifies component sizes and SHA-256 hashes.
3. Added fake-provider tests for private Hugging Face upload/download round-trip and rejection of a public repository in `tests/test_storage.py`.
4. Added optional `HF_TOKEN` and `HF_REPO_ID` loading to the training setup. These must come from each platform's secret manager; never hard-code or print them.
5. Added settings for secondary backup cadence, backup-on-primary-failure, backup-on-handoff, and retention in `config.json`.
6. Integrated secondary backup candidate discovery and restore into `ultron_session.py`. If a secondary candidate is corrupt, startup should fall back to verified Supabase candidates.
7. Added retry handling for a checkpoint that has a verified secondary copy but whose Supabase commit failed.

Important commit sequence:
- `7bef22d95ae873f9e9b8305e90d8e0961a3bfc71` — add Hugging Face Hub dependency.
- `1675d07ba6b0556c96b70b9ba8708ac90f85a6ee` — add secondary-backup unit tests.
- `9b2a76c032ea3431c43e33798787c773c69bf425` — integrate backup restore into training startup.
- `8b141fd03f05f52997cbdf77a7ed4ac34480b9de` — fall back to Supabase if a secondary backup is corrupt.
- `7950a9b2eab54fe3584dd8c2a3823011d232b357` — retry pending primary commits and back up on primary failure.

### Test status — do not overstate

A previous GitHub Actions run, **before the latest Hugging Face integration**, reported 87/87 unit tests passing, plus Python compilation, dashboard JavaScript checks, JSON/notebook validation, model parameter-count checks, 100/100 generated math examples verified, checkpoint save/restore and CPU smoke tests.

The Hugging Face integration commits above were made after that run. A lookup for workflow runs on the latest commit returned no runs. Therefore:

- The previous 87-test result is historical and does **not** validate the latest changes.
- The two new Hugging Face tests have been added but are **not yet confirmed passing**.
- End-to-end training recovery from Hugging Face has **not yet been tested**.
- No real Hugging Face repository has been created or connected.
- No live Kaggle, Colab or Lightning training session has been run.
- Do not claim the system is production-ready.

### Exact next tasks — do these in order

1. **Review the new backup integration carefully.** Re-read the latest versions of `ultron_storage.py`, `ultron_session.py`, `tests/test_storage.py`, `train.py`, `train.ipynb`, `requirements.txt` and `config.json`. Check for import errors, incorrect API arguments, path handling, receipt/manifest mismatches, partial uploads and exception handling.
2. **Protect the one-writer lease.** A secondary backup is not permission to keep training after the Supabase lease/heartbeat has expired. If Supabase is unreachable, stop before the locally known lease deadline, do not let another worker overlap, and make the offline-recovery behaviour explicit and tested. Never extend a lease only in local memory. Verify fencing tokens before every primary checkpoint commit.
3. **Run the full CI test suite on the current `main` commit.** Run Python compilation, `python -m unittest discover -s tests -v`, the `train.py` preflight/model/data/checkpoint/training smoke tests, `node --check dashboard/app.js`, `node --check dashboard/config.js`, JSON parsing and notebook structure checks. Capture the actual result and fix failures before continuing.
4. **Add integration tests** for: restore from a newer verified Hugging Face checkpoint when Supabase's committed pointer is older; fallback to Supabase when the newest Hugging Face checkpoint is corrupt; retry a pending Supabase commit after a temporary outage; stop safely when the lease cannot be renewed; and refuse a stale fencing token.
5. **Review checkpoint retention and backup policy.** Supabase keeps the configured last three verified checkpoints. The Hugging Face backup currently uses `keep_all`; decide whether this is acceptable for free storage or implement safe retention only after a newer backup has been downloaded and verified. Never delete the only good copy.
6. **Re-run all tests after every fix**, then inspect the final GitHub Actions result. Update this README with the real test count, commit SHA and remaining limitations.
7. Only after the backup/recovery tests pass, continue the remaining dashboard deployment, provider setup and iPad handover work. Do not start training automatically.

### Secret setup for the optional secondary backup

The user must create a **private** Hugging Face model repository and add these two secrets in each provider's secret manager:

- `HF_TOKEN`: a Hugging Face token with write access to that private repository.
- `HF_REPO_ID`: repository identifier in `owner/repository` form.

These are optional until the private repository is configured. The Supabase backend secret remains in provider secret managers only. The website must never receive either secret. Do not request secret values in chat, commit them, print them, or include them in notebook outputs.

### Current operational state

- Dashboard source is committed; GitHub Pages still needs to be enabled and `dashboard/config.js` needs the Supabase publishable/anon key.
- A Supabase Auth user must exist before a live training run can be created.
- The user has an iPad and no laptop; all setup instructions must use browser interfaces.
- Live provider accounts, actual quotas, GPU availability, Hugging Face private storage, browser sign-in and cross-provider recovery still need user-side setup or live verification.
- Keep automatic starts disabled until platform policy, secrets and safety limits are verified. Guided switching must remain available.
