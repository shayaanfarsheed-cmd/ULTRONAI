"use strict";
const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");

test("late owner-only workflow status cannot repaint dashboard after sign-out", async () => {
  const source = fs.readFileSync(path.join(__dirname, "../dashboard/training-control.js"), "utf8");
  const nodes = new Map();
  const makeNode = (id) => ({
    id, value: id === "trainingServerSelect" ? "github_actions_cpu" : "",
    hidden: false, disabled: false, textContent: "", className: "", href: "",
    handlers: Object.create(null), parentElement: null,
    addEventListener(type, callback) { this.handlers[type] = callback; },
    insertBefore(node) { node.parentElement = this; },
  });
  const getNode = (id) => {
    if (!nodes.has(id)) nodes.set(id, makeNode(id));
    return nodes.get(id);
  };
  const actions = makeNode("trainingControlActions");
  getNode("trainingRefreshButton").parentElement = actions;

  const windowHandlers = Object.create(null);
  const session = {
    access_token: "owner-access-token",
    user: { id: "owner-user-id" },
  };
  let pendingStatusResolve;
  let statusRequestCount = 0;
  const context = {
    console,
    Promise,
    JSON,
    String,
    Boolean,
    Number,
    Math,
    Date,
    setTimeout,
    clearTimeout,
    sessionStorage: {
      getItem(key) { return key === "ultron_training_session" ? JSON.stringify(session) : null; },
      removeItem(key) { if (key === "ultron_training_session") delete session.access_token; },
    },
    document: {
      getElementById: getNode,
      createElement: (tag) => makeNode(tag),
      addEventListener(type, callback) {
        if (type === "DOMContentLoaded") this.ready = callback;
      },
    },
    window: {
      ULTRON_CONFIG: {
        ownerUserId: "owner-user-id",
        trainingControlFunctionUrl: "https://example.supabase.co/functions/v1/training-control",
        supabasePublishableKey: "public-key",
      },
      addEventListener(type, callback) { windowHandlers[type] = callback; },
      setInterval() { return 1; },
      clearInterval() {},
      confirm() { return false; },
    },
    fetch: async (url) => {
      if (url === "../servers.json") {
        return { ok: true, json: async () => ({ servers: [{ id: "github_actions_cpu", name: "GitHub Actions CPU" }] }) };
      }
      statusRequestCount += 1;
      return await new Promise((resolve) => {
        pendingStatusResolve = () => resolve({
          ok: true,
          json: async () => ({
            run: {
              status: "in_progress",
              message: "PRIVATE RUN MUST NOT REAPPEAR AFTER SIGN-OUT",
              html_url: "https://github.com/example/private-run",
            },
          }),
        });
      });
    },
  };
  vm.runInNewContext(source, context, { filename: "dashboard/training-control.js" });
  context.document.ready();
  await new Promise((resolve) => setImmediate(resolve));
  assert.equal(statusRequestCount, 1, "owner mode should request private status");

  // Simulate the dashboard's owner-mode transition to Guest Mode.
  context.sessionStorage.removeItem("ultron_training_session");
  windowHandlers["ultron:owner-mode-changed"]();
  assert.equal(getNode("trainingControlState").textContent, "NO RECENT WORKFLOW");

  // Complete the older private request after sign-out.
  pendingStatusResolve();
  await new Promise((resolve) => setImmediate(resolve));
  assert.equal(getNode("trainingControlState").textContent, "NO RECENT WORKFLOW");
  assert.equal(getNode("trainingControlDetails").textContent, "No GitHub Actions run was found.");
  assert.equal(getNode("trainingRunLink").hidden, true);
  assert.equal(
    getNode("trainingControlDetails").textContent.includes("PRIVATE RUN MUST NOT REAPPEAR AFTER SIGN-OUT"),
    false,
  );
});
