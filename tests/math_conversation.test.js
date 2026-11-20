"use strict";
const test = require("node:test");
const assert = require("node:assert/strict");
const agent = require("../dashboard/math-agent.js");
const conversation = require("../dashboard/math-conversation.js");

test("conversation routes simple arithmetic and independently verifies it", () => {
  const chat = conversation.createConversation(agent);
  const result = chat.reply("What is 12 + 5?");
  assert.equal(result.kind, "solution");
  assert.equal(result.topic, "whole_number_arithmetic");
  assert.equal(result.answer, "17");
  assert.equal(result.verified, true);
});

test("conversation recognizes explicit topic and supported question format", () => {
  const chat = conversation.createConversation(agent);
  const result = chat.reply("fractions: Calculate: (1/3) + (1/6)");
  assert.equal(result.kind, "solution");
  assert.equal(result.topic, "fractions");
  assert.equal(result.answer, "1/2");
  assert.equal(result.verified, true);
});

test("conversation asks a clarification instead of guessing an unknown topic", () => {
  const chat = conversation.createConversation(agent);
  const result = chat.reply("Can you help me with this homework?");
  assert.equal(result.kind, "clarification");
  assert.match(result.message, /Which maths topic/);
});

test("conversation retains the last topic for a follow-up and provides a format hint", () => {
  const chat = conversation.createConversation(agent);
  const first = chat.reply("decimals: Calculate: 0.1 + 0.2");
  assert.equal(first.answer, "0.3");
  const followup = chat.reply("add these decimals");
  assert.equal(followup.kind, "clarification");
  assert.equal(followup.topic, "decimals");
  assert.ok(followup.example);
});

test("unsupported formats are clarified and never reported as verified", () => {
  const chat = conversation.createConversation(agent);
  const result = chat.reply("fractions: what is one half plus one third?");
  assert.equal(result.kind, "clarification");
  assert.equal(result.verified, false);
  assert.ok(result.example);
});

test("conversation history is bounded and can be reset", () => {
  const chat = conversation.createConversation(agent, { maxTurns: 2 });
  for (let i = 0; i < 5; i++) chat.reply("What is 2 + 2?");
  assert.ok(chat.getHistory().length <= 4);
  chat.reset();
  assert.equal(chat.getHistory().length, 0);
  assert.equal(chat.getLastTopic(), null);
});

test("input validation rejects empty, non-text and oversized messages", () => {
  const chat = conversation.createConversation(agent);
  assert.throws(() => chat.reply(""));
  assert.throws(() => chat.reply(42));
  assert.throws(() => chat.reply("x".repeat(1001)));
});

test("conversation reset command clears context without persisting it", () => {
  const chat = conversation.createConversation(agent);
  chat.reply("What is 2 + 2?");
  const result = chat.reply("/reset");
  assert.equal(result.kind, "notice");
  assert.equal(chat.getHistory().length, 1);
  assert.equal(chat.getLastTopic(), null);
});

test("history copies cannot mutate internal conversation state", () => {
  const chat = conversation.createConversation(agent);
  chat.reply("What is 2 + 2?");
  const history = chat.getHistory();
  history[0].text = "tampered";
  assert.notEqual(chat.getHistory()[0].text, "tampered");
});
