# Seed dataset scanner

The approved seed source is `bkhtmm/openai-math-lemmas`, pinned to Hugging Face
revision `d7056fd31c19fd1a0aed0a0bc3e99026d412b2ca`.

## Stage 1: inventory only

The scanner reads task TOML/JSON metadata and hashes files. It does **not** import,
execute, build, or run any dataset-provided scripts, Lean files, shell files, or
Docker instructions. A successful scan means the expected directory structure and
metadata relationships are present; it does not mean the theorem proofs are valid.

From the repository root, run:

```sh
python ultron_seed_dataset.py "C:/Users/farsh/ultron_math_lemmas"
```

The default output is `dataset/seed/manifest.json`. The manifest contains task
identifiers, provenance fields, relative file paths, sizes, and SHA-256 hashes.
It does not copy the downloaded source files into this repository.

The initial expected task count is 47. The scanner fails closed on missing task
files, duplicate task/theorem identifiers, mismatched theorem lists, and symbolic
links. Python 3.11 or newer is required (for the standard-library TOML parser).

## Trust and validation boundaries

- The original downloaded dataset remains untouched.
- Reference solutions remain in the local source archive; they are not copied into
  generated training examples by this scanner.
- `validation_status = "unvalidated"` is preserved as metadata.
- Lean proof validation is a separate future stage and must use a pinned Lean/Mathlib
  environment and the independent Lean kernel.
- Do not start model training as part of dataset import.
