"use strict";
const test = require("node:test");
const assert = require("node:assert/strict");
const agent = require("../dashboard/math-agent.js");
const reasoning = require("../dashboard/math-reasoning.js");

test("typed problem parsing covers all 18 registered foundation topics", () => {
  for (const topic of agent.TOPIC_KEYS) {
    const question = agent.generate(topic, 37);
    const problem = reasoning.parseProblem(topic, question);
    assert.ok(problem, topic + " should parse into a typed problem");
    assert.equal(problem.schemaVersion, 1);
    assert.equal(problem.topic, topic);
    assert.ok(problem.problemType);
    assert.ok(problem.domain);
    assert.ok(problem.assumptions.length > 0);
    assert.equal(problem.sourceQuestion, question);
  }
});

test("reasoning kernel produces a structured, independently verified report for every topic", () => {
  for (const topic of agent.TOPIC_KEYS) {
    const question = agent.generate(topic, 41);
    const report = reasoning.reason(agent, topic, question);
    assert.equal(report.kind, "solution", topic);
    assert.equal(report.verified, true, topic);
    assert.equal(report.verification.input, "passed");
    assert.equal(report.verification.domain, "passed");
    assert.equal(report.verification.finalAnswer, "passed");
    assert.equal(report.plan.finalAnswer.value, report.answer);
    assert.ok(report.plan.steps.length > 0);
    assert.ok(report.plan.steps.every(step => step.replay.status === "matched"));
    assert.ok(report.plan.steps.every(step => /not a formal proof/.test(step.replay.scope)));
  }
});

test("structured reports reproduce exactly and detect tampering", () => {
  const question = agent.generate("fractions", 12);
  const report = reasoning.reason(agent, "fractions", question);
  assert.equal(reasoning.verifyReport(agent, report).valid, true);
  const altered = JSON.parse(JSON.stringify(report));
  altered.plan.steps[0].explanation = "tampered explanation";
  assert.equal(reasoning.verifyReport(agent, altered).valid, false);
  const alteredAnswer = JSON.parse(JSON.stringify(report));
  alteredAnswer.answer = "999";
  assert.equal(reasoning.verifyReport(agent, alteredAnswer).valid, false);
});

test("typed problem records are immutable and preserve source questions", () => {
  const question = agent.generate("linear_equations", 17);
  const problem = reasoning.parseProblem("linear_equations", question);
  assert.ok(Object.isFrozen(problem));
  assert.ok(Object.isFrozen(problem.operands));
  assert.ok(Object.isFrozen(problem.assumptions));
  assert.equal(problem.sourceQuestion, question);
  assert.throws(() => { problem.operands.coefficient = "0"; });
});

test("invalid domains and malformed formats abstain before producing an answer", () => {
  const invalid = [
    ["fractions", "Calculate: (1/0) + (1/2)"],
    ["ratios_and_proportions", "Simplify ratio: 0:0"],
    ["basic_probability", "Probability: 7 favorable, 6 total"],
    ["basic_probability", "Probability: 1 favorable, 0 total"],
    ["median_and_range", "Median and range of: 1, 2, 3"],
    ["unit_conversion", "Convert: 2 m to g"],
    ["decimals", "Calculate: 1.2 * 3"]
  ];
  for (const [topic, question] of invalid) {
    assert.equal(reasoning.parseProblem(topic, question), null, topic + ": " + question);
    assert.equal(reasoning.reason(agent, topic, question).kind, "abstain");
  }
});

test("unsupported topics, non-text input and oversized questions abstain", () => {
  assert.equal(reasoning.parseProblem("unknown", "Calculate: 1 + 1"), null);
  assert.equal(reasoning.parseProblem("fractions", ""), null);
  assert.equal(reasoning.parseProblem("fractions", "x".repeat(1001)), null);
  assert.equal(reasoning.reason(agent, "unknown", "Calculate: 1 + 1").kind, "abstain");
});

test("verification scope does not claim intermediate steps are formal proofs", () => {
  const question = agent.generate("linear_equations", 21);
  const report = reasoning.reason(agent, "linear_equations", question);
  assert.match(report.verification.scope, /not formally proven/);
  assert.match(report.plan.finalAnswer.verification.scope, /not a formal proof/);
});
