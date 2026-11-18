# ULTRONAI Work Package 1 — Repository Repair Audit

**Audit date:** 2026-11-18  
**Audit base:** `main` at `397f1492c300371821b2651ddfbc7342adc9f60c`  
**Working branch:** `repair/work-package-1-repository-architecture`  
**Scope:** inspection only; this audit does not authorize Supabase changes, authentication deployment, device pairing, training, or merging.

## Verified GitHub baseline

- Repository: `shayaanfarsheed-cmd/ULTRONAI`
- `main` resolves to `397f1492c300371821b2651ddfbc7342adc9f60c`.
- PR #4 is open and unmerged: [Define secure ULTRON device control contract](https://github.com/shayaanfarsheed-cmd/ULTRONAI/pull/4).
- PR #4 head: `6fa27729b657c43719fe5955b3f1b2d609720659`; base: `main` at `397f1492c300371821b2651ddfbc7342adc9f60c`.
- PR #4 latest-head CI runs observed: Test Suite `44218633547`, Preflight `44218633560`, Training Prototype Validation `44218633551`; all three completed successfully.
- No merge, production Supabase operation, credential change, pairing, or training was performed during this audit.

## File-by-file findings and repair plan

| File | Verified issue | Work Package 1 action |
|---|---|---|
| `README.md` | Opening text still describes a Windows-only agent and an older no-login product. Later sections instruct users to create a normal Supabase Auth account and imply the website is already configured for signed-in access. Several handoff sections conflict. | Establish one current authoritative status/handoff; describe one owner account plus Guest Mode as the target, clearly mark it not implemented, remove Windows-only assumptions, and state that legacy setup instructions must not be followed. |
| `supabase/SETUP.md` | Contains public self-registration instructions, says dashboard auth is ready, and gives Kaggle secret/setup instructions. This conflicts with restricted single-owner provisioning and the user's decision not to use Kaggle. | Rewrite as a staged, non-executable setup guide. No account creation, migration, RLS/grant, secret, or production setting changes until separately approved. Remove Kaggle as an active provider path. |
| `docs/LOCAL_AGENT_ARCHITECTURE.md` | Command flow assumes every user signs in; platform/resource sections need to consistently distinguish desktop workers from iPad/mobile browser clients. | Document owner-only control versus public Guest Mode, device-generic terminology, OS-specific enforcement adapters, and fail-closed eligibility. |
| `config.json` | Project stage metadata is stale; local memory enforcement is hard-coded as `windows_job_object`; no machine-readable owner/guest access contract exists. Sequence length remains 192. | Add explicit product-access policy and platform enforcement capability map. Keep sequence length unchanged until model/context compatibility is separately tested. |
| `servers.json` | Kaggle remains enabled and appears first, despite the user's explicit decision not to use Kaggle. | Disable Kaggle for selection; preserve the record only as a disabled provider entry so old IDs/config references do not silently break. |
| `dashboard/app.js` | `publicMode` is permanently true; initialization sets user/session to null. Auth helpers exist but are not connected to a real login/owner experience. The dashboard does not load private owner data. | Do not pretend owner authentication exists. Keep Guest Mode safe. Owner login is a later package; backend authorization must precede enabling controls. |
| `dashboard/index.html` | Device page says “Sign in here” although there is no sign-in UI. Several controls are deliberately disabled; overview contains legacy training control surfaces. | Correct misleading wording in the dashboard package after its interaction inventory; do not enable privileged controls in this documentation/config package. |
| `dashboard/config.js` | Supabase publishable key is a placeholder. | Leave placeholder intact; do not request or commit secrets. A publishable key is not owner authorization. |
| `tests/test_config.py` | Validates JSON and existing training/provider invariants but not owner/guest policy or disabled provider rules. | Add regression tests for new config invariants. Do not claim these tests implement runtime authorization. |
| `.github/workflows/test-suite.yml` | Validates JSON, JavaScript syntax, compilation and tests. | Preserve; run on the new PR head. |
| `.github/workflows/preflight-tests.yml` | Installs only numpy/safetensors on `main`; PR #4 adds JSON Schema validation dependency only on its separate branch. | Keep PR #4 unmerged and separate. Reconcile dependency ownership after the contract PR decision; avoid duplicate or conflicting dependency edits. |
| `requirements.txt` | Contains numpy, safetensors and Hugging Face Hub; no development dependency split. | Avoid removing packages without usage evidence. Check imports before any dependency removal. |
| `train.py` / `ultron_supabase.py` / `train.ipynb` | Training worker still expects backend secret and `SUPABASE_OWNER_ID`; this is not the same as a browser owner session and must remain server-side. Notebook references provider secrets. | Document the distinction. Never move backend secrets into browser config or notebook output. Do not start training. |

## Configuration decisions

1. **Owner account:** exactly one intended owner identity; secure login/logout, recovery and session lifecycle are future implementation work. Public self-registration must remain disabled.
2. **Guest Mode:** public dashboard and public mathematics information only. Guests receive no private history, checkpoints, pairing, or remote training controls.
3. **Backend authorization:** hiding controls is not authorization. Owner identity must be derived from verified server-side identity; never trust a browser-supplied owner ID.
4. **Budget:** $0; no paid services, payment methods, paid trials, or quota bypass.
5. **Training:** no live training until the user separately approves it.
6. **Kaggle:** disabled as a provider because the user declined Kaggle. Do not launch jobs or configure Kaggle credentials.
7. **RAM:** dashboard slider is currently a browser-local preference, not an OS-enforced cap. Platform-specific enforcement must be proven before training is eligible.
8. **Context length:** current config says 192. The earlier 1024-token requirement is unresolved; do not change the model or config until parameter count, positional/context handling, memory and checkpoint compatibility are tested.
9. **PR #4:** remains open/unmerged and is not silently incorporated into this branch. Its contract changes are separate and its latest-head CI passed at the time of this audit.

## Ordered implementation checklist

- [x] Verify main and PR #4 state.
- [x] Inspect README, account/setup docs, agent architecture, dashboard entry points, config, provider registry, dependencies and workflows.
- [x] Create this file-by-file repair audit.
- [x] Update README with the authoritative product architecture and this handoff.
- [x] Rewrite conflicting setup and device-agent documentation.
- [x] Add machine-readable access and platform-enforcement policy to config.
- [x] Disable Kaggle in provider registry and add regression tests.
- [ ] Run JSON validation, Python unit tests, compile checks, JavaScript syntax checks and all CI workflows on the exact PR head.
- [x] Review changed-file inventory and open PR #10; final review remains subject to exact-head CI. Do not merge without explicit approval.

## Explicitly not done

No owner account was created. No auth UI was implemented. No Supabase schema, RLS, grants, Edge Functions, production secrets or live settings were changed. No device was paired. No agent was installed. No training or cloud provider job was started. No PR was merged.
