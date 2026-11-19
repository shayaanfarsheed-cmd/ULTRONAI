from __future__ import annotations

import hashlib
import json
import re
from collections import defaultdict
from typing import Any, Mapping, Sequence

import torch

from ultron_data import SUPPORTED_TOPICS
from ultron_training import generate_completion


# Hand-authored questions and answers. These intentionally use wording that
# the synthetic training generator does not emit. Never add these records to
# a training or curriculum dataset.
_HELD_OUT_ROWS = (
    ("whole_number_arithmetic", 1, "Find the value of 18 + 24.", "42"),
    ("whole_number_arithmetic", 2, "Find the difference between 96 and 38.", "58"),
    ("fractions", 2, "Calculate (3/4) - (1/6).", "7/12"),
    ("decimals", 2, "Find the sum of 4.08 and 3.7.", "7.78"),
    ("percentages", 2, "What is 12% of 150?", "18"),
    ("ratios_and_proportions", 2, "Simplify the ratio 42:56.", "3:4"),
    ("integers", 2, "Evaluate negative fifteen plus nine.", "-6"),
    ("order_of_operations", 2, "Use order of operations: 9 + 4 * 6.", "33"),
    ("pre_algebra", 2, "Find x when x + 14 = 31.", "x = 17"),
    ("linear_equations", 2, "Solve for x: 5*x + 8 = 33.", "x = 5"),
    ("inequalities", 2, "Find all x such that 3*x + 2 < 17.", "x < 5"),
    ("exponents_and_roots", 2, "What is 9 squared?", "81"),
    ("basic_geometry", 2, "A rectangle has length 9 and width 6. Find its area.", "54"),
    ("basic_statistics", 2, "Find the mean of 5, 10, and 15.", "10"),
    ("basic_probability", 2, "There are 5 favorable outcomes out of 20. Find the probability.", "1/4"),
    ("whole_number_arithmetic", 3, "Find the product of 127 and 8.", "1016"),
    ("fractions", 1, "Calculate (1/2) + (1/3).", "5/6"),
    ("fractions", 3, "Calculate (7/8) / (14/15).", "15/16"),
    ("decimals", 1, "Find the sum of 1.25 and 2.5.", "3.75"),
    ("decimals", 3, "Find the difference between 19.75 and 8.625.", "11.125"),
    ("percentages", 1, "What is 25% of 80?", "20"),
    ("percentages", 3, "What is 17% of 250?", "42.5"),
    ("ratios_and_proportions", 1, "Simplify the ratio 18:24.", "3:4"),
    ("ratios_and_proportions", 3, "Simplify the ratio 144:96.", "3:2"),
    ("integers", 1, "Evaluate negative eight plus three.", "-5"),
    ("integers", 3, "Evaluate negative twelve multiplied by negative seven.", "84"),
    ("order_of_operations", 1, "Use order of operations: 4 + 3 * 5.", "19"),
    ("order_of_operations", 3, "Use order of operations: 18 + 7 * 12.", "102"),
    ("pre_algebra", 1, "Find x when x + 7 = 19.", "x = 12"),
    ("pre_algebra", 3, "Find x when x - 18 = -7.", "x = 11"),
    ("linear_equations", 1, "Solve for x: 3*x + 5 = 20.", "x = 5"),
    ("linear_equations", 3, "Solve for x: 12*x + -17 = 55.", "x = 6"),
    ("inequalities", 1, "Find all x such that 2*x + 3 < 11.", "x < 4"),
    ("inequalities", 3, "Find all x such that 7*x + -5 > 30.", "x > 5"),
    ("exponents_and_roots", 1, "What is 12 squared?", "144"),
    ("exponents_and_roots", 3, "What is the square root of 225?", "15"),
    ("basic_geometry", 1, "A rectangle has length 12 and width 7. Find its area.", "84"),
    ("basic_geometry", 3, "A rectangle has length 18 and width 11. Find its perimeter.", "58"),
    ("basic_statistics", 1, "Find the mean of 2, 4, and 6.", "4"),
    ("basic_statistics", 3, "Find the mean of 10, 20, 30, and 40.", "25"),
    ("basic_probability", 1, "There are 3 favorable outcomes out of 8. Find the probability.", "3/8"),
    ("basic_probability", 3, "There are 18 favorable outcomes out of 24. Find the probability.", "3/4"),
)

HELD_OUT_EVALUATION_SET: tuple[dict[str, Any], ...] = tuple(
    {
        "sample_id": f"heldout-{index:03d}",
        "topic": topic,
        "difficulty": difficulty,
        "question": question,
        "answer": answer,
        "split": "held_out",
        "evaluation_only": True,
    }
    for index, (topic, difficulty, question, answer) in enumerate(_HELD_OUT_ROWS, start=1)
)

DEFAULT_EVALUATION_SEED = 20261119
DEFAULT_MAX_NEW_TOKENS = 64


def evaluation_set_fingerprint(examples: Sequence[Mapping[str, Any]] = HELD_OUT_EVALUATION_SET) -> str:
    """Stable SHA-256 fingerprint for the fixed evaluation records."""
    rows = [
        (str(item["topic"]), int(item["difficulty"]), str(item["question"]), str(item["answer"]))
        for item in examples
    ]
    payload = json.dumps(rows, ensure_ascii=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def validate_evaluation_set(examples: Sequence[Mapping[str, Any]] = HELD_OUT_EVALUATION_SET) -> None:
    if not examples:
        raise ValueError("Evaluation set must not be empty")
    seen: set[str] = set()
    for item in examples:
        if item.get("topic") not in SUPPORTED_TOPICS:
            raise ValueError("Evaluation example has an unsupported topic")
        if type(item.get("difficulty")) is not int or item["difficulty"] not in (1, 2, 3):
            raise ValueError("Evaluation difficulty must be 1, 2 or 3")
        question = item.get("question")
        answer = item.get("answer")
        if not isinstance(question, str) or not question.strip():
            raise ValueError("Evaluation question must be non-empty text")
        if not isinstance(answer, str) or not answer.strip():
            raise ValueError("Evaluation answer must be non-empty text")
        normalized = " ".join(question.casefold().split())
        if normalized in seen:
            raise ValueError("Evaluation questions must be unique")
        seen.add(normalized)
        if item.get("evaluation_only") is not True or item.get("split") != "held_out":
            raise ValueError("Evaluation examples must be marked evaluation-only and held-out")


def _extract_answer(completion: str) -> str | None:
    match = re.search(r"(?:^|\n)Answer:\s*([^\r\n]+)", completion)
    return match.group(1).strip() if match else None


@torch.no_grad()
def evaluate_model(
    model: torch.nn.Module,
    tokenizer: Any,
    device: str | torch.device = "cpu",
    examples: Sequence[Mapping[str, Any]] = HELD_OUT_EVALUATION_SET,
    maximum_new_tokens: int = DEFAULT_MAX_NEW_TOKENS,
) -> dict[str, Any]:
    """Evaluate exact-answer generation without gradients or optimizer updates."""
    validate_evaluation_set(examples)
    if type(maximum_new_tokens) is not int or maximum_new_tokens < 1:
        raise ValueError("maximum_new_tokens must be a positive integer")

    resolved = torch.device(device)
    model.to(resolved)
    was_training = model.training
    model.eval()
    by_topic: dict[str, list[dict[str, Any]]] = defaultdict(list)
    by_difficulty: dict[str, list[dict[str, Any]]] = defaultdict(list)
    records: list[dict[str, Any]] = []
    try:
        for item in examples:
            completion = generate_completion(
                model,
                tokenizer,
                str(item["question"]),
                int(model.context_length),
                resolved,
                maximum_new_tokens=maximum_new_tokens,
            )
            predicted = _extract_answer(completion)
            correct = predicted == str(item["answer"]).strip()
            record = {
                "sample_id": item["sample_id"],
                "topic": item["topic"],
                "difficulty": item["difficulty"],
                "expected": item["answer"],
                "predicted": predicted,
                "correct": correct,
                "parse_failed": predicted is None,
            }
            records.append(record)
            by_topic[str(item["topic"])].append(record)
            by_difficulty[str(item["difficulty"])].append(record)
    finally:
        model.train(was_training)

    def summarize(groups: Mapping[str, Sequence[Mapping[str, Any]]]) -> dict[str, dict[str, int | float]]:
        summary: dict[str, dict[str, int | float]] = {}
        for key, items in sorted(groups.items()):
            total = len(items)
            correct = sum(bool(item["correct"]) for item in items)
            parse_failures = sum(bool(item["parse_failed"]) for item in items)
            summary[key] = {
                "correct": correct,
                "total": total,
                "accuracy": correct / total if total else 0.0,
                "parse_failures": parse_failures,
            }
        return summary

    total = len(records)
    correct = sum(bool(item["correct"]) for item in records)
    topic_metrics = summarize(by_topic)
    return {
        "status": "complete",
        "evaluation_name": "ULTRON fixed held-out mathematics evaluation",
        "evaluation_version": "2026-11-19-v1",
        "evaluation_fingerprint": evaluation_set_fingerprint(examples),
        "evaluation_only": True,
        "training_started": False,
        "model_weights_changed": False,
        "optimizer_used": False,
        "parameter_count": sum(parameter.numel() for parameter in model.parameters()),
        "sample_count": total,
        "correct_count": correct,
        "incorrect_count": total - correct,
        "parse_failure_count": sum(bool(item["parse_failed"]) for item in records),
        "accuracy": correct / total if total else 0.0,
        "macro_topic_accuracy": (
            sum(float(item["accuracy"]) for item in topic_metrics.values()) / len(topic_metrics)
            if topic_metrics else 0.0
        ),
        "by_topic": topic_metrics,
        "by_difficulty": summarize(by_difficulty),
        "results": records,
    }
