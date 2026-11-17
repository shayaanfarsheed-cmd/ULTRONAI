# ULTRON training prototype

This branch isolates validation of the existing from-scratch mathematics training engine before it is connected to the public dashboard or any provider automation.

## Scope

- Decoder-only Transformer initialized from random weights (no pretrained model or external AI API).
- Deterministic character tokenizer and project-generated mathematics examples.
- Independent arithmetic/example verification before examples are used.
- Prompt-masked causal language-model training.
- CPU/GPU runtime selection and optional mixed precision.
- Deterministic data-stream state and checkpoint save/restore.
- Curriculum progression gated by held-out evaluation.

## Safe validation

Run from the repository root:

```bash
python -m pip install torch --index-url https://download.pytorch.org/whl/cpu
python -m pip install -r requirements.txt
python -m unittest discover -s tests -v
python train.py --preflight --model-summary --data-smoke-test --checkpoint-smoke-test --training-smoke-test
```

The smoke test performs only two optimizer steps on a tiny generated sample. It is a test, not a long training run. It does not contact a provider, start a persistent session, use Supabase, or upload checkpoints.

## Acceptance gates

1. Configuration and provider registry pass validation.
2. Parameter count is between 3M and 5M and matches the configured architecture.
3. Generated training examples pass the independent verifier and train/validation/test questions do not overlap.
4. Forward/backward pass produces finite loss and updates parameters.
5. Checkpoint round-trip restores model/optimizer state exactly and verifies file hashes.
6. Resume restores data order, random state, scheduler and curriculum state.
7. CPU smoke test completes without credentials or network access to training data.

## Not enabled by this prototype

- No provider job launch or server rotation.
- No Supabase writes or device pairing.
- No dashboard control wiring.
- No automatic long-running training.
- No payment method, quota bypass, or secret stored in the repository.

A successful CI run validates software behavior on GitHub Actions CPU only. It does not prove that a free GPU provider is available, nor that the full model can train within a particular provider's session limit.
