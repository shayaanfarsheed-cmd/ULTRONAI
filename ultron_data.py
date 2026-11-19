from __future__ import annotations

import hashlib
import math
import random
from decimal import Decimal
from fractions import Fraction
from typing import Any, Iterable

from ultron_verify import verify_example


DATA_GENERATOR_VERSION = "2.0.0"


class InvalidGeneratedExampleError(ValueError):
    """Raised when a generated example fails its independent verification."""


SUPPORTED_TOPICS = (
    "whole_number_arithmetic",
    "fractions",
    "decimals",
    "percentages",
    "ratios_and_proportions",
    "integers",
    "order_of_operations",
    "pre_algebra",
    "linear_equations",
    "inequalities",
    "exponents_and_roots",
    "basic_geometry",
    "basic_statistics",
    "basic_probability",
    "median_and_range",
    "simple_interest",
    "unit_conversion",
    "pythagorean_theorem",
)


def _format_fraction(value: Fraction) -> str:
    if value.denominator == 1:
        return str(value.numerator)
    return f"{value.numerator}/{value.denominator}"


def _format_decimal(value: Decimal) -> str:
    rendered = format(value.normalize(), "f")
    if "." in rendered:
        rendered = rendered.rstrip("0").rstrip(".")
    return rendered or "0"


def _make_example(topic: str, question: str, steps: list[str], answer: str, difficulty: int, sample_index: int) -> dict[str, Any]:
    sample_id = hashlib.sha256(f"{topic}|{question}".encode("utf-8")).hexdigest()[:16]
    example = {
        "sample_id": sample_id,
        "sample_index": sample_index,
        "topic": topic,
        "difficulty": difficulty,
        "question": question,
        "steps": steps,
        "answer": answer,
    }
    if not verify_example(example):
        raise InvalidGeneratedExampleError(f"Generated example failed verification: {topic}")
    return example


def generate_example(topic: str, rng: random.Random, difficulty: int = 1, sample_index: int = 0) -> dict[str, Any]:
    if topic not in SUPPORTED_TOPICS:
        raise ValueError(f"Unsupported topic: {topic}")
    if not isinstance(rng, random.Random):
        raise ValueError("rng must be an instance of random.Random")
    if type(difficulty) is not int or difficulty not in (1, 2, 3):
        raise ValueError("difficulty must be an integer from 1 to 3")
    if type(sample_index) is not int or sample_index < 0:
        raise ValueError("sample_index must be a non-negative integer")
    level = difficulty
    upper = (12, 99, 999)[level - 1]

    if topic == "whole_number_arithmetic":
        operation = rng.choice(("+", "-", "*", "/"))
        if operation == "/":
            divisor = rng.randint(2, max(3, min(200, upper)))
            quotient = rng.randint(2, max(3, min(200, upper)))
            left, right = divisor * quotient, divisor
            result = quotient
        else:
            left, right = rng.randint(1, upper), rng.randint(1, upper)
            if operation == "+":
                result = left + right
            elif operation == "-":
                if right > left:
                    left, right = right, left
                result = left - right
            else:
                left, right = rng.randint(2, min(200, upper)), rng.randint(2, min(200, upper))
                result = left * right
        question = f"Calculate: {left} {operation} {right}"
        steps = [f"Step 1: {left} {operation} {right} = {result}."]
        return _make_example(topic, question, steps, str(result), level, sample_index)

    if topic == "fractions":
        fraction_scale = (6, 18, 36)[level - 1]
        left = Fraction(rng.randint(1, fraction_scale), rng.randint(2, fraction_scale))
        right = Fraction(rng.randint(1, fraction_scale), rng.randint(2, fraction_scale))
        operation = rng.choice(("+", "-", "*", "/"))
        if operation == "/":
            result = left / right
        elif operation == "+":
            result = left + right
        elif operation == "-":
            result = left - right
        else:
            result = left * right
        left_text = f"{left.numerator}/{left.denominator}"
        right_text = f"{right.numerator}/{right.denominator}"
        question = f"Calculate: ({left_text}) {operation} ({right_text})"
        if operation in {"+", "-"}:
            common = math.lcm(left.denominator, right.denominator)
            first = left.numerator * (common // left.denominator)
            second = right.numerator * (common // right.denominator)
            raw = first + second if operation == "+" else first - second
            steps = [
                f"Step 1: Use denominator {common}.",
                f"Step 2: {first}/{common} {operation} {second}/{common} = {raw}/{common}.",
                f"Step 3: Reduce to {_format_fraction(result)}.",
            ]
        elif operation == "*":
            steps = [
                f"Step 1: Multiply numerators {left.numerator} * {right.numerator}.",
                f"Step 2: Multiply denominators {left.denominator} * {right.denominator}.",
                f"Step 3: Reduce to {_format_fraction(result)}.",
            ]
        else:
            steps = [
                f"Step 1: Flip the second fraction to {right.denominator}/{right.numerator}.",
                f"Step 2: Multiply to get {_format_fraction(result)}.",
            ]
        return _make_example(topic, question, steps, _format_fraction(result), level, sample_index)

    if topic == "decimals":
        left = Decimal(rng.randint(1, upper * 10)) / Decimal(100)
        right = Decimal(rng.randint(1, upper * 10)) / Decimal(100)
        operation = rng.choice(("+", "-"))
        if operation == "-" and right > left:
            left, right = right, left
        result = left + right if operation == "+" else left - right
        left_text, right_text, answer = _format_decimal(left), _format_decimal(right), _format_decimal(result)
        question = f"Calculate: {left_text} {operation} {right_text}"
        steps = [f"Step 1: Line up the decimal places.", f"Step 2: {left_text} {operation} {right_text} = {answer}."]
        return _make_example(topic, question, steps, answer, level, sample_index)

    if topic == "percentages":
        percent = rng.choice((5, 10, 15, 20, 25, 30, 40, 50, 75, 80))
        amount = rng.randint(10, upper)
        result = Fraction(percent * amount, 100)
        answer = _format_fraction(result)
        question = f"Percentage: {percent}% of {amount}"
        steps = [f"Step 1: {percent}/100 * {amount} = {answer}."]
        return _make_example(topic, question, steps, answer, level, sample_index)

    if topic == "ratios_and_proportions":
        left, right = rng.randint(2, upper), rng.randint(2, upper)
        divisor = math.gcd(left, right)
        answer = f"{left // divisor}:{right // divisor}"
        question = f"Simplify ratio: {left}:{right}"
        steps = [f"Step 1: Divide both parts by {divisor}.", f"Step 2: The simplest ratio is {answer}."]
        return _make_example(topic, question, steps, answer, level, sample_index)

    if topic == "integers":
        left, right = rng.randint(-upper, upper), rng.randint(-upper, upper)
        operation = rng.choice(("+", "-"))
        result = left + right if operation == "+" else left - right
        question = f"Calculate: {left} {operation} {right}"
        steps = [f"Step 1: Apply the integer operation.", f"Step 2: {left} {operation} {right} = {result}."]
        return _make_example(topic, question, steps, str(result), level, sample_index)

    if topic == "order_of_operations":
        first, second, third = rng.randint(1, upper), rng.randint(2, 20), rng.randint(2, 20)
        partial = second * third
        result = first + partial
        question = f"Calculate: {first} + {second} * {third}"
        steps = [f"Step 1: Multiply first: {second} * {third} = {partial}.", f"Step 2: Add: {first} + {partial} = {result}."]
        return _make_example(topic, question, steps, str(result), level, sample_index)

    if topic == "pre_algebra":
        value, offset = rng.randint(-upper, upper), rng.randint(1, upper)
        operation = rng.choice(("+", "-"))
        right = value + offset if operation == "+" else value - offset
        question = f"Solve: x {operation} {offset} = {right}"
        step = f"Step 1: Isolate x to get x = {value}."
        return _make_example(topic, question, [step], f"x = {value}", level, sample_index)

    if topic == "linear_equations":
        coefficient = rng.randint(2, 12)
        value, offset = rng.randint(-upper, upper), rng.randint(-upper, upper)
        right = coefficient * value + offset
        question = f"Solve: {coefficient}*x + {offset} = {right}"
        intermediate = right - offset
        steps = [
            f"Step 1: Subtract {offset} to get {coefficient}*x = {intermediate}.",
            f"Step 2: Divide by {coefficient} to get x = {value}.",
        ]
        return _make_example(topic, question, steps, f"x = {value}", level, sample_index)

    if topic == "inequalities":
        coefficient = rng.randint(1, 9)
        value, offset = rng.randint(-upper, upper), rng.randint(-upper, upper)
        relation = rng.choice(("<", ">"))
        boundary = coefficient * value + offset
        question = f"Solve: {coefficient}*x + {offset} {relation} {boundary}"
        answer = f"x {relation} {value}"
        steps = [f"Step 1: Isolate x at the boundary.", f"Step 2: The solution is {answer}."]
        return _make_example(topic, question, steps, answer, level, sample_index)

    if topic == "exponents_and_roots":
        if rng.choice((True, False)):
            maximum_exponent = (3, 5, 8)[level - 1]
            exponent = rng.randint(2, maximum_exponent)
            base = rng.randint(2, min(200, upper))
            result = base ** exponent
            question = f"Calculate: {base} ** {exponent}"
            if exponent == 2:
                steps = [f"Step 1: Multiply {base} by itself.", f"Step 2: {base} ** 2 = {result}."]
            else:
                steps = [
                    f"Step 1: Multiply {base} by itself {exponent} times.",
                    f"Step 2: {base} ** {exponent} = {result}.",
                ]
        else:
            root = rng.randint(2, min(200, upper))
            result = root
            question = f"Calculate: sqrt({root * root})"
            steps = [f"Step 1: Find the exact square root.", f"Step 2: sqrt({root * root}) = {result}."]
        return _make_example(topic, question, steps, str(result), level, sample_index)

    if topic == "basic_geometry":
        length, width = rng.randint(1, upper), rng.randint(1, upper)
        if rng.choice((True, False)):
            result = length * width
            question = f"Area of rectangle: length {length}, width {width}"
            steps = [f"Step 1: Area = length * width.", f"Step 2: {length} * {width} = {result}."]
        else:
            result = 2 * (length + width)
            question = f"Perimeter of rectangle: length {length}, width {width}"
            steps = [f"Step 1: Perimeter = 2 * (length + width).", f"Step 2: 2 * ({length} + {width}) = {result}."]
        return _make_example(topic, question, steps, str(result), level, sample_index)

    if topic == "basic_statistics":
        values = [rng.randint(1, upper) for _ in range(3)]
        result = Fraction(sum(values), len(values))
        answer = _format_fraction(result)
        question = "Mean of: " + ", ".join(str(value) for value in values)
        steps = [f"Step 1: Add the values to get {sum(values)}.", f"Step 2: Divide by {len(values)} to get {answer}."]
        return _make_example(topic, question, steps, answer, level, sample_index)

    if topic == "basic_probability":
        total = rng.randint(2, max(3, min(upper, 200)))
        favorable = rng.randint(1, total)
        result = Fraction(favorable, total)
        answer = _format_fraction(result)
        question = f"Probability: {favorable} favorable, {total} total"
        steps = [f"Step 1: Divide favorable outcomes by total outcomes.", f"Step 2: The probability is {answer}."]
        return _make_example(topic, question, steps, answer, level, sample_index)

    if topic == "median_and_range":
        values = sorted(rng.randint(1, upper) for _ in range(5))
        median = values[2]
        spread = values[-1] - values[0]
        rendered = ", ".join(str(value) for value in values)
        answer = f"median={median}; range={spread}"
        question = f"Median and range of: {rendered}"
        steps = [
            f"Step 1: Sort the five values: {rendered}.",
            f"Step 2: The middle value is {median}, and the range is {values[-1]} - {values[0]} = {spread}.",
            f"Step 3: {answer}.",
        ]
        return _make_example(topic, question, steps, answer, level, sample_index)

    if topic == "simple_interest":
        principal = rng.randint(20, max(30, upper * 10))
        rate = rng.choice((2, 3, 4, 5, 6, 8, 10, 12))
        years = rng.randint(1, level + 2)
        interest = Fraction(principal * rate * years, 100)
        answer = _format_fraction(interest)
        question = f"Simple interest: principal {principal}, rate {rate}%, time {years} years"
        steps = [
            f"Step 1: Use I = P * r * t / 100.",
            f"Step 2: I = {principal} * {rate} * {years} / 100 = {answer}.",
        ]
        return _make_example(topic, question, steps, answer, level, sample_index)

    if topic == "unit_conversion":
        factor, unit_from, unit_to = rng.choice((
            (100, "m", "cm"),
            (10, "cm", "mm"),
            (1000, "kg", "g"),
        ))
        amount = rng.randint(1, upper)
        result = amount * factor
        question = f"Convert: {amount} {unit_from} to {unit_to}"
        steps = [
            f"Step 1: 1 {unit_from} = {factor} {unit_to}.",
            f"Step 2: {amount} * {factor} = {result} {unit_to}.",
        ]
        return _make_example(topic, question, steps, str(result), level, sample_index)

    if topic == "pythagorean_theorem":
        maximum_m = (5, 15, 50)[level - 1]
        while True:
            m = rng.randint(2, maximum_m)
            n = rng.randint(1, m - 1)
            if math.gcd(m, n) == 1 and (m - n) % 2 == 1:
                break
        left = m * m - n * n
        right = 2 * m * n
        hypotenuse = m * m + n * n
        if rng.choice((True, False)):
            left, right = right, left
        question = f"Hypotenuse of right triangle: legs {left}, {right}"
        answer = str(hypotenuse)
        steps = [
            f"Step 1: Use c^2 = a^2 + b^2 = {left}^2 + {right}^2.",
            f"Step 2: c = sqrt({left * left + right * right}) = {hypotenuse}.",
        ]
        return _make_example(topic, question, steps, answer, level, sample_index)

    raise ValueError(f"Unsupported topic: {topic}")


def _split_bucket(question: str) -> int:
    digest = hashlib.sha256(question.encode("utf-8")).digest()
    return int.from_bytes(digest[:4], "big") % 10


def question_split(question: str) -> str:
    """Return the stable split for a non-empty question.

    This is the single source of truth used by both dataset generation and
    the self-learning dry run. The question text, not its generation index,
    determines the split.
    """
    if not isinstance(question, str) or not question.strip():
        raise ValueError("Question must be a non-empty string")
    bucket = _split_bucket(question)
    if bucket < 8:
        return "train"
    if bucket == 8:
        return "validation"
    return "test"


def generate_dataset(
    count: int,
    seed: int,
    split: str = "train",
    topics: Iterable[str] = SUPPORTED_TOPICS,
    maximum_attempts: int | None = None,
) -> list[dict[str, Any]]:
    if type(count) is not int or count < 1:
        raise ValueError("Dataset count must be a positive integer")
    if type(seed) is not int:
        raise ValueError("Dataset seed must be an integer")
    split_buckets = {"train": set(range(8)), "validation": {8}, "test": {9}}
    if not isinstance(split, str) or split not in split_buckets:
        raise ValueError("Split must be train, validation or test")
    if topics is None or isinstance(topics, (str, bytes)):
        raise ValueError("Topics must be an iterable of unique supported topic names")
    try:
        topic_list = tuple(topics)
    except TypeError as error:
        raise ValueError("Topics must be an iterable of unique supported topic names") from error
    if (
        not topic_list
        or any(not isinstance(topic, str) or topic not in SUPPORTED_TOPICS for topic in topic_list)
        or len(set(topic_list)) != len(topic_list)
    ):
        raise ValueError("Topic list is empty, duplicated, or contains an unsupported topic")
    attempt_limit = maximum_attempts if maximum_attempts is not None else count * 30 + 300
    if type(attempt_limit) is not int or attempt_limit < 1:
        raise ValueError("Maximum attempts must be a positive integer")
    examples: list[dict[str, Any]] = []
    seen: set[str] = set()

    for index in range(attempt_limit):
        topic_index = index % len(topic_list)
        topic = topic_list[topic_index]
        difficulty = 1 + ((index // len(topic_list)) % 3)
        rng = random.Random(seed + index * 1000003 + topic_index * 7919)
        example = generate_example(topic, rng, difficulty, index)
        question_key = example["question"]
        if question_key in seen:
            continue
        seen.add(question_key)
        if question_split(example["question"]) != split:
            continue
        example["split"] = split
        if not verify_example(example):
            raise RuntimeError(f"Independent verifier rejected generated sample {example['sample_id']}")
        examples.append(example)
        if len(examples) == count:
            return examples

    raise RuntimeError(f"Could only generate {len(examples)} of {count} requested {split} examples")
