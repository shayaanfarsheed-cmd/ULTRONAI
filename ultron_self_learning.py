from __future__ import annotations

import random
from collections import Counter
from typing import Any, Callable, Iterable, Mapping

from ultron_data import InvalidGeneratedExampleError, SUPPORTED_TOPICS, generate_example, question_split
from ultron_verify import verify_example_detailed


MAX_ACCEPTED_PER_RUN = 5000


def run_generation_dry_run(
    count: int,
    seed: int,
    split: str = "train",
    topics: Iterable[str] = SUPPORTED_TOPICS,
    maximum_attempts: int | None = None,
    generator: Callable[..., Mapping[str, Any]] | None = None,
    verifier: Callable[[Mapping[str, Any]], tuple[bool, str]] | None = None,
) -> dict[str, Any]:
    """Generate and verify examples without saving data or training.

    A question's exact text determines its split through ultron_data's shared
    question_split() function. Generation failures that have no question
    cannot honestly be assigned to a data split, so they are reported
    separately from split-specific rejected candidates.

    Only InvalidGeneratedExampleError is treated as an expected bad candidate.
    All other generator/verifier exceptions propagate as programming failures.
    """
    if type(count) is not int or not 1 <= count <= MAX_ACCEPTED_PER_RUN:
        raise ValueError(f"count must be an integer between 1 and {MAX_ACCEPTED_PER_RUN}")
    if type(seed) is not int:
        raise ValueError("seed must be an integer")
    if not isinstance(split, str) or split not in {"train", "validation", "test"}:
        raise ValueError("split must be train, validation or test")

    if isinstance(topics, (str, bytes)):
        raise ValueError("topics must be an iterable of supported topic names")
    try:
        topic_list = tuple(topics)
    except TypeError as error:
        raise ValueError("topics must be an iterable of supported topic names") from error
    if (
        not topic_list
        or any(not isinstance(topic, str) or topic not in SUPPORTED_TOPICS for topic in topic_list)
        or len(set(topic_list)) != len(topic_list)
    ):
        raise ValueError("topics must contain unique, supported ULTRON topic names")

    make_candidate = generate_example if generator is None else generator
    verify_candidate = verify_example_detailed if verifier is None else verifier
    if not callable(make_candidate):
        raise ValueError("generator must be callable")
    if not callable(verify_candidate):
        raise ValueError("verifier must be callable")

    attempt_limit = maximum_attempts if maximum_attempts is not None else count * 30 + 300
    if type(attempt_limit) is not int or attempt_limit < 1:
        raise ValueError("maximum_attempts must be a positive integer")

    accepted: list[dict[str, Any]] = []
    rejected_reasons: Counter[str] = Counter()
    generation_errors: Counter[str] = Counter()
    unassigned_rejections: Counter[str] = Counter()
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
        except InvalidGeneratedExampleError as error:
            generation_errors[type(error).__name__] += 1
            continue

        if not isinstance(candidate, Mapping):
            unassigned_rejections["invalid_candidate_type"] += 1
            continue

        question = candidate.get("question")
        if not isinstance(question, str) or not question.strip():
            unassigned_rejections["missing_question"] += 1
            continue

        # Never fall back to sample_index: only the shared question hash can
        # assign a candidate to a split.
        if question_split(question) != split:
            continue

        candidates_in_split += 1
        if question in seen_questions:
            rejected_reasons["duplicate_question"] += 1
            continue
        seen_questions.add(question)

        if candidate.get("topic") != topic or candidate.get("difficulty") != difficulty:
            rejected_reasons["metadata_mismatch"] += 1
            continue
        if candidate.get("sample_index") != sample_index:
            rejected_reasons["sample_index_mismatch"] += 1
            continue

        # The verifier is a boundary check for injected/custom generators.
        # It is the same verifier module used by the default generator, not a
        # second independently implemented verifier.
        verification = verify_candidate(candidate)
        if (
            not isinstance(verification, tuple)
            or len(verification) != 2
            or type(verification[0]) is not bool
            or not isinstance(verification[1], str)
        ):
            raise TypeError("verifier must return a (bool, str) tuple")

        valid, reason = verification
        if not valid:
            rejected_reasons[reason or "verification_failed"] += 1
            continue

        example = dict(candidate)
        example["split"] = split
        accepted.append(example)
        topic_counts[topic] += 1
        difficulty_counts[str(difficulty)] += 1
        if len(accepted) == count:
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
        "generation_error_count": sum(generation_errors.values()),
        "generation_errors": dict(sorted(generation_errors.items())),
        "unassigned_rejection_count": sum(unassigned_rejections.values()),
        "unassigned_rejections": dict(sorted(unassigned_rejections.items())),
        "topic_counts": dict(sorted(topic_counts.items())),
        "difficulty_counts": dict(sorted(difficulty_counts.items())),
        "examples": accepted,
        "training_started": False,
        "model_weights_changed": False,
        "written_to_disk": False,
    }
