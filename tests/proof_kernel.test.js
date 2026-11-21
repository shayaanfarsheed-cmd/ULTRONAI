"use strict";
const test=require("node:test"),assert=require("node:assert/strict"),K=require("../dashboard/proof-kernel.js");
const {T,F}=K, mk=(system,assumptions,steps,conclusion)=>({version:1,system,assumptions,steps,conclusion});
test("typed expression and formula validation",()=>{assert.equal(K.validFormula(F.eq(T.numeral(1),T.numeral(1))),true);assert.equal(K.validFormula(F.eq(T.numeral(1),T.rational(1,1))),false);assert.equal(K.validFormula(F.eq(T.add(T.numeral(1),T.numeral(2)),T.numeral(3))),true);assert.equal(K.validFormula({kind:"evil"}),false);});
test("formal contexts are separate and conservative",()=>{assert.deepEqual(K.SYSTEMS.PEANO_N.enabledAxioms,["PEANO-02","PEANO-03"]);assert.deepEqual(K.SYSTEMS.REAL_FIELD.enabledAxioms,["FIELD-01","FIELD-02","FIELD-03","FIELD-05","FIELD-06","FIELD-09"]);for(const s of ["ORDERED_FIELD","COMPLETE_REAL","EUCLID_GEOMETRY","KOLMOGOROV","ZFC"])assert.deepEqual(K.SYSTEMS[s].enabledAxioms,[]);});
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

test("proof contexts reject terms from incompatible mathematical domains",()=>{
 const fieldEquality=F.eq(T.rational(1,2),T.rational(1,2));
 const peano=mk("PEANO_N",[],[{id:"x",rule:"eq_refl",term:T.rational(1,2),formula:fieldEquality}],"x");
 assert.equal(K.verify(peano).valid,false);
 const pointEquality=F.eq(T.point("A"),T.point("A"));
 const field=mk("REAL_FIELD",[],[{id:"x",rule:"eq_refl",term:T.point("A"),formula:pointEquality}],"x");
 assert.equal(K.verify(field).valid,false);
});

test("proof replay reports undischarged assumptions and closes discharged ones",()=>{
 const a=F.predicate("A"),p=mk("PEANO_N",[{id:"ha",formula:a}],[{id:"a",rule:"assumption",assumption:"ha",formula:a},{id:"imp",rule:"imp_intro",premises:["a"],discharge:"ha",formula:F.implies(a,a)}],"imp");
 const result=K.verify(p);assert.equal(result.valid,true);assert.deepEqual(result.openAssumptions,[]);
 const open=mk("PEANO_N",[{id:"ha",formula:a}],[{id:"a",rule:"assumption",assumption:"ha",formula:a}],"a");
 assert.deepEqual(K.verify(open).openAssumptions,["ha"]);
});
test("assumption and axiom rules reject extraneous premises",()=>{
 const a=F.predicate("A"),p=mk("PEANO_N",[{id:"ha",formula:a}],[{id:"a",rule:"assumption",assumption:"ha",premises:["ha"],formula:a}],"a");
 assert.equal(K.verify(p).valid,false);
});
test("bound variables cannot lie about their declared sort",()=>{
 const bad=F.forall("x","Nat",F.eq(T.variable("x","Field"),T.variable("x","Field")));
 assert.equal(K.validFormula(bad),false);
});

test("trusted system and axiom registries cannot be mutated at runtime",()=>{
 assert.throws(()=>K.SYSTEMS.PEANO_N.enabledAxioms.push("ZFC-10"),TypeError);
 assert.throws(()=>{K.AXIOMS["PEANO-03"].formula.kind="forged";},TypeError);
});

test("implication introduction must discharge an assumption used by its derivation",()=>{
 const a=F.predicate("A"),b=F.predicate("B");
 const invalid=mk("PEANO_N",[{id:"ha",formula:a},{id:"hb",formula:b}],[
  {id:"b",rule:"assumption",assumption:"hb",formula:b},
  {id:"bad",rule:"imp_intro",premises:["b"],discharge:"ha",formula:F.implies(a,b)}
 ],"bad");
 assert.equal(K.verify(invalid).code,"RULE_MISMATCH");
 const valid=mk("PEANO_N",[{id:"ha",formula:a}],[
  {id:"a",rule:"assumption",assumption:"ha",formula:a},
  {id:"good",rule:"imp_intro",premises:["a"],discharge:"ha",formula:F.implies(a,a)}
 ],"good");
 assert.equal(K.verify(valid).valid,true);
});

test("typed AST nodes reject unexpected properties",()=>{
 const term=T.numeral(7);term.injected="unexpected";
 assert.equal(K.termSort(term),null);
 const formula=F.eq(T.numeral(1),T.numeral(1));formula.injected=true;
 assert.equal(K.validFormula(formula),false);
 const p=mk("PEANO_N",[],[{id:"r",rule:"eq_refl",term:T.numeral(1),formula:F.eq(T.numeral(1),T.numeral(1)),debug:"extra"}],"r");
 assert.equal(K.verify(p).code,"INVALID_STEP");
});
test("sparse predicate arguments and proof premises are rejected safely",()=>{
 const sparseArgs=new Array(1);
 assert.equal(K.validFormula(F.predicate("P",sparseArgs)),false);
 const sparsePremises=new Array(2);
 const p=mk("PEANO_N",[],[{id:"bad",rule:"and_intro",premises:sparsePremises,formula:F.and(F.predicate("A"),F.predicate("B"))}],"bad");
 assert.equal(K.verify(p).code,"INVALID_STEP");
});
test("proof and trace envelopes reject unknown fields and sparse lists",()=>{
 const base=mk("PEANO_N",[],[{id:"r",rule:"eq_refl",term:T.numeral(1),formula:F.eq(T.numeral(1),T.numeral(1))}],"r");
 assert.equal(K.verify({...base,untrusted:true}).code,"MALFORMED_PROOF");
 assert.equal(K.verifyWorkingTrace({kind:"ultron-proof-trace",proof:base,untrusted:true}).code,"UNTRUSTED_TRACE");
 const sparseSteps=mk("PEANO_N",[],new Array(1),"r");
 assert.equal(K.verify(sparseSteps).code,"MALFORMED_PROOF");
});
test("assumptions reject additional untyped fields",()=>{
 const p=mk("PEANO_N",[{id:"ha",formula:F.predicate("A"),metadata:"not part of the AST"}],
 [{id:"a",rule:"assumption",assumption:"ha",formula:F.predicate("A")}],"a");
 assert.equal(K.verify(p).code,"INVALID_ASSUMPTION");
});

test("a present but null claimed conclusion cannot bypass trace comparison",()=>{
 const proof=mk("PEANO_N",[],[{id:"r",rule:"eq_refl",term:T.numeral(1),formula:F.eq(T.numeral(1),T.numeral(1))}],"r");
 assert.equal(K.verifyWorkingTrace({kind:"ultron-proof-trace",proof,claimedConclusion:null}).code,"FORGED_TRACE");
});
test("rule-specific step schemas reject malformed premise types",()=>{
 const proof=mk("PEANO_N",[],[{id:"x",rule:"and_left",premises:"not-an-array",formula:F.predicate("A")}],"x");
 assert.equal(K.verify(proof).code,"INVALID_STEP");
});

test("Peano zero-not-successor axiom is formalized and typed",()=>{
 const formula=K.AXIOMS["PEANO-02"].formula;
 assert.equal(K.validFormula(formula,{},new Set(K.SYSTEMS.PEANO_N.sorts)),true);
 const proof=mk("PEANO_N",[],[{id:"ax",rule:"axiom",axiomId:"PEANO-02",formula}],"ax");
 const result=K.verify(proof);
 assert.equal(result.valid,true);
 assert.deepEqual(result.usedAxioms,["PEANO-02"]);
});
test("selected field axioms replay with exact Axiom Bank identifiers",()=>{
 for(const id of ["FIELD-02","FIELD-03","FIELD-05","FIELD-06","FIELD-09"]){
  const formula=K.AXIOMS[id].formula;
  assert.equal(K.validFormula(formula,{},new Set(K.SYSTEMS.REAL_FIELD.sorts)),true,id);
  const proof=mk("REAL_FIELD",[],[{id:"ax",rule:"axiom",axiomId:id,formula}],"ax");
  const result=K.verify(proof);
  assert.equal(result.valid,true,id);
  assert.deepEqual(result.usedAxioms,[id],id);
 }
});
test("negation is a typed formula constructor, not an unvalidated payload",()=>{
 assert.equal(K.validFormula(F.not(F.eq(T.numeral(0),T.numeral(1)))),true);
 assert.equal(K.validFormula(F.not({kind:"untrusted"})),false);
 assert.equal(K.validFormula({...F.not(F.predicate("P")),extra:true}),false);
});
test("new Peano and field axioms remain isolated by their contexts",()=>{
 const peano=K.AXIOMS["PEANO-02"].formula;
 const field=K.AXIOMS["FIELD-09"].formula;
 const wrongPeano=mk("REAL_FIELD",[],[{id:"ax",rule:"axiom",axiomId:"PEANO-02",formula:peano}],"ax");
 const wrongField=mk("PEANO_N",[],[{id:"ax",rule:"axiom",axiomId:"FIELD-09",formula:field}],"ax");
 assert.equal(K.verify(wrongPeano).code,"AXIOM_NOT_AVAILABLE");
 assert.equal(K.verify(wrongField).code,"AXIOM_NOT_AVAILABLE");
});
test("formalized field axiom cannot be replaced by a forged statement",()=>{
 const original=K.AXIOMS["FIELD-09"].formula;
 const changed=F.forall("a","Field",F.eq(T.variable("a","Field"),T.variable("a","Field")));
 const proof=mk("REAL_FIELD",[],[{id:"ax",rule:"axiom",axiomId:"FIELD-09",formula:changed}],"ax");
 assert.equal(K.verify(proof).code,"RULE_MISMATCH");
 assert.equal(K.validFormula(original,{},new Set(K.SYSTEMS.REAL_FIELD.sorts)),true);
});
