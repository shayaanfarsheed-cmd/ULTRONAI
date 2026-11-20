"use strict";
const test = require("node:test");
const assert = require("node:assert/strict");
const agent = require("../dashboard/math-agent.js");
const reasoning = require("../dashboard/math-reasoning.js");
const tutorApi = require("../dashboard/math-tutor.js");

function create() { return tutorApi.createTutor(agent, reasoning); }

test("prerequisite graph covers all 18 topics and is acyclic", () => {
  assert.equal(Object.keys(tutorApi.PREREQUISITES).length, 18);
  assert.equal(tutorApi.validateGraph(agent.TOPIC_KEYS), true);
  assert.deepEqual(tutorApi.PREREQUISITES.pythagorean_theorem, ["basic_geometry", "exponents_and_roots"]);
});

test("progressive hints are grounded in verified solution knowledge", () => {
  const tutor = create();
  const hints = tutor.getHints("fractions", "Calculate: (1/3) + (1/6)");
  assert.equal(hints.available, true);
  assert.equal(hints.verifiedSource, true);
  assert.deepEqual(hints.hints.map(item => item.level), [1, 2, 3]);
  assert.match(hints.hints[0].text, /common denominator/i);
  assert.match(hints.hints[1].text, /reduced/i);
  assert.equal(tutor.getHints("fractions", "unsupported").available, false);
});

test("mistake diagnosis refuses to infer a misconception from a final answer", () => {
  const tutor = create();
  const result = tutor.diagnose("fractions", "Calculate: (1/3) + (1/6)", "2/3");
  assert.equal(result.status, "incorrect_unclassified");
  assert.equal(result.misconception, null);
  assert.match(result.message, /cannot identify the cause/i);
});

test("correct answers are independently verified before being diagnosed", () => {
  const tutor = create();
  const result = tutor.diagnose("whole_number_arithmetic", "Calculate: 12 + 5", "17");
  assert.equal(result.status, "correct");
  assert.equal(result.expected, "17");
});

test("unsupported prompts abstain and never invent a diagnosis", () => {
  const tutor = create();
  const result = tutor.diagnose("decimals", "Calculate: 1.2 * 3", "3.6");
  assert.equal(result.status, "unsupported");
  assert.equal(result.misconception, null);
});

test("mastery, streak and review intervals advance deterministically", () => {
  const tutor = create();
  assert.equal(tutor.recordAttempt("fractions", true).dueAt, 2);
  assert.equal(tutor.recordAttempt("fractions", true).dueAt, 4);
  assert.equal(tutor.recordAttempt("fractions", true).dueAt, 7);
  const failed = tutor.recordAttempt("fractions", false);
  assert.equal(failed.streak, 0);
  assert.equal(failed.dueAt, 5);
  assert.equal(tutor.getSnapshot().topics.find(x => x.topic === "fractions").accuracy, 0.75);
});

test("review becomes due on session turn and is selected before unseen topics", () => {
  const tutor = create();
  tutor.recordAttempt("whole_number_arithmetic", false);
  tutor.recordAttempt("fractions", true);
  assert.ok(tutor.getSnapshot().dueTopics.includes("whole_number_arithmetic"));
  assert.equal(tutor.nextExercise().topic, "whole_number_arithmetic");
});

test("adaptive sequencing respects prerequisite readiness and weakest mastery", () => {
  const tutor = create();
  assert.equal(tutor.nextExercise().topic, "whole_number_arithmetic");
  tutor.recordAttempt("whole_number_arithmetic", true);
  tutor.recordAttempt("whole_number_arithmetic", true);
  const selected = tutor.nextExercise();
  assert.equal(tutor.getPrerequisites("fractions")[0].ready, true);
  assert.equal(selected.topic, "fractions");
  assert.equal(selected.difficulty, "foundation_fixed");
});

test("all generated exercises across all topics pass the independent verifier", () => {
  const tutor = create();
  for (const topic of agent.TOPIC_KEYS) {
    const exercise = Object.freeze({ topic, question: agent.generate(topic, 71) });
    const solved = agent.solve(exercise.topic, exercise.question);
    assert.equal(agent.verify(exercise.topic, exercise.question, solved.answer), true, topic);
  }
  for (let i = 0; i < 18; i++) {
    const exercise = tutor.nextExercise();
    assert.ok(agent.TOPIC_KEYS.includes(exercise.topic));
    const solved = agent.solve(exercise.topic, exercise.question);
    assert.equal(agent.verify(exercise.topic, exercise.question, solved.answer), true);
  }
});

test("session reset clears mastery, review schedule and deterministic seed", () => {
  const tutor = create();
  tutor.recordAttempt("whole_number_arithmetic", true);
  tutor.recordAttempt("fractions", false);
  const before = tutor.getSnapshot();
  assert.ok(before.turn > 0);
  assert.equal(before.storage, "memory_only");
  assert.equal(before.rawQuestionsPersisted, false);
  assert.equal(before.rawAnswersPersisted, false);
  const reset = tutor.reset();
  assert.equal(reset.turn, 0);
  assert.deepEqual(reset.dueTopics, []);
  assert.equal(reset.topics.every(x => x.attempts === 0 && x.dueAt === null), true);
  assert.equal(tutor.nextExercise().question, agent.generate("whole_number_arithmetic", 1));
});

test("invalid attempts and unknown topics are rejected", () => {
  const tutor = create();
  assert.throws(() => tutor.recordAttempt("unknown", true));
  assert.throws(() => tutor.recordAttempt("fractions", "yes"));
  assert.throws(() => tutor.getPrerequisites("unknown"));
});
