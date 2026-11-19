from __future__ import annotations

import argparse
import json
import random
import sys

import torch

from ultron_evaluation import (
    DEFAULT_EVALUATION_SEED,
    DEFAULT_MAX_NEW_TOKENS,
    HELD_OUT_EVALUATION_SET,
    evaluate_model,
)
from ultron_model import CharTokenizer, ULTRONTransformer


def resolve_device(requested: str) -> str:
    if requested != "auto":
        return requested
    if torch.cuda.is_available():
        return "cuda"
    mps = getattr(getattr(torch.backends, "mps", None), "is_available", None)
    if callable(mps) and mps():
        return "mps"
    return "cpu"


def main() -> int:
    parser = argparse.ArgumentParser(description="Run ULTRON's fixed held-out evaluation (no training).")
    parser.add_argument("--device", choices=("auto", "cpu", "cuda", "mps"), default="auto")
    parser.add_argument("--seed", type=int, default=DEFAULT_EVALUATION_SEED)
    parser.add_argument("--limit", type=int, default=0, help="Evaluate only the first N questions (0 = all).")
    parser.add_argument("--max-new-tokens", type=int, default=DEFAULT_MAX_NEW_TOKENS)
    args = parser.parse_args()

    if args.limit < 0:
        parser.error("--limit cannot be negative")
    if args.max_new_tokens < 1:
        parser.error("--max-new-tokens must be positive")

    device = resolve_device(args.device)
    random.seed(args.seed)
    torch.manual_seed(args.seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(args.seed)

    tokenizer = CharTokenizer()
    model = ULTRONTransformer(vocab_size=tokenizer.vocab_size)
    model.to(device)
    examples = HELD_OUT_EVALUATION_SET[:args.limit] if args.limit else HELD_OUT_EVALUATION_SET
    report = evaluate_model(
        model,
        tokenizer,
        device=device,
        examples=examples,
        maximum_new_tokens=args.max_new_tokens,
    )
    report["seed"] = args.seed
    report["device"] = device
    report["model_initialization"] = "random"
    report["checkpoint_loaded"] = False
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
