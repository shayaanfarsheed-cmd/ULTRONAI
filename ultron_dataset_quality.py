from __future__ import annotations

import hashlib
import re
import unicodedata
from collections import Counter, defaultdict
from difflib import SequenceMatcher
from typing import Any, Iterable, Mapping

from ultron_data import question_split
from ultron_verify import verify_example_detailed

QUALITY_AUDITOR_VERSION = "1.0.0"
NEAR_DUPLICATE_THRESHOLD = 0.985


class DatasetQualityError(ValueError):
    """Raised when a generated dataset violates a quality or split-safety gate."""


def normalize_question(question: str) -> str:
    if not isinstance(question, str) or not question.strip():
        raise ValueError("Question must be a non-empty string")
    normalized = unicodedata.normalize("NFKC", question).casefold()
    return " ".join(normalized.split())


def structural_fingerprint(question: str) -> str:
    """Return a template fingerprint that preserves operators and replaces literals."""
    normalized = normalize_question(question)
    tokens = re.findall(r"\d+(?:\.\d+)?|[a-z]+|[^\w\s]", normalized)
    shaped = ["<number>" if re.fullmatch(r"\d+(?:\.\d+)?", token) else token for token in tokens]
    return " ".join(shaped)


def _near_duplicate_pairs(examples: list[Mapping[str, Any]], threshold: float) -> list[dict[str, Any]]:
    """Find highly similar questions using a bounded candidate index.

    The exact and structural indexes catch the common generator-template cases.
    This fuzzy pass catches near-identical text with small wording/punctuation edits.
    """
    buckets: dict[tuple[str, int], list[int]] = defaultdict(list)
    token_rows: list[tuple[str, ...]] = []
    for index, example in enumerate(examples):
        topic = str(example.get("topic", ""))
        question = normalize_question(str(example.get("question", "")))
        tokens = tuple(re.findall(r"[a-z]+|\d+(?:\.\d+)?|[^\w\s]", question))
        token_rows.append(tokens)
        buckets[(topic, len(tokens))].append(index)

    pairs: list[dict[str, Any]] = []
    seen: set[tuple[int, int]] = set()
    for indices in buckets.values():
        # Very large same-length groups are narrowed by the first and last token.
        indexed: dict[tuple[str, ...], list[int]] = defaultdict(list)
        for index in indices:
            tokens = token_rows[index]
            # The first three tokens keep candidate groups narrow while
            # allowing edits to later numbers/terms to be compared.
            signature = tokens[:3] if len(tokens) >= 3 else tokens
            indexed[signature].append(index)
        candidates: set[tuple[int, int]] = set()
        for group in indexed.values():
            if len(group) > 1:
                for offset, left in enumerate(group):
                    for right in group[offset + 1:]:
                        candidates.add((min(left, right), max(left, right)))
        for left, right in candidates:
            if (left, right) in seen:
                continue
            seen.add((left, right))
            a, b = token_rows[left], token_rows[right]
            if not a or not b:
                continue
            similarity = SequenceMatcher(a=a, b=b, autojunk=False).ratio()
            if similarity >= threshold and normalize_question(str(examples[left]["question"])) != normalize_question(str(examples[right]["question"])):
                pairs.append({
                    "left_sample_id": examples[left].get("sample_id"),
                    "right_sample_id": examples[right].get("sample_id"),
                    "left_split": examples[left].get("split"),
                    "right_split": examples[right].get("split"),
                    "similarity": round(similarity, 6),
                })
    return pairs


def audit_dataset(
    examples: Iterable[Mapping[str, Any]],
    *,
    required_splits: tuple[str, ...] = ("train", "validation", "test"),
    near_duplicate_threshold: float = NEAR_DUPLICATE_THRESHOLD,
    require_all_topics: Iterable[str] = (),
    minimum_examples: int = 1,
) -> dict[str, Any]:
    """Validate answers, metadata, uniqueness, split isolation and dataset coverage."""
    if not 0.0 < near_duplicate_threshold <= 1.0:
        raise ValueError("near_duplicate_threshold must be in (0, 1]")
    if type(minimum_examples) is not int or minimum_examples < 1:
        raise ValueError("minimum_examples must be a positive integer")

    rows = [dict(row) for row in examples]
    if len(rows) < minimum_examples:
        raise DatasetQualityError(f"Dataset has {len(rows)} examples; requires at least {minimum_examples}")

    seen_ids: dict[str, int] = {}
    seen_questions: dict[str, int] = {}
    question_splits: dict[str, set[str]] = defaultdict(set)
    structural_splits: dict[str, set[str]] = defaultdict(set)
    topic_counts: Counter[str] = Counter()
    difficulty_counts: Counter[str] = Counter()
    split_counts: Counter[str] = Counter()
    invalid: list[dict[str, Any]] = []
    exact_duplicates: list[dict[str, Any]] = []

    for index, row in enumerate(rows):
        sample_id = row.get("sample_id")
        question = row.get("question")
        topic = row.get("topic")
        difficulty = row.get("difficulty")
        split = row.get("split")
        if not isinstance(sample_id, str) or not sample_id:
            invalid.append({"index": index, "reason": "invalid_sample_id"})
            continue
        if not isinstance(question, str) or not question.strip():
            invalid.append({"sample_id": sample_id, "reason": "invalid_question"})
            continue
        if not isinstance(topic, str) or not topic:
            invalid.append({"sample_id": sample_id, "reason": "invalid_topic"})
            continue
        if type(difficulty) is not int or difficulty not in (1, 2, 3):
            invalid.append({"sample_id": sample_id, "reason": "invalid_difficulty"})
            continue
        if split not in required_splits:
            invalid.append({"sample_id": sample_id, "reason": "invalid_split"})
            continue
        if question_split(question) != split:
            invalid.append({"sample_id": sample_id, "reason": "question_split_mismatch"})
        if sample_id in seen_ids:
            exact_duplicates.append({
                "kind": "duplicate_sample_id",
                "sample_id": sample_id,
                "first_index": seen_ids[sample_id],
                "duplicate_index": index,
            })
        else:
            seen_ids[sample_id] = index
        normalized = normalize_question(question)
        if normalized in seen_questions:
            exact_duplicates.append({
                "kind": "duplicate_question",
                "question": question,
                "first_index": seen_questions[normalized],
                "duplicate_index": index,
            })
        else:
            seen_questions[normalized] = index

        question_splits[normalized].add(str(split))
        structural_splits[structural_fingerprint(question)].add(str(split))
        topic_counts[str(topic)] += 1
        difficulty_counts[str(difficulty)] += 1
        split_counts[str(split)] += 1

        valid, reason = verify_example_detailed(row)
        if not valid:
            invalid.append({"sample_id": sample_id, "reason": reason or "answer_verification_failed"})

    cross_split_exact = [
        {"question": question, "splits": sorted(splits)}
        for question, splits in question_splits.items()
        if len(splits) > 1
    ]

    structural_leakage = [
        {"fingerprint": fingerprint, "splits": sorted(splits)}
        for fingerprint, splits in structural_splits.items()
        if len(splits) > 1
    ]
    near_duplicates = _near_duplicate_pairs(rows, near_duplicate_threshold)
    near_duplicate_leakage = [
        pair for pair in near_duplicates if pair["left_split"] != pair["right_split"]
    ]

    missing_splits = [split for split in required_splits if split_counts[split] == 0]
    required_topics = set(require_all_topics)
    missing_topics = sorted(required_topics.difference(topic_counts))
    status = "passed" if not (
        invalid or exact_duplicates or cross_split_exact or near_duplicate_leakage
        or missing_splits or missing_topics
    ) else "failed"

    return {
        "auditor_version": QUALITY_AUDITOR_VERSION,
        "status": status,
        "example_count": len(rows),
        "split_counts": dict(sorted(split_counts.items())),
        "topic_counts": dict(sorted(topic_counts.items())),
        "difficulty_counts": dict(sorted(difficulty_counts.items())),
        "invalid_example_count": len(invalid),
        "invalid_examples": invalid[:100],
        "exact_duplicate_count": len(exact_duplicates),
        "exact_duplicates": exact_duplicates[:100],
        "cross_split_exact_leakage_count": len(cross_split_exact),
        "cross_split_exact_leakage": cross_split_exact[:100],
        "structural_template_count": len(structural_splits),
        "structural_templates_shared_across_splits": len(structural_leakage),
        "structural_template_leakage": structural_leakage[:100],
        "near_duplicate_count": len(near_duplicates),
        "near_duplicate_leakage_count": len(near_duplicate_leakage),
        "near_duplicate_leakage": near_duplicate_leakage[:100],
        "near_duplicate_threshold": near_duplicate_threshold,
        "missing_splits": missing_splits,
        "missing_topics": missing_topics,
        "dataset_sha256": hashlib.sha256(
            "\n".join(
                f"{row.get('split')}|{row.get('topic')}|{row.get('question')}|{row.get('answer')}"
                for row in rows
            ).encode("utf-8")
        ).hexdigest(),
    }


def require_dataset_pass(report: Mapping[str, Any]) -> None:
    if report.get("status") != "passed":
        raise DatasetQualityError(
            "Dataset quality gates failed: "
            f"invalid={report.get('invalid_example_count')}, "
            f"duplicates={report.get('exact_duplicate_count')}, "
            f"exact_leakage={report.get('cross_split_exact_leakage_count')}, "
            f"near_duplicate_leakage={report.get('near_duplicate_leakage_count')}, "
            f"missing_splits={report.get('missing_splits')}, "
            f"missing_topics={report.get('missing_topics')}"
        )
