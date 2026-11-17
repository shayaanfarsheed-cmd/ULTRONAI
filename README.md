# ULTRON Training Control

ULTRON is an independently implemented mathematics Transformer training project. It starts from random weights, generates its own deterministic mathematics data, verifies examples independently, and does not use pretrained models, pretrained weights, AI APIs, or paid compute.

## Browser dashboard

The static dashboard is in `dashboard/`. The repository root redirects to it.

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
