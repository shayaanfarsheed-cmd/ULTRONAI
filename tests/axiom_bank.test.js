"use strict";
const test = require("node:test");
const assert = require("node:assert/strict");
const bank = require("../dashboard/axiom-bank.js");
const agent = require("../dashboard/math-agent.js");

test("axiom bank has stable identifiers and named formal systems", () => {
  assert.ok(bank.count >= 37);
  assert.equal(bank.get("PEANO-00").system, "PEANO_N");
  assert.equal(new Set(bank.entries.map(x => x.id)).size, bank.count);
  for (const entry of bank.entries) {
    assert.ok(bank.systems[entry.system], entry.id);
    assert.ok(entry.references.length > 0, entry.id);
    assert.ok(entry.formal.length > 10, entry.id);
    assert.ok(["foundation", "proof", "advanced"].includes(entry.level), entry.id);
    assert.ok(["axiom", "schema"].includes(entry.category), entry.id);
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

test("every topic tag belongs to the registered foundation curriculum", () => {
  const known = new Set(agent.TOPIC_KEYS);
  for (const entry of bank.entries) {
    for (const topic of entry.topics) assert.ok(known.has(topic), entry.id + " -> " + topic);
  }
  assert.ok(bank.forTopic("basic_geometry").some(x => x.id === "EUCLID-01"));
  assert.ok(bank.forTopic("basic_probability").some(x => x.id === "PROB-01"));
});
