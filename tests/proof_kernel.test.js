"use strict";
const test=require("node:test"),assert=require("node:assert/strict"),K=require("../dashboard/proof-kernel.js");
const {T,F}=K, mk=(system,assumptions,steps,conclusion)=>({version:1,system,assumptions,steps,conclusion});
test("typed expression and formula validation",()=>{assert.equal(K.validFormula(F.eq(T.numeral(1),T.numeral(1))),true);assert.equal(K.validFormula(F.eq(T.numeral(1),T.rational(1,1))),false);assert.equal(K.validFormula(F.eq(T.add(T.numeral(1),T.numeral(2)),T.numeral(3))),true);assert.equal(K.validFormula({kind:"evil"}),false);});
test("formal contexts are separate and conservative",()=>{assert.deepEqual(K.SYSTEMS.PEANO_N.enabledAxioms,["PEANO-02","PEANO-03"]);assert.deepEqual(K.SYSTEMS.PEANO_N.enabledAxiomSchemas,["PEANO-04"]);assert.deepEqual(K.SYSTEMS.REAL_FIELD.enabledAxioms,["FIELD-01","FIELD-02","FIELD-03","FIELD-04","FIELD-05","FIELD-06","FIELD-07","FIELD-08","FIELD-09"]);assert.deepEqual(K.SYSTEMS.REAL_FIELD.enabledAxiomSchemas,[]);for(const s of ["ORDERED_FIELD","COMPLETE_REAL"]){assert.deepEqual(K.SYSTEMS[s].enabledAxioms,[]);assert.deepEqual(K.SYSTEMS[s].enabledAxiomSchemas,[]);}assert.deepEqual(K.SYSTEMS.EUCLID_GEOMETRY.enabledAxioms,["EUCLID-01"]);assert.deepEqual(K.SYSTEMS.KOLMOGOROV.enabledAxioms,["PROB-01","PROB-02"]);assert.deepEqual(K.SYSTEMS.ZFC.enabledAxioms,["ZFC-01","ZFC-02"]);for(const s of ["EUCLID_GEOMETRY","KOLMOGOROV","ZFC"])assert.deepEqual(K.SYSTEMS[s].enabledAxiomSchemas,[]);});
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

test("Peano induction schema replays a valid base case and successor step",()=>{
 const conclusionVariable="n",inductionVariable="k";
 const P=x=>F.predicate("EvenLike",[x]);
 const base=P(T.numeral(0));
 const step=F.forall(inductionVariable,"Nat",F.implies(P(T.variable(inductionVariable,"Nat")),P(T.succ(T.variable(inductionVariable,"Nat")))));
 const goal=F.forall(conclusionVariable,"Nat",P(T.variable(conclusionVariable,"Nat")));
 const proof=mk("PEANO_N",[{id:"base",formula:base},{id:"step",formula:step}],[
  {id:"base-proof",rule:"assumption",assumption:"base",formula:base},
  {id:"step-proof",rule:"assumption",assumption:"step",formula:step},
  {id:"induction",rule:"induction",axiomId:"PEANO-04",variable:inductionVariable,premises:["base-proof","step-proof"],formula:goal}
 ],"induction");
 const result=K.verify(proof);
 assert.equal(result.valid,true);
 assert.deepEqual(result.usedAxiomSchemas,["PEANO-04"]);
 assert.deepEqual(result.openAssumptions,["base","step"]);
});
test("Peano induction rejects a forged base case",()=>{
 const P=x=>F.predicate("P",[x]);
 const base=P(T.numeral(1));
 const step=F.forall("k","Nat",F.implies(P(T.variable("k","Nat")),P(T.succ(T.variable("k","Nat")))));
 const goal=F.forall("n","Nat",P(T.variable("n","Nat")));
 const proof=mk("PEANO_N",[{id:"b",formula:base},{id:"s",formula:step}],[
  {id:"b0",rule:"assumption",assumption:"b",formula:base},
  {id:"s0",rule:"assumption",assumption:"s",formula:step},
  {id:"i",rule:"induction",axiomId:"PEANO-04",variable:"k",premises:["b0","s0"],formula:goal}
 ],"i");
 assert.equal(K.verify(proof).code,"RULE_MISMATCH");
});
test("Peano induction schema is unavailable outside Peano arithmetic",()=>{
 const proof=mk("REAL_FIELD",[],[
  {id:"i",rule:"induction",axiomId:"PEANO-04",variable:"k",premises:["base","step"],formula:F.forall("n","Field",F.predicate("P",[T.variable("n","Field")]))}
 ],"i");
 assert.equal(K.verify(proof).code,"AXIOM_SCHEMA_NOT_AVAILABLE");
});
test("Peano induction rejects a capture-prone induction variable",()=>{
 const P=x=>F.predicate("P",[x]);
 const body=F.and(P(T.variable("n","Nat")),F.forall("k","Nat",F.predicate("Q",[T.variable("n","Nat")])));
 const goal=F.forall("n","Nat",body);
 const base=F.and(P(T.numeral(0)),F.forall("k","Nat",F.predicate("Q",[T.numeral(0)])));
 const dummy=F.predicate("dummy");
 const proof=mk("PEANO_N",[{id:"b",formula:base},{id:"s",formula:dummy}],[
  {id:"b0",rule:"assumption",assumption:"b",formula:base},
  {id:"s0",rule:"assumption",assumption:"s",formula:dummy},
  {id:"i",rule:"induction",axiomId:"PEANO-04",variable:"k",premises:["b0","s0"],formula:goal}
 ],"i");
 assert.equal(K.verify(proof).code,"INVALID_INDUCTION_VARIABLE");
});
test("induction schema ID cannot be forged or substituted",()=>{
 const proof=mk("PEANO_N",[],[
  {id:"i",rule:"induction",axiomId:"FIELD-01",variable:"k",premises:["b","s"],formula:F.forall("n","Nat",F.predicate("P",[T.variable("n","Nat")]))}
 ],"i");
 assert.equal(K.verify(proof).code,"INVALID_STEP");
});

test("Peano induction rejects an induction variable free in an open premise assumption",()=>{
 const k=T.variable("k","Nat");
 const P=x=>F.predicate("P",[x]);
 const base=P(T.numeral(0));
 const step=F.forall("j","Nat",F.implies(P(T.variable("j","Nat")),P(T.succ(T.variable("j","Nat")))));
 const taintedBase=F.and(base,F.predicate("Q",[k]));
 const goal=F.forall("n","Nat",P(T.variable("n","Nat")));
 const proof=mk("PEANO_N",[{id:"tainted",formula:taintedBase},{id:"step",formula:step}],[
  {id:"base",rule:"assumption",assumption:"tainted",formula:taintedBase},
  {id:"base-only",rule:"and_left",premises:["base"],formula:base},
  {id:"step-proof",rule:"assumption",assumption:"step",formula:step},
  {id:"induction",rule:"induction",axiomId:"PEANO-04",variable:"k",premises:["base-only","step-proof"],formula:goal}
 ],"induction");
 assert.equal(K.verify(proof).code,"INDUCTION_VARIABLE_IN_ASSUMPTION");
});

test("universal introduction verifies a fresh eigenvariable instance",()=>{
 const eigen=T.variable("k","Nat");
 const instance=F.eq(eigen,eigen);
 const goal=F.forall("n","Nat",F.eq(T.variable("n","Nat"),T.variable("n","Nat")));
 const proof=mk("PEANO_N",[],[
  {id:"reflexive",rule:"eq_refl",term:eigen,formula:instance},
  {id:"generalized",rule:"forall_intro",variable:"k",premises:["reflexive"],formula:goal}
 ],"generalized");
 assert.equal(K.verify(proof).valid,true);
 assert.deepEqual(K.verify(proof).openAssumptions,[]);
});
test("universal introduction rejects an eigenvariable free in an open assumption",()=>{
 const eigen=T.variable("k","Nat"),claim=F.predicate("P",[eigen]);
 const goal=F.forall("n","Nat",F.predicate("P",[T.variable("n","Nat")]));
 const proof=mk("PEANO_N",[{id:"assumption",formula:claim}],[ 
  {id:"premise",rule:"assumption",assumption:"assumption",formula:claim},
  {id:"generalized",rule:"forall_intro",variable:"k",premises:["premise"],formula:goal}
 ],"generalized");
 assert.equal(K.verify(proof).code,"EIGENVARIABLE_IN_ASSUMPTION");
});
test("universal introduction rejects a mismatched premise instance",()=>{
 const eigen=T.variable("j","Nat"),goal=F.forall("n","Nat",F.eq(T.variable("n","Nat"),T.variable("n","Nat")));
 const proof=mk("PEANO_N",[],[
  {id:"reflexive",rule:"eq_refl",term:eigen,formula:F.eq(eigen,eigen)},
  {id:"generalized",rule:"forall_intro",variable:"k",premises:["reflexive"],formula:goal}
 ],"generalized");
 assert.equal(K.verify(proof).code,"RULE_MISMATCH");
});
test("universal introduction rejects binder capture and shadowing",()=>{
 const body=F.and(F.predicate("P",[T.variable("n","Nat")]),F.forall("k","Nat",F.predicate("Q",[T.variable("n","Nat")])));
 const goal=F.forall("n","Nat",body);
 const proof=mk("PEANO_N",[],[
  {id:"premise",rule:"eq_refl",term:T.numeral(1),formula:F.eq(T.numeral(1),T.numeral(1))},
  {id:"generalized",rule:"forall_intro",variable:"k",premises:["premise"],formula:goal}
 ],"generalized");
 assert.equal(K.verify(proof).code,"INVALID_EIGENVARIABLE");
});
test("universal introduction works in a compatible field context",()=>{
 const eigen=T.variable("z","Field"),goal=F.forall("x","Field",F.eq(T.variable("x","Field"),T.variable("x","Field")));
 const proof=mk("REAL_FIELD",[],[
  {id:"reflexive",rule:"eq_refl",term:eigen,formula:F.eq(eigen,eigen)},
  {id:"generalized",rule:"forall_intro",variable:"z",premises:["reflexive"],formula:goal}
 ],"generalized");
 assert.equal(K.verify(proof).valid,true);
});

test("existential formulas are typed and their binders scope variables",()=>{
 const valid=F.exists("x","Field",F.eq(T.variable("x","Field"),T.rational(0,1)));
 assert.equal(K.validFormula(valid,{},new Set(K.SYSTEMS.REAL_FIELD.sorts)),true);
 const wrongSort=F.exists("x","Nat",F.eq(T.variable("x","Nat"),T.numeral(0)));
 assert.equal(K.validFormula(wrongSort,{},new Set(K.SYSTEMS.REAL_FIELD.sorts)),false);
 const lyingBoundSort=F.exists("x","Field",F.eq(T.variable("x","Nat"),T.numeral(0)));
 assert.equal(K.validFormula(lyingBoundSort,{},new Set(K.SYSTEMS.REAL_FIELD.sorts)),false);
 const unbound=F.exists("x","Field",F.eq(T.variable("y","Field"),T.rational(0,1)));
 assert.equal(K.validFormula(unbound,{},new Set(K.SYSTEMS.REAL_FIELD.sorts)),true);
});
test("existential substitution rejects variable capture",()=>{
 const universal=F.forall("x","Field",F.exists("y","Field",F.eq(T.variable("x","Field"),T.variable("y","Field"))));
 const proof=mk("REAL_FIELD",[{id:"q",formula:universal}],[
  {id:"given",rule:"assumption",assumption:"q",formula:universal},
  {id:"captured",rule:"forall_elim",premises:["given"],term:T.variable("y","Field"),formula:F.predicate("unreachable")}
 ],"captured");
 assert.equal(K.verify(proof).code,"RULE_MISMATCH");
});
test("remaining field inverse and identity axioms replay by exact ID",()=>{
 for(const id of ["FIELD-04","FIELD-07","FIELD-08"]){
  const formula=K.AXIOMS[id].formula;
  assert.equal(K.validFormula(formula,{},new Set(K.SYSTEMS.REAL_FIELD.sorts)),true,id);
  const proof=mk("REAL_FIELD",[],[{id:"ax",rule:"axiom",axiomId:id,formula}],"ax");
  const result=K.verify(proof);
  assert.equal(result.valid,true,id);
  assert.deepEqual(result.usedAxioms,[id],id);
 }
});
test("field inverse axioms remain isolated and reject forged statements",()=>{
 for(const id of ["FIELD-04","FIELD-07","FIELD-08"]){
  const formula=K.AXIOMS[id].formula;
  const wrong=mk("PEANO_N",[],[{id:"ax",rule:"axiom",axiomId:id,formula}],"ax");
  assert.equal(K.verify(wrong).code,"AXIOM_NOT_AVAILABLE",id);
  const forged=mk("REAL_FIELD",[],[{id:"ax",rule:"axiom",axiomId:id,formula:F.predicate("forged")}],"ax");
  assert.equal(K.verify(forged).code,"RULE_MISMATCH",id);
 }
});
test("unregistered existential inference names remain rejected",()=>{
 const proof=mk("REAL_FIELD",[],[
  {id:"fake",rule:"exists_magic",premises:[],formula:F.exists("x","Field",F.predicate("P",[T.variable("x","Field")]))}
 ],"fake");
 assert.equal(K.verify(proof).code,"UNKNOWN_RULE");
});

test("universal introduction treats existential binders as variable-name collisions",()=>{
 const body=F.exists("k","Nat",F.predicate("P",[T.variable("n","Nat")]));
 const goal=F.forall("n","Nat",body);
 const proof=mk("PEANO_N",[],[
  {id:"premise",rule:"eq_refl",term:T.numeral(1),formula:F.eq(T.numeral(1),T.numeral(1))},
  {id:"generalized",rule:"forall_intro",variable:"k",premises:["premise"],formula:goal}
 ],"generalized");
 assert.equal(K.verify(proof).code,"INVALID_EIGENVARIABLE");
});

test("existential introduction verifies a concrete witness",()=>{
 const witness=T.variable("a","Field"),instance=F.predicate("P",[witness]);
 const goal=F.exists("x","Field",F.predicate("P",[T.variable("x","Field")]));
 const proof=mk("REAL_FIELD",[{id:"pa",formula:instance}],[
  {id:"given",rule:"assumption",assumption:"pa",formula:instance},
  {id:"some",rule:"exists_intro",premises:["given"],term:witness,formula:goal}
 ],"some");
 const result=K.verify(proof);
 assert.equal(result.valid,true);
 assert.deepEqual(result.openAssumptions,["pa"]);
 assert.deepEqual(result.trace[1].term,witness);
});
test("existential introduction rejects a witness that would be captured by a nested binder",()=>{
 const witness=T.variable("a","Field");
 const goal=F.exists("x","Field",F.exists("a","Field",F.predicate("P",[T.variable("x","Field"),T.variable("a","Field")])));
 const instance=F.predicate("P",[witness,witness]);
 const proof=mk("REAL_FIELD",[{id:"pa",formula:instance}],[
  {id:"given",rule:"assumption",assumption:"pa",formula:instance},
  {id:"some",rule:"exists_intro",premises:["given"],term:witness,formula:goal}
 ],"some");
 assert.equal(K.verify(proof).code,"RULE_MISMATCH");
});
test("existential elimination discharges only the temporary witness assumption",()=>{
 const witness=T.variable("k","Field"),P=x=>F.predicate("P",[x]);
 const existential=F.exists("x","Field",P(T.variable("x","Field")));
 const witnessAssumption=P(witness);
 const conclusion=F.eq(T.rational(1,1),T.rational(1,1));
 const proof=mk("REAL_FIELD",[
  {id:"major",formula:existential},
  {id:"case",formula:witnessAssumption}
 ],[
  {id:"major-step",rule:"assumption",assumption:"major",formula:existential},
  {id:"case-step",rule:"assumption",assumption:"case",formula:witnessAssumption},
  {id:"truth",rule:"eq_refl",term:T.rational(1,1),formula:conclusion},
  {id:"combined",rule:"and_intro",premises:["case-step","truth"],formula:F.and(witnessAssumption,conclusion)},
  {id:"minor-proof",rule:"and_right",premises:["combined"],formula:conclusion},
  {id:"eliminated",rule:"exists_elim",premises:["major-step","minor-proof"],variable:"k",discharge:"case",formula:conclusion}
 ],"eliminated");
 const result=K.verify(proof);
 assert.equal(result.valid,true);
 assert.deepEqual(result.openAssumptions,["major"]);
 assert.equal(result.trace.at(-1).discharge,"case");
});
test("existential elimination rejects a witness leaked into the conclusion",()=>{
 const witness=T.variable("k","Field"),P=x=>F.predicate("P",[x]);
 const existential=F.exists("x","Field",P(T.variable("x","Field")));
 const minor=P(witness);
 const proof=mk("REAL_FIELD",[{id:"major",formula:existential},{id:"case",formula:minor}],[
  {id:"major-step",rule:"assumption",assumption:"major",formula:existential},
  {id:"case-step",rule:"assumption",assumption:"case",formula:minor},
  {id:"eliminated",rule:"exists_elim",premises:["major-step","case-step"],variable:"k",discharge:"case",formula:minor}
 ],"eliminated");
 assert.equal(K.verify(proof).code,"INVALID_EXISTS_EIGENVARIABLE");
});
test("existential elimination rejects witness leakage through another open assumption",()=>{
 const witness=T.variable("k","Field"),P=x=>F.predicate("P",[x]),Q=x=>F.predicate("Q",[x]);
 const existential=F.exists("x","Field",P(T.variable("x","Field")));
 const witnessAssumption=P(witness),other=Q(witness);
 const conclusion=F.eq(T.rational(1,1),T.rational(1,1));
 const proof=mk("REAL_FIELD",[
  {id:"major",formula:existential},{id:"case",formula:witnessAssumption},{id:"other",formula:other}
 ],[
  {id:"major-step",rule:"assumption",assumption:"major",formula:existential},
  {id:"case-step",rule:"assumption",assumption:"case",formula:witnessAssumption},
  {id:"other-step",rule:"assumption",assumption:"other",formula:other},
  {id:"truth",rule:"eq_refl",term:T.rational(1,1),formula:conclusion},
  {id:"case-and-truth",rule:"and_intro",premises:["case-step","truth"],formula:F.and(witnessAssumption,conclusion)},
  {id:"combined",rule:"and_intro",premises:["other-step","case-and-truth"],formula:F.and(other,F.and(witnessAssumption,conclusion))},
  {id:"peel-other",rule:"and_right",premises:["combined"],formula:F.and(witnessAssumption,conclusion)},
  {id:"minor-proof",rule:"and_right",premises:["peel-other"],formula:conclusion},
  {id:"eliminated",rule:"exists_elim",premises:["major-step","minor-proof"],variable:"k",discharge:"case",formula:conclusion}
 ],"eliminated");
 assert.equal(K.verify(proof).code,"EXISTS_EIGENVARIABLE_IN_ASSUMPTION");
});
test("existential elimination rejects discharging the major-premise dependency",()=>{
 const witness=T.variable("k","Field"),P=x=>F.predicate("P",[x]);
 const instance=P(witness),existential=F.exists("x","Field",P(T.variable("x","Field")));
 const conclusion=F.eq(T.rational(1,1),T.rational(1,1));
 const proof=mk("REAL_FIELD",[{id:"case",formula:instance}],[
  {id:"case-step",rule:"assumption",assumption:"case",formula:instance},
  {id:"major-step",rule:"exists_intro",premises:["case-step"],term:witness,formula:existential},
  {id:"truth",rule:"eq_refl",term:T.rational(1,1),formula:conclusion},
  {id:"combined",rule:"and_intro",premises:["case-step","truth"],formula:F.and(instance,conclusion)},
  {id:"minor-proof",rule:"and_right",premises:["combined"],formula:conclusion},
  {id:"eliminated",rule:"exists_elim",premises:["major-step","minor-proof"],variable:"k",discharge:"case",formula:conclusion}
 ],"eliminated");
 assert.equal(K.verify(proof).code,"INVALID_EXISTS_ELIMINATION_SCOPE");
});
test("existential elimination rejects a mismatched witness assumption",()=>{
 const witness=T.variable("k","Field"),P=x=>F.predicate("P",[x]),Q=x=>F.predicate("Q",[x]);
 const existential=F.exists("x","Field",P(T.variable("x","Field")));
 const conclusion=F.eq(T.rational(1,1),T.rational(1,1));
 const proof=mk("REAL_FIELD",[
  {id:"major",formula:existential},
  {id:"case",formula:Q(witness)}
 ],[
  {id:"major-step",rule:"assumption",assumption:"major",formula:existential},
  {id:"case-step",rule:"assumption",assumption:"case",formula:Q(witness)},
  {id:"truth",rule:"eq_refl",term:T.rational(1,1),formula:conclusion},
  {id:"combined",rule:"and_intro",premises:["case-step","truth"],formula:F.and(Q(witness),conclusion)},
  {id:"minor-proof",rule:"and_right",premises:["combined"],formula:conclusion},
  {id:"eliminated",rule:"exists_elim",premises:["major-step","minor-proof"],variable:"k",discharge:"case",formula:conclusion}
 ],"eliminated");
 assert.equal(K.verify(proof).code,"RULE_MISMATCH");
});

test("existential elimination rejects an eigenvariable already free in the major premise",()=>{
 const witness=T.variable("k","Field"),P=(x,y)=>F.predicate("P",[x,y]);
 const major=F.exists("x","Field",P(T.variable("x","Field"),witness));
 const caseFormula=P(witness,witness),conclusion=F.eq(T.rational(1,1),T.rational(1,1));
 const proof=mk("REAL_FIELD",[{id:"major",formula:major},{id:"case",formula:caseFormula}],[
  {id:"major-step",rule:"assumption",assumption:"major",formula:major},
  {id:"case-step",rule:"assumption",assumption:"case",formula:caseFormula},
  {id:"truth",rule:"eq_refl",term:T.rational(1,1),formula:conclusion},
  {id:"combined",rule:"and_intro",premises:["case-step","truth"],formula:F.and(caseFormula,conclusion)},
  {id:"minor-proof",rule:"and_right",premises:["combined"],formula:conclusion},
  {id:"eliminated",rule:"exists_elim",premises:["major-step","minor-proof"],variable:"k",discharge:"case",formula:conclusion}
 ],"eliminated");
 assert.equal(K.verify(proof).code,"INVALID_EXISTS_EIGENVARIABLE");
});
test("existential elimination requires its witness assumption in the minor proof",()=>{
 const witness=T.variable("k","Field"),P=x=>F.predicate("P",[x]);
 const major=F.exists("x","Field",P(T.variable("x","Field"))),conclusion=F.eq(T.rational(1,1),T.rational(1,1));
 const proof=mk("REAL_FIELD",[{id:"major",formula:major},{id:"case",formula:P(witness)}],[
  {id:"major-step",rule:"assumption",assumption:"major",formula:major},
  {id:"case-unused",rule:"assumption",assumption:"case",formula:P(witness)},
  {id:"truth",rule:"eq_refl",term:T.rational(1,1),formula:conclusion},
  {id:"eliminated",rule:"exists_elim",premises:["major-step","truth"],variable:"k",discharge:"case",formula:conclusion}
 ],"eliminated");
 assert.equal(K.verify(proof).code,"INVALID_EXISTS_ELIMINATION_SCOPE");
});

test("Euclidean first postulate has typed points, incidence and a distinctness condition",()=>{
 const formula=K.AXIOMS["EUCLID-01"].formula;
 assert.equal(K.validFormula(formula,{},new Set(K.SYSTEMS.EUCLID_GEOMETRY.sorts)),true);
 const proof=mk("EUCLID_GEOMETRY",[],[{id:"euclid",rule:"axiom",axiomId:"EUCLID-01",formula}],"euclid");
 const result=K.verify(proof);
 assert.equal(result.valid,true);
 assert.deepEqual(result.usedAxioms,["EUCLID-01"]);
 const wrong=mk("REAL_FIELD",[],[{id:"euclid",rule:"axiom",axiomId:"EUCLID-01",formula}],"euclid");
 assert.equal(K.verify(wrong).code,"AXIOM_NOT_AVAILABLE");
});
test("line and incidence nodes reject incompatible geometric sorts",()=>{
 assert.equal(K.termSort(T.line("l")),"Line");
 assert.equal(K.validFormula(F.incident(T.point("A"),T.line("l")),{},new Set(K.SYSTEMS.EUCLID_GEOMETRY.sorts)),true);
 assert.equal(K.validFormula(F.incident(T.event("A"),T.line("l")),{},new Set(K.SYSTEMS.EUCLID_GEOMETRY.sorts)),false);
 assert.equal(K.validFormula({...F.incident(T.point("A"),T.line("l")),extra:true},{},new Set(K.SYSTEMS.EUCLID_GEOMETRY.sorts)),false);
});
test("Kolmogorov nonnegativity and normalization axioms replay by exact ID",()=>{
 for(const id of ["PROB-01","PROB-02"]){
  const formula=K.AXIOMS[id].formula;
  assert.equal(K.validFormula(formula,{},new Set(K.SYSTEMS.KOLMOGOROV.sorts)),true,id);
  const proof=mk("KOLMOGOROV",[],[{id:"ax",rule:"axiom",axiomId:id,formula}],"ax");
  const result=K.verify(proof);
  assert.equal(result.valid,true,id);
  assert.deepEqual(result.usedAxioms,[id],id);
  const wrong=mk("REAL_FIELD",[],[{id:"ax",rule:"axiom",axiomId:id,formula}],"ax");
  assert.equal(K.verify(wrong).code,"AXIOM_NOT_AVAILABLE",id);
 }
});
test("probability measure terms require an Event and real-valued order",()=>{
 assert.equal(K.termSort(T.sampleSpace()),"Event");
 assert.equal(K.termSort(T.measure(T.event("A"))),"Real");
 assert.equal(K.termSort(T.measure(T.set("A"))),null);
 assert.equal(K.termSort(T.real(1,0)),null);
 assert.equal(K.termSort(T.real(-1,1)),"Real");
 assert.equal(K.validFormula(F.le(T.real(0,1),T.measure(T.event("A"))),{},new Set(K.SYSTEMS.KOLMOGOROV.sorts)),true);
 assert.equal(K.validFormula(F.le(T.measure(T.event("A")),T.real(0,1)),{},new Set(K.SYSTEMS.KOLMOGOROV.sorts)),true);
 assert.equal(K.validFormula(F.le(T.measure(T.event("A")),T.rational(1,1)),{},new Set(K.SYSTEMS.KOLMOGOROV.sorts)),false);
 assert.equal(K.validFormula({...F.le(T.real(0,1),T.measure(T.event("A"))),extra:true},{},new Set(K.SYSTEMS.KOLMOGOROV.sorts)),false);
 assert.equal(K.validFormula(F.lt(T.rational(1,2),T.real(1,1)),{},new Set(K.SYSTEMS.KOLMOGOROV.sorts)),false);
});
test("ZFC extensionality and empty-set axioms replay with set-only terms",()=>{
 for(const id of ["ZFC-01","ZFC-02"]){
  const formula=K.AXIOMS[id].formula;
  assert.equal(K.validFormula(formula,{},new Set(K.SYSTEMS.ZFC.sorts)),true,id);
  const proof=mk("ZFC",[],[{id:"ax",rule:"axiom",axiomId:id,formula}],"ax");
  const result=K.verify(proof);
  assert.equal(result.valid,true,id);
  assert.deepEqual(result.usedAxioms,[id],id);
  const wrong=mk("PEANO_N",[],[{id:"ax",rule:"axiom",axiomId:id,formula}],"ax");
  assert.equal(K.verify(wrong).code,"AXIOM_NOT_AVAILABLE",id);
 }
});
test("new formal contexts reject forged statements and incompatible terms",()=>{
 for(const [system,id] of [["EUCLID_GEOMETRY","EUCLID-01"],["KOLMOGOROV","PROB-01"],["ZFC","ZFC-01"]]){
  const forged=mk(system,[],[{id:"ax",rule:"axiom",axiomId:id,formula:F.predicate("forged",[])}],"ax");
  assert.equal(K.verify(forged).code,"RULE_MISMATCH",id);
 }
 const fieldLine=mk("REAL_FIELD",[],[{id:"x",rule:"eq_refl",term:T.line("l"),formula:F.eq(T.line("l"),T.line("l"))}],"x");
 const zfcPoint=mk("ZFC",[],[{id:"x",rule:"eq_refl",term:T.point("A"),formula:F.eq(T.point("A"),T.point("A"))}],"x");
 const geometryEvent=mk("EUCLID_GEOMETRY",[],[{id:"x",rule:"eq_refl",term:T.event("e"),formula:F.eq(T.event("e"),T.event("e"))}],"x");
 assert.equal(K.verify(fieldLine).code,"INVALID_STEP");
 assert.equal(K.verify(zfcPoint).code,"INVALID_STEP");
 assert.equal(K.verify(geometryEvent).code,"INVALID_STEP");
});
test("countable additivity remains disabled until sequence and sum operators exist",()=>{
 assert.equal(K.AXIOMS["PROB-03"],undefined);
 assert.deepEqual(K.SYSTEMS.KOLMOGOROV.enabledAxioms,["PROB-01","PROB-02"]);
});
