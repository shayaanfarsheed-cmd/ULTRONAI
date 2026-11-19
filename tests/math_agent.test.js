"use strict";
const test=require("node:test");
const assert=require("node:assert/strict");
const agent=require("../dashboard/math-agent.js");
test("every supported topic solves and independently verifies a generated question",()=>{
 for(const topic of agent.TOPIC_KEYS){const q=agent.generate(topic,7);const result=agent.solve(topic,q);assert.equal(agent.verify(topic,q,result.answer),true,topic);assert.ok(result.steps.length);assert.ok(result.knowledge.rule);}
});
test("solver does not accept unsupported formats or oversized input",()=>{
 assert.throws(()=>agent.solve("fractions","1/2 + 1/3"));
 assert.throws(()=>agent.solve("fractions","x".repeat(1001)));
 assert.throws(()=>agent.solve("unknown","Calculate: 1 + 1"));
});
test("independent verifier rejects a deliberately wrong answer",()=>{
 for(const topic of agent.TOPIC_KEYS){const q=agent.generate(topic,9);const result=agent.solve(topic,q);assert.equal(agent.verify(topic,q,result.answer+"wrong"),false,topic);}
});
test("exact arithmetic avoids floating point for fractions and decimals",()=>{
 assert.equal(agent.solve("fractions","Calculate: (1/3) + (1/6)").answer,"1/2");
 assert.equal(agent.solve("decimals","Calculate: 0.1 + 0.2").answer,"0.3");
 assert.equal(agent.solve("decimals","Calculate: 0.5 + 0.25").answer,"0.75");
});
test("generator returns bounded deterministic question formats",()=>{
 for(const topic of agent.TOPIC_KEYS)assert.equal(agent.generate(topic,3),agent.generate(topic,3));
});
