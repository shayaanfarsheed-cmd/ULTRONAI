"use strict";
const test = require("node:test");
const assert = require("node:assert/strict");
const runtime = require("../dashboard/runtime.js");

test("bounded mapper never exceeds its concurrency limit and preserves order", async () => {
  let active = 0, maximum = 0;
  const values = await runtime.mapWithConcurrency([0,1,2,3,4,5,6], 3, async (value) => {
    active += 1; maximum = Math.max(maximum, active);
    await new Promise(resolve => setTimeout(resolve, 5));
    active -= 1;
    return value * 2;
  });
  assert.equal(maximum, 3);
  assert.deepEqual(values, [0,2,4,6,8,10,12]);
});

test("manifest validator accepts a valid bounded manifest", () => {
  const manifest = {checkpoint_id:"ckpt-valid_1", step:12, files:{
    "state.json":{size_bytes:10,sha256:"a".repeat(64)},
    "weights.bin":{size_bytes:20,sha256:"b".repeat(64)}
  }};
  assert.deepEqual(runtime.validateManifest(manifest, "ckpt-valid_1"), {totalBytes:30,fileCount:2});
});

test("manifest validator rejects traversal, malformed hashes and unsafe sizes", () => {
  const base = {checkpoint_id:"ckpt-safe",step:1,files:{"state.json":{size_bytes:1,sha256:"a".repeat(64)}}};
  for (const [name, entry] of [
    ["../secret",{size_bytes:1,sha256:"a".repeat(64)}],
    ["state.json",{size_bytes:-1,sha256:"a".repeat(64)}],
    ["state.json",{size_bytes:Number.MAX_SAFE_INTEGER+1,sha256:"a".repeat(64)}],
    ["state.json",{size_bytes:1,sha256:"not-a-hash"}]
  ]) {
    const bad = {...base,files:{[name]:entry}};
    assert.throws(() => runtime.validateManifest(bad,"ckpt-safe"));
  }
});

test("manifest validator enforces aggregate checkpoint size", () => {
  const manifest = {checkpoint_id:"ckpt-large",step:1,files:{
    "state.json":{size_bytes:runtime.MAX_TOTAL_BYTES,sha256:"a".repeat(64)}
  }};
  assert.throws(() => runtime.validateManifest(manifest,"ckpt-large"), /256 MiB/);
});

test("chart scheduler falls back synchronously when animation frames are unavailable", () => {
  let called = 0;
  assert.equal(runtime.scheduleFrame(() => { called += 1; }, {}), null);
  assert.equal(called, 1);
});

test("chart scheduler uses requestAnimationFrame when available", () => {
  let queued = null;
  runtime.scheduleFrame(() => {}, {requestAnimationFrame: callback => { queued = callback; return 7; }});
  assert.equal(typeof queued, "function");
});
