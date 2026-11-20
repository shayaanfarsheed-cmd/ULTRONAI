"use strict";
const test = require("node:test");
const assert = require("node:assert/strict");
const bank = require("../dashboard/axiom-bank.js");
const agent = require("../dashboard/math-agent.js");

test("axiom bank has stable identifiers and named formal systems", () => {
  assert.ok(bank.count >= 35);
  assert.equal(new Set(bank.entries.map(x => x.id)).size, bank.count);
  for (const entry of bank.entries) {
    assert.ok(bank.systems[entry.system], entry.id);
    assert.ok(entry.references.length > 0, entry.id);
    assert.ok(entry.formal.length > 10, entry.id);
    assert.ok(["foundation", "proof", "advanced"].includes(entry.level), entry.id);
  }
});

test("field laws and ordered-field assumptions remain separately scoped", () => {
  assert.equal(bank.get("FIELD-08").system, "REAL_FIELD");
  assert.match(bank.get("FIELD-08").formal, /a≠0/);
  assert.equal(bank.get("ORDER-04").system, "ORDERED_FIELD");
  assert.match(bank.get("ORDER-04").formal, /0<c/);
  assert.equal(bank.get("COMPLETE-01").system, "COMPLETE_REAL");
});

test("topic lookup returns only explicitly tagged axioms", () => {
  const fractionAxioms = bank.forTopic("fractions");
  assert.ok(fractionAxioms.some(x => x.id === "FIELD-08"));
  assert.ok(fractionAxioms.every(x => x.system === "REAL_FIELD"));
  assert.deepEqual(bank.forTopic("unknown-topic"), []);
});

test("probability additivity explicitly requires pairwise disjoint events", () => {
  const axiom = bank.get("PROB-03");
  assert.match(axiom.formal, /pairwise-disjoint/);
  assert.match(axiom.teaching, /disjointness/);
});

test("Euclidean parallel postulate is not represented as universal geometry", () => {
  const axiom = bank.get("EUCLID-05");
  assert.equal(axiom.system, "EUCLID_GEOMETRY");
  assert.match(axiom.teaching, /non-Euclidean/);
});

test("ZFC choice is distinguished from ZF and schemas are identified", () => {
  assert.equal(bank.get("ZFC-10").system, "ZFC");
  assert.match(bank.get("ZFC-08").teaching, /schema/);
  assert.match(bank.get("ZFC-07").teaching, /unrestricted comprehension/);
});

test("search filters by system, topic and text without mutating the bank", () => {
  assert.ok(bank.list({ system: "KOLMOGOROV" }).every(x => x.system === "KOLMOGOROV"));
  assert.ok(bank.list({ query: "induction" }).some(x => x.id === "PEANO-04"));
  assert.ok(Object.isFrozen(bank.entries));
  assert.ok(Object.isFrozen(bank.get("FIELD-01")));
});

test("unknown axiom lookup returns a safe not-found result", () => {
  assert.equal(bank.get("NOT-AN-AXIOM"), null);
  assert.equal(bank.explain("NOT-AN-AXIOM").found, false);
});

test("axiom bank covers all topics that claim a foundation association", () => {
  const covered = new Set(bank.entries.flatMap(x => x.topics));
  for (const topic of agent.TOPIC_KEYS) {
    assert.ok(typeof agent.TOPICS[topic].label === "string", topic);
    assert.ok(covered.has(topic) || topic === "median_and_range" || topic === "simple_interest" || topic === "unit_conversion" || topic === "pythagorean_theorem", topic);
  }
});
