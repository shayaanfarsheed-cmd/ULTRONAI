from __future__ import annotations

import hashlib
import random
from collections import Counter
from typing import Any, Callable, Iterable, Mapping

from ultron_data import SUPPORTED_TOPICS, generate_example
from ultron_verify import verify_example_detailed


SPLIT_BUCKETS = {
    "train": frozenset(range(8)),
    "validation": frozenset({8}),
    "test": frozenset({9}),
}
MAX_ACCEPTED_PER_RUN = 5000


def _question_bucket(question: str, sample_index: int) -> int:
    if not question:
        return sample_index % 10
    digest = hashlib.sha256(question.encode("utf-8")).digest()
    return int.from_bytes(digest[:4], "big") % 10


def run_generation_dry_run(
    count: int,
    seed: int,
    split: str = "train",
    topics: Iterable[str] = SUPPORTED_TOPICS,
    maximum_attempts: int | None = None,
    generator: Callable[..., Mapping[str, Any]] | None = None,
    verifier: Callable[[Mapping[str, Any]], tuple[bool, str]] | None = None,
) -> dict[str, Any]:
    """Generate and independently verify examples without saving or training.

    Count is the requested number of accepted examples, not the number of
    candidates. Rejected candidates are counted and never returned as training
    examples. The split hash is stable and matches ultron_data's 80/10/10 split.
    """
    if type(count) is not int or not 1 <= count <= MAX_ACCEPTED_PER_RUN:
        raise ValueError(f"count must be an integer between 1 and {MAX_ACCEPTED_PER_RUN}")
    if type(seed) is not int:
        raise ValueError("seed must be an integer")
    if split not in SPLIT_BUCKETS:
        raise ValueError("split must be train, validation or test")

    topic_list = tuple(topics)
    if not topic_list or any(topic not in SUPPORTED_TOPICS for topic in topic_list):
        raise ValueError("topics must contain supported ULTRON topics")

    make_candidate = generate_example if generator is None else generator
    verify_candidate = verify_example_detailed if verifier is None else verifier
    attempt_limit = maximum_attempts if maximum_attempts is not None else count * 30 + 300
    if type(attempt_limit) is not int or attempt_limit < 1:
        raise ValueError("maximum_attempts must be a positive integer")

    accepted: list[dict[str, Any]] = []
    rejected_reasons: Counter[str] = Counter()
    topic_counts: Counter[str] = Counter()
    difficulty_counts: Counter[str] = Counter()
    seen_questions: set[str] = set()
    candidates_in_split = 0

    for sample_index in range(attempt_limit):
        topic_index = sample_index % len(topic_list)
        topic = topic_list[topic_index]
        difficulty = 1 + (sample_index % 3)
        rng = random.Random(seed + sample_index * 1000003 + topic_index * 7919)

        try:
            candidate = make_candidate(
                topic,
                rng,
                difficulty=difficulty,
                sample_index=sample_index,
            )
        except Exception as error:
            if sample_index % 10 in SPLIT_BUCKETS[split]:
                candidates_in_split += 1
                rejected_reasons[type(error).__name__] += 1
            continue

        if not isinstance(candidate, Mapping):
            if sample_index % 10 in SPLIT_BUCKETS[split]:
                candidates_in_split += 1
                rejected_reasons["invalid_candidate_type"] += 1
            continue

        question = candidate.get("question")
        question_text = question if isinstance(question, str) else ""
        if _question_bucket(question_text, sample_index) not in SPLIT_BUCKETS[split]:
            continue

        candidates_in_split += 1
        if not question_text:
            rejected_reasons["missing_question"] += 1
            continue
        if question_text in seen_questions:
            rejected_reasons["duplicate_question"] += 1
            continue
        seen_questions.add(question_text)

        try:
            valid, reason = verify_candidate(candidate)
        except Exception as error:
            valid, reason = False, type(error).__name__

        if not valid:
            rejected_reasons[str(reason or "verification_failed")] += 1
            continue

        example = dict(candidate)
        example["split"] = split
        accepted.append(example)
        topic_counts[str(example.get("topic", "unknown"))] += 1
        difficulty_counts[str(example.get("difficulty", "unknown"))] += 1
        if len(accepted) >= count:
            break

    return {
        "status": "complete" if len(accepted) == count else "incomplete",
        "mode": "generation_and_verification_dry_run",
        "split": split,
        "seed": seed,
        "requested_accepted": count,
        "attempt_limit": attempt_limit,
        "candidates_in_split": candidates_in_split,
        "accepted_count": len(accepted),
        "rejected_count": sum(rejected_reasons.values()),
        "rejection_reasons": dict(sorted(rejected_reasons.items())),
        "topic_counts": dict(sorted(topic_counts.items())),
        "difficulty_counts": dict(sorted(difficulty_counts.items())),
        "examples": accepted,
        "training_started": False,
        "model_weights_changed": False,
        "written_to_disk": False,
    }
