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
test("frozen held-out foundation set is independently solved and scored",()=>{
 const dataset=require("../evaluation/heldout_foundation_v1.json");
 const report=agent.evaluateHeldout(dataset);
 assert.equal(report.datasetId,"ultron-heldout-foundation-v1");
 assert.equal(report.total,dataset.examples.length);
 assert.equal(report.passed,dataset.examples.length);
 assert.equal(report.failed,0);
 assert.equal(report.accuracy,1);
 assert.equal(new Set(report.cases.map(item=>item.sampleId)).size,dataset.examples.length);
});
test("held-out evaluation rejects altered, duplicate, or non-test datasets",()=>{
 const dataset=require("../evaluation/heldout_foundation_v1.json");
 const altered=JSON.parse(JSON.stringify(dataset));altered.examples[0].answer="999";
 assert.equal(agent.evaluateHeldout(altered).failed,1);
 const duplicate=JSON.parse(JSON.stringify(dataset));duplicate.examples[1].sample_id=duplicate.examples[0].sample_id;
 assert.throws(()=>agent.evaluateHeldout(duplicate));
 const leaked=JSON.parse(JSON.stringify(dataset));leaked.examples[0].split="train";
 assert.throws(()=>agent.evaluateHeldout(leaked));
 const unfrozen=JSON.parse(JSON.stringify(dataset));unfrozen.frozen=false;
 assert.throws(()=>agent.evaluateHeldout(unfrozen));
});
