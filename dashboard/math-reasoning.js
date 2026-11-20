(function (root) {
  "use strict";

  const STEP_KINDS = {
    whole_number_arithmetic: ["integer_operation"],
    integers: ["signed_integer_operation"],
    fractions: ["fraction_operation", "fraction_reduction"],
    decimals: ["align_decimal_places", "decimal_operation"],
    percentages: ["convert_percentage", "multiply_amount"],
    ratios_and_proportions: ["find_greatest_common_divisor", "reduce_ratio"],
    order_of_operations: ["evaluate_multiplication", "evaluate_addition"],
    pre_algebra: ["apply_inverse_operation", "isolate_variable"],
    linear_equations: ["subtract_constant", "divide_coefficient"],
    inequalities: ["isolate_boundary", "preserve_inequality_direction"],
    exponents_and_roots: ["apply_power_or_root"],
    basic_geometry: ["select_geometry_formula", "substitute_dimensions"],
    basic_statistics: ["sum_values", "divide_by_count"],
    basic_probability: ["count_outcomes", "reduce_probability"],
    median_and_range: ["sort_values", "calculate_median_and_range"],
    simple_interest: ["apply_interest_formula", "substitute_interest_values"],
    unit_conversion: ["select_conversion_factor", "scale_quantity"],
    pythagorean_theorem: ["apply_pythagorean_theorem", "check_exact_root"]
  };

  const PARSERS = {
    whole_number_arithmetic: {
      type: "integer_arithmetic", domain: "integers",
      pattern: /^Calculate: (-?\d+) ([+*/-]) (-?\d+)$/,
      fields: m => ({ left: m[1], operator: m[2], right: m[3] }),
      assumptions: ["Integer arithmetic only", "Division must be exact"]
    },
    integers: {
      type: "signed_integer_arithmetic", domain: "integers",
      pattern: /^Calculate: (-?\d+) ([+*/-]) (-?\d+)$/,
      fields: m => ({ left: m[1], operator: m[2], right: m[3] }),
      assumptions: ["Operands are signed integers", "Division must be exact"]
    },
    fractions: {
      type: "fraction_arithmetic", domain: "rational_numbers",
      pattern: /^Calculate: \((\d+\/\d+)\) ([+*/-]) \((\d+\/\d+)\)$/,
      fields: m => ({ left: m[1], operator: m[2], right: m[3] }),
      assumptions: ["Denominators are non-zero", "Fractions are reduced exactly"]
    },
    decimals: {
      type: "decimal_arithmetic", domain: "finite_decimals",
      pattern: /^Calculate: (-?\d+(?:\.\d+)?) ([+-]) (-?\d+(?:\.\d+)?)$/,
      fields: m => ({ left: m[1], operator: m[2], right: m[3] }),
      assumptions: ["Only decimal addition and subtraction are supported", "Decimal arithmetic uses exact scaled integers"]
    },
    percentages: {
      type: "percentage_of_amount", domain: "rational_numbers",
      pattern: /^Percentage: (\d+)% of (\d+)$/,
      fields: m => ({ percentage: m[1], amount: m[2] }),
      assumptions: ["Percentage is a non-negative whole number"]
    },
    ratios_and_proportions: {
      type: "ratio_simplification", domain: "non_negative_integers",
      pattern: /^Simplify ratio: (\d+):(\d+)$/,
      fields: m => ({ first: m[1], second: m[2] }),
      assumptions: ["Both ratio terms are non-negative", "The ratio 0:0 is undefined"]
    },
    order_of_operations: {
      type: "order_of_operations", domain: "non_negative_integers",
      pattern: /^Calculate: (\d+) \+ (\d+) \* (\d+)$/,
      fields: m => ({ addend: m[1], multiplicand: m[2], multiplier: m[3] }),
      assumptions: ["Multiplication is evaluated before addition"]
    },
    pre_algebra: {
      type: "one_step_linear_equation", domain: "integers",
      pattern: /^Solve: x ([+-]) (\d+) = (-?\d+)$/,
      fields: m => ({ variable: "x", operator: m[1], offset: m[2], result: m[3] }),
      assumptions: ["Variable is x", "Solution is an integer"]
    },
    linear_equations: {
      type: "two_step_linear_equation", domain: "integers",
      pattern: /^Solve: (\d+)\*x \+ (-?\d+) = (-?\d+)$/,
      fields: m => ({ coefficient: m[1], constant: m[2], result: m[3] }),
      assumptions: ["Coefficient is non-zero", "Solution is an integer"]
    },
    inequalities: {
      type: "linear_inequality", domain: "real_numbers",
      pattern: /^Solve: (\d+)\*x \+ (-?\d+) ([<>]) (-?\d+)$/,
      fields: m => ({ coefficient: m[1], constant: m[2], operator: m[3], boundary: m[4] }),
      assumptions: ["Coefficient is positive", "Dividing by the coefficient does not reverse the inequality"]
    },
    exponents_and_roots: {
      type: "integer_square_or_square_root", domain: "non_negative_integers",
      pattern: /^(?:Calculate: (\d+) \*\* 2|Calculate: sqrt\((\d+)\))$/,
      fields: m => m[1] ? ({ operation: "square", value: m[1] }) : ({ operation: "square_root", value: m[2] }),
      assumptions: ["Square roots must be exact non-negative integers"]
    },
    basic_geometry: {
      type: "rectangle_measurement", domain: "non_negative_integer_lengths",
      pattern: /^(Area|Perimeter) of rectangle: length (\d+), width (\d+)$/,
      fields: m => ({ measure: m[1].toLowerCase(), length: m[2], width: m[3] }),
      assumptions: ["Shape is a Euclidean rectangle", "Lengths are non-negative integers"]
    },
    basic_statistics: {
      type: "arithmetic_mean", domain: "non_negative_integer_dataset",
      pattern: /^Mean of: ([0-9, ]+)$/,
      fields: m => ({ values: m[1].split(",").map(value => value.trim()) }),
      assumptions: ["Dataset contains comma-separated whole numbers", "Dataset is non-empty"]
    },
    basic_probability: {
      type: "equally_likely_probability", domain: "rational_numbers",
      pattern: /^Probability: (\d+) favorable, (\d+) total$/,
      fields: m => ({ favorable: m[1], total: m[2] }),
      assumptions: ["Outcomes are equally likely", "0 ≤ favorable ≤ total", "Total is positive"]
    },
    median_and_range: {
      type: "median_and_range", domain: "non_negative_integer_dataset",
      pattern: /^Median and range of: ([0-9, ]+)$/,
      fields: m => ({ values: m[1].split(",").map(value => value.trim()) }),
      assumptions: ["Exactly five whole-number values are required"]
    },
    simple_interest: {
      type: "simple_interest", domain: "non_negative_rational_amounts",
      pattern: /^Simple interest: principal (\d+), rate (\d+)%, time (\d+) years$/,
      fields: m => ({ principal: m[1], annualRatePercent: m[2], years: m[3] }),
      assumptions: ["Simple interest only; no compounding", "Rate is an annual percentage"]
    },
    unit_conversion: {
      type: "metric_unit_conversion", domain: "metric_quantities",
      pattern: /^Convert: (\d+) (m|cm|kg) to (cm|mm|g)$/,
      fields: m => ({ amount: m[1], fromUnit: m[2], toUnit: m[3] }),
      assumptions: ["Only explicitly supported metric conversions are accepted"]
    },
    pythagorean_theorem: {
      type: "right_triangle_hypotenuse", domain: "non_negative_integer_lengths",
      pattern: /^Hypotenuse of right triangle: legs (\d+), (\d+)$/,
      fields: m => ({ firstLeg: m[1], secondLeg: m[2] }),
      assumptions: ["Triangle is right-angled", "Hypotenuse must be an exact integer"]
    }
  };

  function deepFreeze(value) {
    if (!value || typeof value !== "object" || Object.isFrozen(value)) return value;
    Object.freeze(value);
    Object.keys(value).forEach(key => deepFreeze(value[key]));
    return value;
  }

  deepFreeze(PARSERS);
  deepFreeze(STEP_KINDS);
  const SUPPORTED_TOPICS = Object.freeze(Object.keys(PARSERS));

  function isPerfectSquare(value) {
    if (value < 0n) return false;
    let low = 0n;
    let high = value + 1n;
    while (low + 1n < high) {
      const middle = (low + high) / 2n;
      if (middle * middle <= value) low = middle;
      else high = middle;
    }
    return low * low === value;
  }

  function parseProblem(topic, question) {
    const parser = PARSERS[topic];
    if (!parser || typeof question !== "string" || !question.trim() || question.length > 1000) return null;
    const normalizedQuestion = question.trim();
    const match = parser.pattern.exec(normalizedQuestion);
    if (!match) return null;
    const operands = parser.fields(match);
    if (operands.values && (operands.values.length === 0 || operands.values.some(value => !/^\d+$/.test(value)))) return null;
    if (topic === "whole_number_arithmetic" || topic === "integers") {
      if (operands.operator === "/") {
        const left = BigInt(operands.left);
        const right = BigInt(operands.right);
        if (right === 0n || left % right !== 0n) return null;
      }
    }
    if (topic === "fractions") {
      for (const key of ["left", "right"]) {
        const [numerator, denominator] = operands[key].split("/");
        if (denominator === "0") return null;
        if (key === "right" && operands.operator === "/" && numerator === "0") return null;
      }
    }
    if (topic === "linear_equations") {
      const coefficient = BigInt(operands.coefficient);
      if (coefficient === 0n || (BigInt(operands.result) - BigInt(operands.constant)) % coefficient !== 0n) return null;
    }
    if (topic === "inequalities") {
      const coefficient = BigInt(operands.coefficient);
      if (coefficient <= 0n || (BigInt(operands.boundary) - BigInt(operands.constant)) % coefficient !== 0n) return null;
    }
    if (topic === "exponents_and_roots" && operands.operation === "square_root" && !isPerfectSquare(BigInt(operands.value))) return null;
    if (topic === "pythagorean_theorem") {
      const first = BigInt(operands.firstLeg);
      const second = BigInt(operands.secondLeg);
      if (!isPerfectSquare(first * first + second * second)) return null;
    }
    if (topic === "ratios_and_proportions" && operands.first === "0" && operands.second === "0") return null;
    if (topic === "basic_probability" && (operands.total === "0" || BigInt(operands.favorable) > BigInt(operands.total))) return null;
    if (topic === "median_and_range" && operands.values.length !== 5) return null;
    if (topic === "unit_conversion" && !({ "m:cm": true, "cm:mm": true, "kg:g": true })[operands.fromUnit + ":" + operands.toUnit]) return null;
    return deepFreeze({
      schemaVersion: 1,
      topic,
      problemType: parser.type,
      domain: parser.domain,
      operation: parser.type,
      sourceQuestion: question,
      normalizedQuestion,
      operands,
      assumptions: parser.assumptions.slice()
    });
  }

  function buildPlan(topic, solved, verified) {
    const kinds = STEP_KINDS[topic] || [];
    return {
      schemaVersion: 1,
      steps: solved.steps.map((explanation, index) => ({
        stepId: "step-" + (index + 1),
        kind: kinds[index] || "deterministic_operation",
        explanation,
        replay: {
          status: "matched",
          scope: "Exact deterministic replay against the existing solver output; not a formal proof."
        }
      })),
      finalAnswer: {
        value: solved.answer,
        verification: {
          status: verified ? "passed" : "failed",
          method: "Independent topic-specific answer verifier",
          scope: "Final answer only; intermediate explanation text is not a formal proof."
        }
      }
    };
  }

  function reason(agent, topic, question) {
    if (!agent || typeof agent.solve !== "function" || typeof agent.verify !== "function") {
      return { kind: "abstain", message: "A compatible mathematics solver is required.", verified: false };
    }
    const problem = parseProblem(topic, question);
    if (!problem) return { kind: "abstain", message: "The question does not match a validated structured problem format for this topic.", verified: false };
    try {
      const solved = agent.solve(topic, problem.normalizedQuestion);
      const verified = Boolean(agent.verify(topic, problem.normalizedQuestion, solved.answer));
      const plan = buildPlan(topic, solved, verified);
      return {
        kind: verified ? "solution" : "unverified",
        problem,
        plan,
        answer: solved.answer,
        knowledge: solved.knowledge,
        steps: solved.steps.slice(),
        verification: {
          input: "passed",
          domain: "passed",
          finalAnswer: verified ? "passed" : "failed",
          scope: "Typed input validation and independent final-answer verification. Explanatory steps are replayed, not formally proven."
        },
        verified
      };
    } catch (error) {
      return { kind: "abstain", message: error && error.message ? error.message : "The structured solver could not validate this problem.", problem, verified: false };
    }
  }

  function verifyReport(agent, report) {
    if (!report || !report.problem || typeof report.problem.topic !== "string" || typeof report.problem.sourceQuestion !== "string") {
      return { valid: false, reason: "A structured problem report is required." };
    }
    const replayed = reason(agent, report.problem.topic, report.problem.sourceQuestion);
    if (replayed.kind !== "solution" && replayed.kind !== "unverified") {
      return { valid: false, reason: "The original problem no longer reproduces as a supported problem." };
    }
    const same = replayed.kind === report.kind &&
      replayed.verified === report.verified &&
      JSON.stringify(replayed.problem) === JSON.stringify(report.problem) &&
      JSON.stringify(replayed.plan) === JSON.stringify(report.plan) &&
      replayed.answer === report.answer &&
      JSON.stringify(replayed.knowledge) === JSON.stringify(report.knowledge) &&
      JSON.stringify(replayed.steps) === JSON.stringify(report.steps) &&
      JSON.stringify(replayed.verification) === JSON.stringify(report.verification);
    return {
      valid: same,
      reason: same ? "Structured report reproduced exactly." : "The structured report differs from deterministic replay.",
      replayedAnswer: replayed.answer,
      verified: replayed.verified
    };
  }

  const api = { SUPPORTED_TOPICS, parseProblem, reason, verifyReport };
  if (typeof module !== "undefined" && module.exports) module.exports = api;
  root.ULTRON_REASONING = api;
})(typeof globalThis !== "undefined" ? globalThis : this);
