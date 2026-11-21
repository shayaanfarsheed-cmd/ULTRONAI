"use strict";
const test=require("node:test"),assert=require("node:assert/strict"),K=require("../dashboard/proof-kernel.js");
const {T,F}=K, mk=(system,assumptions,steps,conclusion)=>({version:1,system,assumptions,steps,conclusion});
test("typed expression and formula validation",()=>{assert.equal(K.validFormula(F.eq(T.numeral(1),T.numeral(1))),true);assert.equal(K.validFormula(F.eq(T.numeral(1),T.rational(1,1))),false);assert.equal(K.validFormula(F.eq(T.add(T.numeral(1),T.numeral(2)),T.numeral(3))),true);assert.equal(K.validFormula({kind:"evil"}),false);});
test("formal contexts are separate and conservative",()=>{assert.deepEqual(K.SYSTEMS.PEANO_N.enabledAxioms,["PEANO-03"]);assert.deepEqual(K.SYSTEMS.REAL_FIELD.enabledAxioms,["FIELD-01"]);for(const s of ["ORDERED_FIELD","COMPLETE_REAL","EUCLID_GEOMETRY","KOLMOGOROV","ZFC"])assert.deepEqual(K.SYSTEMS[s].enabledAxioms,[]);});
test("reflexivity replays and forged conclusion fails",()=>{const x=T.variable("x","Nat"),p=mk("PEANO_N",[],[{id:"r",rule:"eq_refl",term:x,formula:F.eq(x,x)}],"r");assert.equal(K.verify(p).valid,true);p.steps[0].formula=F.eq(x,T.numeral(2));assert.equal(K.verify(p).code,"RULE_MISMATCH");});
test("assumptions, conjunction and implication introduction",()=>{const a=F.predicate("A"),b=F.predicate("B"),p=mk("PEANO_N",[{id:"ha",formula:a},{id:"hb",formula:b}],[{id:"a",rule:"assumption",assumption:"ha",formula:a},{id:"b",rule:"assumption",assumption:"hb",formula:b},{id:"ab",rule:"and_intro",premises:["a","b"],formula:F.and(a,b)},{id:"imp",rule:"imp_intro",premises:["b"],discharge:"hb",formula:F.implies(b,b)}],"imp");assert.equal(K.verify(p).valid,true);});
test("unknown, forward and duplicate references rejected",()=>{const a=F.predicate("A"),p=mk("PEANO_N",[],[{id:"x",rule:"and_left",premises:["future"],formula:a}],"x");assert.equal(K.verify(p).code,"UNKNOWN_PREMISE");const d=mk("PEANO_N",[{id:"x",formula:a}],[{id:"x",rule:"assumption",assumption:"x",formula:a}],"x");assert.equal(K.verify(d).code,"INVALID_STEP");});
test("axiom dependencies bind to exact formal-system IDs",()=>{const ax=K.AXIOMS["PEANO-03"].formula,g=mk("PEANO_N",[],[{id:"a",rule:"axiom",axiomId:"PEANO-03",formula:ax}],"a");assert.equal(K.verify(g).valid,true);const wrong=mk("REAL_FIELD",[],[{id:"a",rule:"axiom",axiomId:"PEANO-03",formula:ax}],"a");assert.equal(K.verify(wrong).code,"AXIOM_NOT_AVAILABLE");const natural=mk("ZFC",[],[{id:"a",rule:"axiom",axiomId:"ZFC-10",formula:F.predicate("Choice")}],"a");assert.equal(K.verify(natural).code,"AXIOM_NOT_AVAILABLE");});
test("working trace rejects forged or unstructured evidence",()=>{const x=T.numeral(3),p=mk("PEANO_N",[],[{id:"r",rule:"eq_refl",term:x,formula:F.eq(x,x)}],"r");assert.equal(K.verifyWorkingTrace({kind:"ultron-proof-trace",proof:p,claimedConclusion:F.eq(x,x)}).diagnosisEligible,true);assert.equal(K.verifyWorkingTrace({kind:"ultron-proof-trace",proof:p,claimedConclusion:F.eq(x,T.numeral(4))}).code,"FORGED_TRACE");assert.equal(K.verifyWorkingTrace({steps:[]}).code,"UNTRUSTED_TRACE");});
test("quantifier elimination rejects incompatible replacement sort",()=>{const q=K.AXIOMS["PEANO-03"].formula,p=mk("PEANO_N",[],[{id:"q",rule:"axiom",axiomId:"PEANO-03",formula:q},{id:"bad",rule:"forall_elim",premises:["q"],term:T.rational(1,2),formula:F.predicate("bad")}],"bad");assert.equal(K.verify(p).valid,false);});

test("quantifier substitution rejects variable capture",()=>{
 const inner=F.forall("y","Nat",F.eq(T.variable("x","Nat"),T.variable("y","Nat")));
 const outer=F.forall("x","Nat",inner);
 const p=mk("PEANO_N",[{id:"q",formula:outer}],[{id:"q0",rule:"assumption",assumption:"q",formula:outer},{id:"capture",rule:"forall_elim",premises:["q0"],term:T.variable("y","Nat"),formula:F.forall("y","Nat",F.eq(T.variable("y","Nat"),T.variable("y","Nat")))}],"capture");
 assert.equal(K.verify(p).valid,false);
});
test("field axiom is usable only in field context",()=>{
 const f=K.AXIOMS["FIELD-01"].formula;
 const good=mk("REAL_FIELD",[],[{id:"field",rule:"axiom",axiomId:"FIELD-01",formula:f}],"field");
 assert.equal(K.verify(good).valid,true);
 const bad=mk("PEANO_N",[],[{id:"field",rule:"axiom",axiomId:"FIELD-01",formula:f}],"field");
 assert.equal(K.verify(bad).code,"AXIOM_NOT_AVAILABLE");
});
