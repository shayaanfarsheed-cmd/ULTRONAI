from __future__ import annotations

import ast
import hashlib
import math
import re
from decimal import Decimal, InvalidOperation
from typing import Any, Mapping


def _independent_gcd(left: int, right: int) -> int:
    first, second = abs(left), abs(right)
    while second:
        first, second = second, first % second
    return first


def _normalize(numerator: int, denominator: int = 1) -> tuple[int, int]:
    if denominator == 0:
        raise ZeroDivisionError("Division by zero")
    if denominator < 0:
        numerator = -numerator
        denominator = -denominator
    divisor = math.gcd(numerator, denominator)
    return numerator // divisor, denominator // divisor


def _decimal_pair(value: str) -> tuple[int, int]:
    decimal_value = Decimal(value)
    numerator, denominator = decimal_value.as_integer_ratio()
    return _normalize(numerator, denominator)


def _parse_number(value: str) -> tuple[int, int]:
    text = value.strip()
    if "/" in text:
        numerator, denominator = text.split("/", 1)
        return _normalize(int(numerator.strip()), int(denominator.strip()))
    return _decimal_pair(text)


def _add(left: tuple[int, int], right: tuple[int, int]) -> tuple[int, int]:
    return _normalize(left[0] * right[1] + right[0] * left[1], left[1] * right[1])


def _subtract(left: tuple[int, int], right: tuple[int, int]) -> tuple[int, int]:
    return _normalize(left[0] * right[1] - right[0] * left[1], left[1] * right[1])


def _multiply(left: tuple[int, int], right: tuple[int, int]) -> tuple[int, int]:
    return _normalize(left[0] * right[0], left[1] * right[1])


def _divide(left: tuple[int, int], right: tuple[int, int]) -> tuple[int, int]:
    return _normalize(left[0] * right[1], left[1] * right[0])


def _evaluate_node(node: ast.AST, variables: Mapping[str, tuple[int, int]] | None = None) -> tuple[int, int]:
    values = {} if variables is None else variables
    if isinstance(node, ast.Expression):
        return _evaluate_node(node.body, values)
    if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)) and not isinstance(node.value, bool):
        return _decimal_pair(str(node.value))
    if isinstance(node, ast.Name) and node.id in values:
        return values[node.id]
    if isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.UAdd):
        return _evaluate_node(node.operand, values)
    if isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.USub):
        numerator, denominator = _evaluate_node(node.operand, values)
        return _normalize(-numerator, denominator)
    if isinstance(node, ast.BinOp):
        left = _evaluate_node(node.left, values)
        right = _evaluate_node(node.right, values)
        if isinstance(node.op, ast.Add):
            return _add(left, right)
        if isinstance(node.op, ast.Sub):
            return _subtract(left, right)
        if isinstance(node.op, ast.Mult):
            return _multiply(left, right)
        if isinstance(node.op, ast.Div):
            return _divide(left, right)
        if isinstance(node.op, ast.Pow) and right[1] == 1 and -8 <= right[0] <= 8:
            exponent = right[0]
            if left[0] == 0 and exponent < 0:
                raise ZeroDivisionError("Zero cannot have a negative exponent")
            if exponent >= 0:
                return _normalize(left[0] ** exponent, left[1] ** exponent)
            return _normalize(left[1] ** (-exponent), left[0] ** (-exponent))
    if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == "sqrt" and len(node.args) == 1:
        numerator, denominator = _evaluate_node(node.args[0], values)
        if numerator < 0:
            raise ValueError("Square root of a negative value")
        root_numerator = math.isqrt(numerator)
        root_denominator = math.isqrt(denominator)
        if root_numerator * root_numerator != numerator or root_denominator * root_denominator != denominator:
            raise ValueError("Only exact square roots are supported")
        return _normalize(root_numerator, root_denominator)
    raise ValueError("Unsupported expression syntax")


def _evaluate_expression(expression: str, variables: Mapping[str, tuple[int, int]] | None = None) -> tuple[int, int]:
    return _evaluate_node(ast.parse(expression, mode="eval"), variables)


def _compare(left: tuple[int, int], right: tuple[int, int], operator: ast.cmpop) -> bool:
    difference = left[0] * right[1] - right[0] * left[1]
    if isinstance(operator, ast.Lt):
        return difference < 0
    if isinstance(operator, ast.Gt):
        return difference > 0
    if isinstance(operator, ast.LtE):
        return difference <= 0
    if isinstance(operator, ast.GtE):
        return difference >= 0
    if isinstance(operator, ast.Eq):
        return difference == 0
    raise ValueError("Unsupported comparison")


def _sample_id(topic: str, question: str) -> str:
    return hashlib.sha256(f"{topic}|{question}".encode("utf-8")).hexdigest()[:16]


def verify_example_detailed(example: Mapping[str, Any]) -> tuple[bool, str]:
    try:
        topic = str(example["topic"])
        question = str(example["question"])
        answer = str(example["answer"]).strip()
        steps = example["steps"]
        if not question or not answer:
            return False, "Question or answer is empty"
        if not isinstance(steps, list) or not steps or any(not isinstance(step, str) or not step.strip() for step in steps):
            return False, "Solution steps are missing or invalid"
        if answer not in steps[-1]:
            return False, "Final solution step does not contain the answer"
        if example.get("sample_id") != _sample_id(topic, question):
            return False, "Sample identifier does not match the question"

        if topic in {"whole_number_arithmetic", "fractions", "decimals", "integers", "order_of_operations", "exponents_and_roots"}:
            expression = question.split(":", 1)[1].strip()
            expected = _evaluate_expression(expression)
            observed = _parse_number(answer)
            return expected == observed, "Expression result matches" if expected == observed else "Expression result does not match"

        if topic == "percentages":
            match = re.fullmatch(r"Percentage: (\d+)% of (\d+)", question)
            if not match:
                return False, "Percentage question format is invalid"
            percent, amount = map(int, match.groups())
            expected = _normalize(percent * amount, 100)
            observed = _parse_number(answer)
            return expected == observed, "Percentage result matches" if expected == observed else "Percentage result does not match"

        if topic == "ratios_and_proportions":
            match = re.fullmatch(r"Simplify ratio: (\d+):(\d+)", question)
            if not match:
                return False, "Ratio question format is invalid"
            left, right = map(int, match.groups())
            divisor = _independent_gcd(left, right)
            expected = f"{left // divisor}:{right // divisor}"
            return answer == expected, "Ratio is simplified" if answer == expected else "Ratio is not simplified correctly"

        if topic in {"pre_algebra", "linear_equations"}:
            match = re.fullmatch(r"Solve: (.+) = (.+)", question)
            answer_match = re.fullmatch(r"x = (-?\d+(?:\.\d+)?(?:/\d+)?)", answer)
            if not match or not answer_match:
                return False, "Equation format is invalid"
            variable_value = _parse_number(answer_match.group(1))
            left = _evaluate_expression(match.group(1), {"x": variable_value})
            right = _evaluate_expression(match.group(2), {"x": variable_value})
            return left == right, "Substitution satisfies equation" if left == right else "Substitution does not satisfy equation"

        if topic == "inequalities":
            match = re.fullmatch(r"Solve: (.+) ([<>]) (.+)", question)
            answer_match = re.fullmatch(r"x ([<>]) (-?\d+(?:\.\d+)?(?:/\d+)?)", answer)
            if not match or not answer_match:
                return False, "Inequality format is invalid"
            left_expression, relation, right_expression = match.groups()
            answer_relation, boundary_text = answer_match.groups()
            boundary = _parse_number(boundary_text)
            if relation != answer_relation:
                return False, "Inequality direction is incorrect"
            left_at_boundary = _evaluate_expression(left_expression, {"x": boundary})
            right_at_boundary = _evaluate_expression(right_expression, {"x": boundary})
            if left_at_boundary != right_at_boundary:
                return False, "Reported boundary does not satisfy equality"
            one = (1, 1)
            below = _subtract(boundary, one)
            above = _add(boundary, one)
            operator = ast.Lt() if relation == "<" else ast.Gt()
            below_result = _compare(_evaluate_expression(left_expression, {"x": below}), _evaluate_expression(right_expression, {"x": below}), operator)
            above_result = _compare(_evaluate_expression(left_expression, {"x": above}), _evaluate_expression(right_expression, {"x": above}), operator)
            expected = below_result and not above_result if relation == "<" else above_result and not below_result
            return expected, "Inequality boundary and direction match" if expected else "Inequality boundary or direction is incorrect"

        if topic == "basic_geometry":
            area = re.fullmatch(r"Area of rectangle: length (\d+), width (\d+)", question)
            perimeter = re.fullmatch(r"Perimeter of rectangle: length (\d+), width (\d+)", question)
            if area:
                length, width = map(int, area.groups())
                expected = str(length * width)
            elif perimeter:
                length, width = map(int, perimeter.groups())
                expected = str(2 * (length + width))
            else:
                return False, "Geometry question format is invalid"
            return answer == expected, "Geometry result matches" if answer == expected else "Geometry result does not match"

        if topic == "basic_statistics":
            match = re.fullmatch(r"Mean of: ([0-9, ]+)", question)
            if not match:
                return False, "Statistics question format is invalid"
            values = [int(item.strip()) for item in match.group(1).split(",")]
            expected = _normalize(sum(values), len(values))
            observed = _parse_number(answer)
            return expected == observed, "Mean result matches" if expected == observed else "Mean result does not match"

        if topic == "basic_probability":
            match = re.fullmatch(r"Probability: (\d+) favorable, (\d+) total", question)
            if not match:
                return False, "Probability question format is invalid"
            favorable, total = map(int, match.groups())
            if total <= 0 or favorable < 0 or favorable > total:
                return False, "Probability counts are invalid"
            expected = _normalize(favorable, total)
            observed = _parse_number(answer)
            return expected == observed, "Probability result matches" if expected == observed else "Probability result does not match"

        return False, f"Unsupported topic: {topic}"
    except (ArithmeticError, InvalidOperation, KeyError, TypeError, ValueError, SyntaxError):
        return False, "Verification error"


def verify_example(example: Mapping[str, Any]) -> bool:
    return verify_example_detailed(example)[0]
