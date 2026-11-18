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
  const files = {};
  for (const name of ["state.json", "part-1.bin", "part-2.bin", "part-3.bin", "part-4.bin"]) {
    files[name] = {size_bytes:runtime.MAX_FILE_BYTES,sha256:"a".repeat(64)};
  }
  const manifest = {checkpoint_id:"ckpt-large",step:1,files};
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

test("single-flight shares one in-flight refresh and permits a fresh run after reset", async () => {
  const singleFlight = runtime.createSingleFlight();
  let calls = 0;
  let release;
  const gate = new Promise(resolve => { release = resolve; });
  const operation = async () => { calls += 1; await gate; return calls; };
  const first = singleFlight(operation);
  const second = singleFlight(operation);
  await Promise.resolve();
  assert.equal(calls, 1);
  release();
  assert.equal(await first, 1);
  assert.equal(await second, 1);
  assert.equal(await singleFlight(async () => { calls += 1; return calls; }), 2);
  let releaseOld;
  const oldGate = new Promise(resolve => { releaseOld = resolve; });
  const oldRun = singleFlight(async () => { await oldGate; return "old"; });
  singleFlight.reset();
  assert.equal(await singleFlight(async () => "new"), "new");
  releaseOld();
  assert.equal(await oldRun, "old");
});

test("bounded response reader accepts a stream exactly at the configured limit", async () => {
  const response = new Response(new Uint8Array([1,2,3,4]), {headers:{"content-length":"4"}});
  const bytes = await runtime.readResponseBytes(response, 4);
  assert.deepEqual(Array.from(new Uint8Array(bytes)), [1,2,3,4]);
});

test("bounded response reader cancels a stream that crosses the limit", async () => {
  let cancelled = false;
  const stream = new ReadableStream({
    start(controller) { controller.enqueue(new Uint8Array([1,2,3])); },
    cancel() { cancelled = true; }
  });
  const response = {headers:new Headers(),body:stream};
  await assert.rejects(runtime.readResponseBytes(response, 2), /allowed download size/);
  assert.equal(cancelled, true);
});

test("bounded response reader rejects an oversized declared length before reading", async () => {
  let read = false;
  const response = {
    headers:new Headers({"content-length":"9"}),
    body:{getReader(){read = true; throw new Error("must not read");}}
  };
  await assert.rejects(runtime.readResponseBytes(response, 8), /allowed download size/);
  assert.equal(read, false);
});

test("bounded response reader fails closed without streaming or a trustworthy length", async () => {
  const response = {headers:new Headers(),arrayBuffer:async () => new Uint8Array([1]).buffer};
  await assert.rejects(runtime.readResponseBytes(response, 8), /cannot safely enforce/);
});

test("manifest validator rejects numeric strings for the checkpoint step", () => {
  const manifest = {checkpoint_id:"ckpt-step",step:"12",files:{
    "state.json":{size_bytes:1,sha256:"a".repeat(64)}
  }};
  assert.throws(() => runtime.validateManifest(manifest, "ckpt-step"), /structure is invalid/);
});

test("bounded response reader rejects a dishonest declared length", async () => {
  const response = new Response(new Uint8Array([1,2,3]), {headers:{"content-length":"2"}});
  await assert.rejects(runtime.readResponseBytes(response, 8), /does not match its header/);
});
