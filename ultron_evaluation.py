from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any, Mapping, Sequence

from ultron_data import question_split

EVALUATOR_VERSION = "1.0.0"
DATASET_ID = "ultron-heldout-foundation-v1"
DEFAULT_DATASET_PATH = Path(__file__).resolve().parent / "evaluation" / "heldout_foundation_v1.json"


class EvaluationInputError(ValueError):
    """Raised when an evaluation dataset or prediction file is unsafe or invalid."""


def load_heldout_dataset(path: str | Path = DEFAULT_DATASET_PATH) -> dict[str, Any]:
    """Load and validate the frozen test fixture; never generate or alter examples."""
    try:
        payload = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise EvaluationInputError(f"Could not read evaluation dataset: {error}") from error

    if not isinstance(payload, dict):
        raise EvaluationInputError("Evaluation dataset must be a JSON object")
    if payload.get("schema_version") != 1 or payload.get("dataset_id") != DATASET_ID:
        raise EvaluationInputError("Unsupported evaluation dataset identity or schema")
    if payload.get("frozen") is not True:
        raise EvaluationInputError("Evaluation dataset must be explicitly frozen")

    examples = payload.get("examples")
    if not isinstance(examples, list) or not examples:
        raise EvaluationInputError("Evaluation dataset must contain examples")

    seen_ids: set[str] = set()
    seen_questions: set[str] = set()
    for index, example in enumerate(examples):
        if not isinstance(example, dict):
            raise EvaluationInputError(f"Example {index} must be an object")
        sample_id = example.get("sample_id")
        question = example.get("question")
        answer = example.get("answer")
        topic = example.get("topic")
        difficulty = example.get("difficulty")
        if not isinstance(sample_id, str) or not sample_id:
            raise EvaluationInputError(f"Example {index} has an invalid sample_id")
        if sample_id in seen_ids:
            raise EvaluationInputError(f"Duplicate sample_id: {sample_id}")
        if not isinstance(question, str) or not question.strip():
            raise EvaluationInputError(f"Example {sample_id} has an invalid question")
        if question in seen_questions:
            raise EvaluationInputError(f"Duplicate question in evaluation dataset: {question}")
        if not isinstance(answer, str) or not answer.strip():
            raise EvaluationInputError(f"Example {sample_id} has an invalid expected answer")
        if not isinstance(topic, str) or not topic:
            raise EvaluationInputError(f"Example {sample_id} has an invalid topic")
        if type(difficulty) is not int or difficulty not in (1, 2, 3):
            raise EvaluationInputError(f"Example {sample_id} has an invalid difficulty")
        if example.get("split") != "test" or question_split(question) != "test":
            raise EvaluationInputError(f"Example {sample_id} is not in the reserved test split")
        seen_ids.add(sample_id)
        seen_questions.add(question)

    return payload


def _normalize_answer(value: str) -> str:
    """Normalize whitespace only; do not silently equate different math expressions."""
    return " ".join(value.split())


def _group_metrics(rows: Sequence[Mapping[str, Any]], key: str) -> dict[str, dict[str, int | float]]:
    groups: dict[str, list[Mapping[str, Any]]] = {}
    for row in rows:
        groups.setdefault(str(row[key]), []).append(row)
    result: dict[str, dict[str, int | float]] = {}
    for label in sorted(groups):
        items = groups[label]
        correct = sum(bool(item["correct"]) for item in items)
        total = len(items)
        result[label] = {
            "correct": correct,
            "total": total,
            "accuracy": correct / total,
        }
    return result


def evaluate_predictions(
    dataset: Mapping[str, Any],
    predictions: Mapping[str, str],
    *,
    model_label: str | None = None,
) -> dict[str, Any]:
    """Score explicit predictions against a validated frozen fixture, without model mutation."""
    if not isinstance(dataset, Mapping) or dataset.get("dataset_id") != DATASET_ID:
        raise EvaluationInputError("A validated held-out foundation dataset is required")
    if dataset.get("schema_version") != 1 or dataset.get("frozen") is not True:
        raise EvaluationInputError("Evaluation dataset identity, schema, or frozen flag is invalid")
    trusted_examples = load_heldout_dataset()["examples"]
    examples = dataset.get("examples")
    if examples != trusted_examples:
        raise EvaluationInputError("Evaluation data must exactly match the canonical frozen fixture")
    if not isinstance(examples, list) or not examples:
        raise EvaluationInputError("Evaluation dataset must contain examples")
    if not isinstance(predictions, Mapping):
        raise EvaluationInputError("Predictions must be a mapping of sample_id to answer")

    seen_ids: set[str] = set()
    seen_questions: set[str] = set()
    for index, example in enumerate(examples):
        if not isinstance(example, Mapping):
            raise EvaluationInputError(f"Example {index} must be an object")
        sample_id = example.get("sample_id")
        question = example.get("question")
        if not isinstance(sample_id, str) or not sample_id or sample_id in seen_ids:
            raise EvaluationInputError(f"Example {index} has an invalid or duplicate sample_id")
        if not isinstance(question, str) or not question.strip() or question in seen_questions:
            raise EvaluationInputError(f"Example {sample_id} has an invalid or duplicate question")
        if example.get("split") != "test" or question_split(question) != "test":
            raise EvaluationInputError(f"Example {sample_id} is not in the reserved test split")
        if not isinstance(example.get("answer"), str) or not example["answer"].strip():
            raise EvaluationInputError(f"Example {sample_id} has an invalid expected answer")
        if not isinstance(example.get("topic"), str) or not example["topic"]:
            raise EvaluationInputError(f"Example {sample_id} has an invalid topic")
        if type(example.get("difficulty")) is not int or example["difficulty"] not in (1, 2, 3):
            raise EvaluationInputError(f"Example {sample_id} has an invalid difficulty")
        seen_ids.add(sample_id)
        seen_questions.add(question)

    known_ids = seen_ids
    unknown_ids = set(predictions).difference(known_ids)
    if unknown_ids:
        raise EvaluationInputError(f"Predictions contain unknown sample IDs: {sorted(map(str, unknown_ids))}")
    for sample_id, prediction in predictions.items():
        if not isinstance(sample_id, str) or not isinstance(prediction, str):
            raise EvaluationInputError("Prediction IDs and answers must be strings")

    rows: list[dict[str, Any]] = []
    for example in examples:
        sample_id = str(example["sample_id"])
        predicted = predictions.get(sample_id)
        if predicted is None:
            category = "missing_prediction"
            correct = False
        else:
            correct = _normalize_answer(predicted) == _normalize_answer(str(example["answer"]))
            category = "correct" if correct else "incorrect_answer"
        rows.append({
            "sample_id": sample_id,
            "topic": str(example["topic"]),
            "difficulty": int(example["difficulty"]),
            "correct": correct,
            "failure_category": category,
            "expected_answer": str(example["answer"]),
            "predicted_answer": predicted,
        })

    correct_count = sum(bool(row["correct"]) for row in rows)
    total = len(rows)
    prediction_payload = json.dumps(dict(predictions), ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    report: dict[str, Any] = {
        "report_schema_version": 1,
        "evaluator_version": EVALUATOR_VERSION,
        "dataset": {
            "dataset_id": DATASET_ID,
            "schema_version": 1,
            "frozen": True,
            "sample_count": total,
        },
        "predictions": {
            "provided_count": len(predictions),
            "sha256": hashlib.sha256(prediction_payload.encode("utf-8")).hexdigest(),
        },
        "overall": {
            "correct": correct_count,
            "total": total,
            "accuracy": correct_count / total,
        },
        "by_topic": _group_metrics(rows, "topic"),
        "by_difficulty": _group_metrics(rows, "difficulty"),
        "failures": [
            {
                "sample_id": row["sample_id"],
                "topic": row["topic"],
                "difficulty": row["difficulty"],
                "category": row["failure_category"],
                "expected_answer": row["expected_answer"],
                "predicted_answer": row["predicted_answer"],
            }
            for row in rows if not row["correct"]
        ],
    }
    if model_label is not None:
        if not isinstance(model_label, str) or not model_label.strip():
            raise EvaluationInputError("model_label must be a non-empty string when provided")
        report["model_label"] = model_label.strip()
    return report


def _load_predictions(path: str | Path) -> dict[str, str]:
    raw = Path(path).read_bytes()
    try:
        payload = json.loads(raw.decode("utf-8"))
    except (UnicodeError, json.JSONDecodeError) as error:
        raise EvaluationInputError(f"Could not read predictions JSON: {error}") from error
    if not isinstance(payload, dict):
        raise EvaluationInputError("Predictions file must be a JSON object mapping sample IDs to answers")
    if "predictions" in payload:
        payload = payload["predictions"]
    if not isinstance(payload, dict):
        raise EvaluationInputError("The predictions property must be a JSON object")
    return payload


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Score explicit ULTRON predictions against the frozen foundation test set.")
    parser.add_argument("--predictions", required=True, help="JSON object mapping sample_id to predicted answer")
    parser.add_argument("--output", help="Optional path for the JSON report; stdout is used when omitted")
    parser.add_argument("--model-label", help="Optional descriptive model/checkpoint label")
    args = parser.parse_args(argv)

    try:
        dataset = load_heldout_dataset()
        report = evaluate_predictions(dataset, _load_predictions(args.predictions), model_label=args.model_label)
        rendered = json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\\n"
        if args.output:
            Path(args.output).write_text(rendered, encoding="utf-8")
        else:
            print(rendered, end="")
    except (EvaluationInputError, OSError) as error:
        parser.error(str(error))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
