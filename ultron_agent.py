from __future__ import annotations

import argparse
import json
import math
import random
import re
import time
from collections import Counter
from decimal import Decimal
from fractions import Fraction
from typing import Any

from ultron_data import SUPPORTED_TOPICS, generate_example
from ultron_verify import verify_example_detailed


AGENT_VERSION = "0.1.0"
MAX_QUESTIONS_PER_RUN = 50_000
MAX_QUESTION_LENGTH = 1_000

# Compact, inspectable mathematical knowledge. These summaries guide method
# selection and are returned with every solution; they are not training data.
MATH_KNOWLEDGE: dict[str, dict[str, str]] = {
    "whole_number_arithmetic": {
        "concept": "Whole-number arithmetic",
        "rule": "Use addition, subtraction, multiplication, or exact division.",
        "method": "Read the operator, calculate with integer arithmetic, and check the result.",
    },
    "fractions": {
        "concept": "Fractions",
        "rule": "For + or -, use a common denominator; for *, multiply across; for /, multiply by the reciprocal.",
        "method": "Parse both fractions, apply the operation exactly, then reduce to lowest terms.",
    },
    "decimals": {
        "concept": "Decimals",
        "rule": "Align decimal places for addition and subtraction.",
        "method": "Use decimal arithmetic rather than binary floating-point, then remove insignificant trailing zeros.",
    },
    "percentages": {
        "concept": "Percentages",
        "rule": "p percent of n equals (p / 100) multiplied by n.",
        "method": "Multiply the percentage by the amount and divide by 100; reduce the exact fraction.",
    },
    "ratios_and_proportions": {
        "concept": "Ratios",
        "rule": "Equivalent ratios are made by multiplying or dividing both terms by the same non-zero number.",
        "method": "Find the greatest common divisor and divide both terms by it.",
    },
    "integers": {
        "concept": "Positive and negative integers",
        "rule": "Addition and subtraction follow signed-number rules.",
        "method": "Evaluate the signed expression and retain the sign of the result.",
    },
    "order_of_operations": {
        "concept": "Order of operations",
        "rule": "Multiplication is performed before addition; operations of equal priority are evaluated left to right.",
        "method": "Evaluate the multiplication first, then add the remaining term.",
    },
    "pre_algebra": {
        "concept": "One-step equations",
        "rule": "Keep an equation balanced by applying the inverse operation to both sides.",
        "method": "Undo the addition or subtraction attached to x to isolate x.",
    },
    "linear_equations": {
        "concept": "Linear equations",
        "rule": "Apply inverse operations to both sides; isolate the variable by undoing addition, then multiplication.",
        "method": "Subtract the constant term, then divide by the coefficient of x.",
    },
    "inequalities": {
        "concept": "Linear inequalities",
        "rule": "Solve like an equation. Dividing by a negative reverses the inequality sign.",
        "method": "Find the boundary value and preserve the direction for the positive coefficients supported here.",
    },
    "exponents_and_roots": {
        "concept": "Exponents and square roots",
        "rule": "a squared means a multiplied by itself; sqrt(n) is the non-negative value whose square is n.",
        "method": "Use integer multiplication or an exact integer square-root check.",
    },
    "basic_geometry": {
        "concept": "Rectangle geometry",
        "rule": "Rectangle area = length × width; perimeter = 2 × (length + width).",
        "method": "Identify whether area or perimeter is requested, then substitute the given dimensions.",
    },
    "basic_statistics": {
        "concept": "Mean (average)",
        "rule": "Mean = sum of all values divided by the number of values.",
        "method": "Add the values, divide by the count, and simplify the exact result.",
    },
    "basic_probability": {
        "concept": "Basic probability",
        "rule": "Probability = favourable outcomes / total equally likely outcomes.",
        "method": "Form the favourable-to-total fraction and reduce it.",
    },
}


class AgentInputError(ValueError):
    """Raised when an agent request is outside its bounded input contract."""


def _fraction_text(value: Fraction) -> str:
    return str(value.numerator) if value.denominator == 1 else f"{value.numerator}/{value.denominator}"


def _decimal_text(value: Decimal) -> str:
    rendered = format(value.normalize(), "f")
    if "." in rendered:
        rendered = rendered.rstrip("0").rstrip(".")
    return rendered or "0"


def solve_question(topic: str, question: str) -> dict[str, Any]:
    """Solve from topic + question only; expected answers/steps are never inputs."""
    if not isinstance(topic, str) or topic not in MATH_KNOWLEDGE:
        raise AgentInputError(f"Unsupported topic: {topic}")
    if not isinstance(question, str) or not question.strip():
        raise AgentInputError("question must be a non-empty string")
    if len(question) > MAX_QUESTION_LENGTH:
        raise AgentInputError(f"question must be at most {MAX_QUESTION_LENGTH} characters")

    answer: str
    steps: list[str]

    if topic in {"whole_number_arithmetic", "integers"}:
        prefix = "Calculate: "
        if not question.startswith(prefix):
            raise AgentInputError("Invalid arithmetic question")
        expression = question[len(prefix):]
        match = re.fullmatch(r"(-?\d+) ([+*/-]) (-?\d+)", expression)
        if not match:
            raise AgentInputError("Unsupported arithmetic expression")
        left, operator, right = match.groups()
        a, b = int(left), int(right)
        if operator == "+":
            result = a + b
        elif operator == "-":
            result = a - b
        elif operator == "*":
            result = a * b
        else:
            if b == 0 or a % b:
                raise AgentInputError("Only exact integer division is supported")
            result = a // b
        answer = str(result)
        if topic == "whole_number_arithmetic":
            steps = [f"Step 1: {expression} = {answer}."]
        else:
            steps = ["Step 1: Apply the integer operation.", f"Step 2: {expression} = {answer}."]

    elif topic == "fractions":
        match = re.fullmatch(r"Calculate: \((\d+/\d+)\) ([+*/-]) \((\d+/\d+)\)", question)
        if not match:
            raise AgentInputError("Invalid fraction question")
        left_text, operator, right_text = match.groups()
        left, right = Fraction(left_text), Fraction(right_text)
        if operator in {"+", "-"}:
            common = math.lcm(left.denominator, right.denominator)
            first = left.numerator * (common // left.denominator)
            second = right.numerator * (common // right.denominator)
            raw = first + second if operator == "+" else first - second
            result = left + right if operator == "+" else left - right
            steps = [
                f"Step 1: Use denominator {common}.",
                f"Step 2: {first}/{common} {operator} {second}/{common} = {raw}/{common}.",
                f"Step 3: Reduce to {_fraction_text(result)}.",
            ]
        elif operator == "*":
            result = left * right
            steps = [
                f"Step 1: Multiply numerators {left.numerator} * {right.numerator}.",
                f"Step 2: Multiply denominators {left.denominator} * {right.denominator}.",
                f"Step 3: Reduce to {_fraction_text(result)}.",
            ]
        else:
            if right == 0:
                raise AgentInputError("Division by zero")
            result = left / right
            steps = [
                f"Step 1: Flip the second fraction to {right.denominator}/{right.numerator}.",
                f"Step 2: Multiply to get {_fraction_text(result)}.",
            ]
        answer = _fraction_text(result)

    elif topic == "decimals":
        match = re.fullmatch(r"Calculate: (-?\d+(?:\.\d+)?) ([+-]) (-?\d+(?:\.\d+)?)", question)
        if not match:
            raise AgentInputError("Invalid decimal question")
        left_text, operator, right_text = match.groups()
        left, right = Decimal(left_text), Decimal(right_text)
        result = left + right if operator == "+" else left - right
        answer = _decimal_text(result)
        steps = [
            "Step 1: Line up the decimal places.",
            f"Step 2: {_decimal_text(left)} {operator} {_decimal_text(right)} = {answer}.",
        ]

    elif topic == "percentages":
        match = re.fullmatch(r"Percentage: (\d+)% of (\d+)", question)
        if not match:
            raise AgentInputError("Invalid percentage question")
        percent, amount = map(int, match.groups())
        answer = _fraction_text(Fraction(percent * amount, 100))
        steps = [f"Step 1: {percent}/100 * {amount} = {answer}."]

    elif topic == "ratios_and_proportions":
        match = re.fullmatch(r"Simplify ratio: (\d+):(\d+)", question)
        if not match:
            raise AgentInputError("Invalid ratio question")
        left, right = map(int, match.groups())
        divisor = math.gcd(left, right)
        answer = f"{left // divisor}:{right // divisor}"
        steps = [
            f"Step 1: Divide both parts by {divisor}.",
            f"Step 2: The simplest ratio is {answer}.",
        ]

    elif topic == "order_of_operations":
        match = re.fullmatch(r"Calculate: (\d+) \+ (\d+) \* (\d+)", question)
        if not match:
            raise AgentInputError("Invalid order-of-operations question")
        first, second, third = map(int, match.groups())
        partial = second * third
        answer = str(first + partial)
        steps = [
            f"Step 1: Multiply first: {second} * {third} = {partial}.",
            f"Step 2: Add: {first} + {partial} = {answer}.",
        ]

    elif topic == "pre_algebra":
        match = re.fullmatch(r"Solve: x ([+-]) (\d+) = (-?\d+)", question)
        if not match:
            raise AgentInputError("Invalid one-step equation")
        operator, offset_text, right_text = match.groups()
        offset, right = int(offset_text), int(right_text)
        value = right - offset if operator == "+" else right + offset
        answer = f"x = {value}"
        steps = [f"Step 1: Isolate x to get {answer}."]

    elif topic == "linear_equations":
        match = re.fullmatch(r"Solve: (\d+)\*x \+ (-?\d+) = (-?\d+)", question)
        if not match:
            raise AgentInputError("Invalid linear equation")
        coefficient, offset, right = map(int, match.groups())
        intermediate = right - offset
        if intermediate % coefficient:
            raise AgentInputError("Equation does not have an integer solution in this agent version")
        value = intermediate // coefficient
        answer = f"x = {value}"
        steps = [
            f"Step 1: Subtract {offset} to get {coefficient}*x = {intermediate}.",
            f"Step 2: Divide by {coefficient} to get {answer}.",
        ]

    elif topic == "inequalities":
        match = re.fullmatch(r"Solve: (\d+)\*x \+ (-?\d+) ([<>]) (-?\d+)", question)
        if not match:
            raise AgentInputError("Invalid linear inequality")
        coefficient_text, offset_text, relation, boundary_text = match.groups()
        coefficient, offset, boundary = int(coefficient_text), int(offset_text), int(boundary_text)
        if coefficient <= 0 or (boundary - offset) % coefficient:
            raise AgentInputError("Unsupported inequality coefficient or non-integer boundary")
        value = (boundary - offset) // coefficient
        answer = f"x {relation} {value}"
        steps = [
            "Step 1: Isolate x at the boundary.",
            f"Step 2: The solution is {answer}.",
        ]

    elif topic == "exponents_and_roots":
        square = re.fullmatch(r"Calculate: (\d+) \*\* 2", question)
        root = re.fullmatch(r"Calculate: sqrt\((\d+)\)", question)
        if square:
            base = int(square.group(1))
            result = base * base
            steps = [f"Step 1: Multiply {base} by itself.", f"Step 2: {base} ** 2 = {result}."]
        elif root:
            radicand = int(root.group(1))
            result = math.isqrt(radicand)
            if result * result != radicand:
                raise AgentInputError("Only exact square roots are supported")
            steps = ["Step 1: Find the exact square root.", f"Step 2: sqrt({radicand}) = {result}."]
        else:
            raise AgentInputError("Invalid exponent/root question")
        answer = str(result)

    elif topic == "basic_geometry":
        area = re.fullmatch(r"Area of rectangle: length (\d+), width (\d+)", question)
        perimeter = re.fullmatch(r"Perimeter of rectangle: length (\d+), width (\d+)", question)
        if area:
            length, width = map(int, area.groups())
            result = length * width
            steps = ["Step 1: Area = length * width.", f"Step 2: {length} * {width} = {result}."]
        elif perimeter:
            length, width = map(int, perimeter.groups())
            result = 2 * (length + width)
            steps = ["Step 1: Perimeter = 2 * (length + width).", f"Step 2: 2 * ({length} + {width}) = {result}."]
        else:
            raise AgentInputError("Invalid rectangle geometry question")
        answer = str(result)

    elif topic == "basic_statistics":
        match = re.fullmatch(r"Mean of: ([0-9, ]+)", question)
        if not match:
            raise AgentInputError("Invalid mean question")
        values = [int(item.strip()) for item in match.group(1).split(",")]
        if not values:
            raise AgentInputError("Mean requires at least one value")
        total = sum(values)
        answer = _fraction_text(Fraction(total, len(values)))
        steps = [f"Step 1: Add the values to get {total}.", f"Step 2: Divide by {len(values)} to get {answer}."]

    elif topic == "basic_probability":
        match = re.fullmatch(r"Probability: (\d+) favorable, (\d+) total", question)
        if not match:
            raise AgentInputError("Invalid probability question")
        favorable, total = map(int, match.groups())
        if total <= 0 or favorable > total:
            raise AgentInputError("Invalid probability counts")
        answer = _fraction_text(Fraction(favorable, total))
        steps = [
            "Step 1: Divide favorable outcomes by total outcomes.",
            f"Step 2: The probability is {answer}.",
        ]
    else:
        raise AgentInputError(f"No solver is registered for topic: {topic}")

    return {
        "answer": answer,
        "steps": steps,
        "knowledge": dict(MATH_KNOWLEDGE[topic]),
        "solver": "deterministic_math_agent",
        "agent_version": AGENT_VERSION,
    }


def run_agent_benchmark(
    count: int,
    seed: int = 20261119,
    topics: tuple[str, ...] = SUPPORTED_TOPICS,
    maximum_seconds: float = 10.0,
) -> dict[str, Any]:
    """Generate, solve, and independently verify a bounded stream of questions."""
    if type(count) is not int or not 1 <= count <= MAX_QUESTIONS_PER_RUN:
        raise AgentInputError(f"count must be an integer from 1 to {MAX_QUESTIONS_PER_RUN}")
    if type(seed) is not int:
        raise AgentInputError("seed must be an integer")
    if not isinstance(topics, tuple) or not topics or len(set(topics)) != len(topics):
        raise AgentInputError("topics must be a non-empty tuple of unique topic names")
    if any(topic not in MATH_KNOWLEDGE for topic in topics):
        raise AgentInputError("topics contains an unsupported topic")
    if isinstance(maximum_seconds, bool) or not isinstance(maximum_seconds, (int, float)) or not math.isfinite(maximum_seconds) or maximum_seconds <= 0:
        raise AgentInputError("maximum_seconds must be a positive finite number")

    started = time.perf_counter()
    generated = solved = verified_correct = 0
    failures: Counter[str] = Counter()
    topic_totals: Counter[str] = Counter()
    topic_correct: Counter[str] = Counter()
    examples: list[dict[str, Any]] = []
    for index in range(count):
        if time.perf_counter() - started >= maximum_seconds:
            break
        topic = topics[index % len(topics)]
        rng = random.Random(seed + index * 1000003 + (index % len(topics)) * 7919)
        source = generate_example(topic, rng, difficulty=1 + (index % 3), sample_index=index)
        generated += 1
        topic_totals[topic] += 1

        # Critical leakage boundary: the solver receives only topic + question.
        question = source["question"]
        try:
            result = solve_question(topic, question)
            solved += 1
            candidate = {
                "sample_id": source["sample_id"],
                "topic": topic,
                "question": question,
                "answer": result["answer"],
                "steps": result["steps"],
            }
            valid, reason = verify_example_detailed(candidate)
            if valid:
                verified_correct += 1
                topic_correct[topic] += 1
                category = "verified_correct"
            else:
                failures["independent_verification_failed"] += 1
                category = "verification_failed"
                result["verification_reason"] = reason
            if len(examples) < 20:
                examples.append({
                    "question": question,
                    "topic": topic,
                    "answer": result["answer"],
                    "steps": result["steps"],
                    "summary": result["knowledge"],
                    "status": category,
                })
        except (AgentInputError, ArithmeticError, ValueError) as error:
            failures[type(error).__name__] += 1

    elapsed = max(time.perf_counter() - started, 1e-12)
    return {
        "agent": "ULTRON Math Agent",
        "agent_version": AGENT_VERSION,
        "mode": "generate_solve_verify_benchmark",
        "seed": seed,
        "requested_questions": count,
        "generated_questions": generated,
        "solved_questions": solved,
        "independently_verified_correct": verified_correct,
        "accuracy_of_generated_questions": verified_correct / generated if generated else 0.0,
        "questions_per_second": generated / elapsed,
        "verified_solutions_per_second": verified_correct / elapsed,
        "elapsed_seconds": elapsed,
        "failures": dict(sorted(failures.items())),
        "by_topic": {
            topic: {
                "generated": topic_totals[topic],
                "verified_correct": topic_correct[topic],
                "accuracy": topic_correct[topic] / topic_totals[topic] if topic_totals[topic] else 0.0,
            }
            for topic in topics
        },
        "sample_solutions": examples,
        "knowledge_base_topics": len(MATH_KNOWLEDGE),
        "training_started": False,
        "model_weights_changed": False,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run ULTRON's deterministic math agent benchmark.")
    parser.add_argument("--count", type=int, default=1000, help="Questions to generate and solve (maximum 50000)")
    parser.add_argument("--seed", type=int, default=20261119)
    parser.add_argument("--seconds", type=float, default=10.0, help="Maximum runtime in seconds")
    parser.add_argument("--output", help="Optional JSON report path")
    args = parser.parse_args(argv)
    try:
        report = run_agent_benchmark(args.count, seed=args.seed, maximum_seconds=args.seconds)
    except (AgentInputError, ValueError) as error:
        parser.error(str(error))
    rendered = json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    if args.output:
        with open(args.output, "w", encoding="utf-8") as output:
            output.write(rendered)
    else:
        print(rendered, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
