"use strict";
const test = require("node:test");
const assert = require("node:assert/strict");
const runtime = require("../dashboard/runtime.js");

test("public runtime exports only the animation scheduler", () => {
  assert.deepEqual(Object.keys(runtime), ["scheduleFrame"]);
  assert.equal(Object.isFrozen(runtime), true);
});

test("chart scheduler falls back synchronously when animation frames are unavailable", () => {
  let called = 0;
  assert.equal(runtime.scheduleFrame(() => { called += 1; }, {}), null);
  assert.equal(called, 1);
});

test("chart scheduler uses requestAnimationFrame when available", () => {
  let queued = null;
  const handle = runtime.scheduleFrame(() => {}, {
    requestAnimationFrame: callback => { queued = callback; return 7; }
  });
  assert.equal(typeof queued, "function");
  assert.equal(handle, 7);
});

test("chart scheduler rejects a non-function callback", () => {
  assert.throws(() => runtime.scheduleFrame(null, {}), /drawing callback/);
});
