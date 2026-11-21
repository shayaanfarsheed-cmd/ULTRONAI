(function (root) {
"use strict";
function deepFreeze(value){if(value&&typeof value==="object"&&!Object.isFrozen(value)){Object.keys(value).forEach(key=>deepFreeze(value[key]));Object.freeze(value);}return value;}
const SYSTEMS=deepFreeze({
 PEANO_N:{label:"Peano arithmetic",sorts:["Nat"],enabledAxioms:["PEANO-02","PEANO-03"],enabledAxiomSchemas:["PEANO-04"]},
 REAL_FIELD:{label:"Field theory",sorts:["Field"],enabledAxioms:["FIELD-01","FIELD-02","FIELD-03","FIELD-04","FIELD-05","FIELD-06","FIELD-07","FIELD-08","FIELD-09"],enabledAxiomSchemas:[]},
 ORDERED_FIELD:{label:"Ordered-field theory",sorts:["Field"],enabledAxioms:[],enabledAxiomSchemas:[]},
 COMPLETE_REAL:{label:"Complete real field",sorts:["Field"],enabledAxioms:[],enabledAxiomSchemas:[]},
 EUCLID_GEOMETRY:{label:"Euclidean geometry",sorts:["Point","Line"],enabledAxioms:["EUCLID-01","EUCLID-02"],enabledAxiomSchemas:[]},
 KOLMOGOROV:{label:"Kolmogorov probability",sorts:["Event","Real"],enabledAxioms:["PROB-01","PROB-02"],enabledAxiomSchemas:[]},
 ZFC:{label:"Zermelo–Fraenkel set theory with Choice",sorts:["Set"],enabledAxioms:["ZFC-01","ZFC-02","ZFC-03","ZFC-04","ZFC-05","ZFC-06","ZFC-09"],enabledAxiomSchemas:[]}
});
const T=Object.freeze({
 variable:(name,sort)=>({kind:"var",name,sort}), numeral:value=>({kind:"nat",value}),
 succ:value=>({kind:"succ",value}), add:(left,right)=>({kind:"add",left,right}),
 multiply:(left,right)=>({kind:"mul",left,right}),
 rational:(numerator,denominator)=>({kind:"rational",numerator,denominator}),
 point:name=>({kind:"point",name}), line:name=>({kind:"line",name}), event:name=>({kind:"event",name}), set:name=>({kind:"set",name}),
 real:(numerator,denominator)=>({kind:"real",numerator,denominator}),
 sampleSpace:()=>({kind:"sampleSpace"}), measure:event=>({kind:"measure",event})
});
const F=Object.freeze({
 eq:(left,right)=>({kind:"eq",left,right}), lt:(left,right)=>({kind:"lt",left,right}),
 and:(left,right)=>({kind:"and",left,right}), implies:(left,right)=>({kind:"implies",left,right}),
 forall:(name,sort,body)=>({kind:"forall",name,sort,body}), exists:(name,sort,body)=>({kind:"exists",name,sort,body}), not:formula=>({kind:"not",formula}),
 member:(term,set)=>({kind:"member",term,set}), incident:(point,line)=>({kind:"incident",point,line}), between:(first,middle,last)=>({kind:"between",first,middle,last}), predicate:(name,args)=>({kind:"predicate",name,args:args||[]})
});
const isObj=x=>!!x&&typeof x==="object"&&!Array.isArray(x), stable=x=>JSON.stringify(x), clone=x=>JSON.parse(JSON.stringify(x));
function exactKeys(value,required,optional=[]){if(!isObj(value))return false;const allowed=new Set(required.concat(optional));const keys=Reflect.ownKeys(value);return required.every(key=>Object.prototype.hasOwnProperty.call(value,key))&&keys.every(key=>typeof key==="string"&&allowed.has(key));}
function denseArray(value){if(!Array.isArray(value))return false;for(let i=0;i<value.length;i++)if(!Object.prototype.hasOwnProperty.call(value,i))return false;return true;}
function validStepShape(step){
 if(!isObj(step)||typeof step.rule!=="string")return false;
 const base=["id","rule","formula"];
 const emptyOptionalPremises=()=>!Object.prototype.hasOwnProperty.call(step,"premises")||(denseArray(step.premises)&&step.premises.length===0);
 switch(step.rule){
  case "assumption":return exactKeys(step,base,["assumption","premises"])&&Object.prototype.hasOwnProperty.call(step,"assumption")&&typeof step.assumption==="string"&&emptyOptionalPremises();
  case "axiom":return exactKeys(step,base,["axiomId","premises"])&&Object.prototype.hasOwnProperty.call(step,"axiomId")&&typeof step.axiomId==="string"&&emptyOptionalPremises();
  case "eq_refl":return exactKeys(step,base,["term","premises"])&&Object.prototype.hasOwnProperty.call(step,"term")&&emptyOptionalPremises();
  case "eq_symm":case "eq_trans":case "and_intro":case "and_left":case "and_right":case "imp_elim":return exactKeys(step,base.concat("premises"))&&denseArray(step.premises);
  case "imp_intro":return exactKeys(step,base.concat(["premises","discharge"]))&&denseArray(step.premises)&&Object.prototype.hasOwnProperty.call(step,"discharge")&&typeof step.discharge==="string";
  case "forall_elim":return exactKeys(step,base.concat(["premises","term"]))&&denseArray(step.premises)&&Object.prototype.hasOwnProperty.call(step,"term");
  case "exists_intro":return exactKeys(step,base.concat(["premises","term"]))&&denseArray(step.premises)&&step.premises.length===1&&Object.prototype.hasOwnProperty.call(step,"term");
  case "exists_elim":return exactKeys(step,base.concat(["premises","variable","discharge"]))&&denseArray(step.premises)&&step.premises.length===2&&Object.prototype.hasOwnProperty.call(step,"variable")&&typeof step.variable==="string"&&step.variable.length>0&&Object.prototype.hasOwnProperty.call(step,"discharge")&&typeof step.discharge==="string";
  case "forall_intro":return exactKeys(step,base.concat(["premises","variable"]))&&denseArray(step.premises)&&step.premises.length===1&&Object.prototype.hasOwnProperty.call(step,"variable")&&typeof step.variable==="string"&&step.variable.length>0;
  case "induction":return exactKeys(step,base.concat(["premises","axiomId","variable"]))&&denseArray(step.premises)&&step.premises.length===2&&Object.prototype.hasOwnProperty.call(step,"axiomId")&&step.axiomId==="PEANO-04"&&Object.prototype.hasOwnProperty.call(step,"variable")&&typeof step.variable==="string"&&step.variable.length>0;
  default:return false;
 }
}
function termSort(t,bound={}) {
 if(!isObj(t))return null;
 switch(t.kind){
 case "var":return exactKeys(t,["kind","name","sort"])&&typeof t.name==="string"&&typeof t.sort==="string"&&(!bound[t.name]||bound[t.name]===t.sort)?(bound[t.name]||t.sort):null;
 case "nat":return exactKeys(t,["kind","value"])&&Number.isSafeInteger(t.value)&&t.value>=0?"Nat":null;
 case "succ":return exactKeys(t,["kind","value"])&&termSort(t.value,bound)==="Nat"?"Nat":null;
 case "add":case "mul":{if(!exactKeys(t,["kind","left","right"]))return null;const a=termSort(t.left,bound),b=termSort(t.right,bound);return a&&a===b&&(a==="Nat"||a==="Field")?a:null;}
 case "rational":return exactKeys(t,["kind","numerator","denominator"])&&Number.isSafeInteger(t.numerator)&&Number.isSafeInteger(t.denominator)&&t.denominator!==0?"Field":null;
 case "point":return exactKeys(t,["kind","name"])&&typeof t.name==="string"&&t.name?"Point":null;
 case "event":return exactKeys(t,["kind","name"])&&typeof t.name==="string"&&t.name?"Event":null;
 case "set":return exactKeys(t,["kind","name"])&&typeof t.name==="string"&&t.name?"Set":null;
 case "line":return exactKeys(t,["kind","name"])&&typeof t.name==="string"&&t.name?"Line":null;
 case "real":return exactKeys(t,["kind","numerator","denominator"])&&Number.isSafeInteger(t.numerator)&&Number.isSafeInteger(t.denominator)&&t.denominator!==0?"Real":null;
 case "sampleSpace":return exactKeys(t,["kind"])?"Event":null;
 case "measure":return exactKeys(t,["kind","event"])&&termSort(t.event,bound)==="Event"?"Real":null;
 default:return null;
 }
}
function validFormula(f,bound={},allowedSorts=null) {
 if(!isObj(f))return false;
 switch(f.kind){
 case "eq":{if(!exactKeys(f,["kind","left","right"]))return false;const sort=termSort(f.left,bound);return !!sort&&sort===termSort(f.right,bound)&&(!allowedSorts||allowedSorts.has(sort));}
 case "lt":{if(!exactKeys(f,["kind","left","right"]))return false;const sort=termSort(f.left,bound);return ["Nat","Field","Real"].includes(sort)&&sort===termSort(f.right,bound)&&(!allowedSorts||allowedSorts.has(sort));}
 case "and":case "implies":return exactKeys(f,["kind","left","right"])&&validFormula(f.left,bound,allowedSorts)&&validFormula(f.right,bound,allowedSorts);
 case "not":return exactKeys(f,["kind","formula"])&&validFormula(f.formula,bound,allowedSorts);
 case "forall":case "exists":{if(!exactKeys(f,["kind","name","sort","body"])||typeof f.name!=="string"||!["Nat","Field","Real","Point","Line","Event","Probability","Set"].includes(f.sort)||(allowedSorts&&!allowedSorts.has(f.sort)))return false;return validFormula(f.body,Object.assign({},bound,{[f.name]:f.sort}),allowedSorts);}
 case "member":{if(!exactKeys(f,["kind","term","set"]))return false;const a=termSort(f.term,bound),b=termSort(f.set,bound);return !!a&&b==="Set"&&(!allowedSorts||(allowedSorts.has(a)&&allowedSorts.has(b)));}
 case "incident":return exactKeys(f,["kind","point","line"])&&termSort(f.point,bound)==="Point"&&termSort(f.line,bound)==="Line"&&(!allowedSorts||(allowedSorts.has("Point")&&allowedSorts.has("Line")));
 case "between":return exactKeys(f,["kind","first","middle","last"])&&termSort(f.first,bound)==="Point"&&termSort(f.middle,bound)==="Point"&&termSort(f.last,bound)==="Point"&&(!allowedSorts||allowedSorts.has("Point"));
 case "predicate":return exactKeys(f,["kind","name","args"])&&typeof f.name==="string"&&!!f.name&&denseArray(f.args)&&f.args.every(x=>{const sort=termSort(x,bound);return !!sort&&(!allowedSorts||allowedSorts.has(sort));});
 default:return false;
 }
}
function freeVariableNames(node,bound=new Set(),out=new Set()){
 if(!isObj(node))return out;
 if(node.kind==="var"){if(!bound.has(node.name))out.add(node.name);return out;}
 if(node.kind==="forall"||node.kind==="exists"){const next=new Set(bound);next.add(node.name);freeVariableNames(node.body,next,out);return out;}
 for(const value of Object.values(node)){if(Array.isArray(value))value.forEach(x=>freeVariableNames(x,bound,out));else if(isObj(value))freeVariableNames(value,bound,out);}
 return out;
}
function allVariableNames(node,out=new Set()){
 if(!isObj(node))return out;
 if(node.kind==="var"||node.kind==="forall"||node.kind==="exists")out.add(node.name);
 for(const value of Object.values(node)){if(Array.isArray(value))value.forEach(x=>allVariableNames(x,out));else if(isObj(value))allVariableNames(value,out);}
 return out;
}
function hasFreeVariableInDependencies(refs,name,available){
 for(const ref of refs){for(const assumptionId of ref.dependencies){const dependency=available.get(assumptionId);if(dependency&&dependency.origin==="assumption"&&freeVariableNames(dependency.formula).has(name))return true;}}
 return false;
}
function substitute(node,name,replacement){
 if(!isObj(node))return node;
 if(node.kind==="var"&&node.name===name)return clone(replacement);
 if((node.kind==="forall"||node.kind==="exists")&&node.name===name)return clone(node);
 if((node.kind==="forall"||node.kind==="exists")&&freeVariableNames(replacement).has(node.name))return null;
 const out={};for(const k of Object.keys(node))out[k]=Array.isArray(node[k])?node[k].map(x=>substitute(x,name,replacement)):isObj(node[k])?substitute(node[k],name,replacement):node[k];return out;
}
const equivalent=(a,b)=>F.and(F.implies(a,b),F.implies(b,a));
const disjunction=(a,b)=>F.not(F.and(F.not(a),F.not(b)));
const pointVar=name=>T.variable(name,"Point");
const lineVar=name=>T.variable(name,"Line");
const and4=(a,b,c,d)=>F.and(a,F.and(b,F.and(c,d)));
const EUCLID_SEGMENT_EXTENSION=F.forall("A","Point",
 F.forall("B","Point",
  F.implies(
   F.not(F.eq(pointVar("A"),pointVar("B"))),
   F.exists("C","Point",
    F.exists("l","Line",
     and4(
      F.incident(pointVar("A"),lineVar("l")),
      F.incident(pointVar("B"),lineVar("l")),
      F.incident(pointVar("C"),lineVar("l")),
      F.between(pointVar("A"),pointVar("B"),pointVar("C"))
     )
    )
   )
  )
 )
);
const AXIOMS=deepFreeze({
 "PEANO-02":{system:"PEANO_N",formula:F.forall("n","Nat",F.not(F.eq(T.succ(T.variable("n","Nat")),T.numeral(0))))},
 "PEANO-03":{system:"PEANO_N",formula:F.forall("m","Nat",F.forall("n","Nat",F.implies(F.eq(T.succ(T.variable("m","Nat")),T.succ(T.variable("n","Nat"))),F.eq(T.variable("m","Nat"),T.variable("n","Nat")))))},
 "FIELD-01":{system:"REAL_FIELD",formula:F.forall("a","Field",F.forall("b","Field",F.eq(T.add(T.variable("a","Field"),T.variable("b","Field")),T.add(T.variable("b","Field"),T.variable("a","Field")))))},
 "FIELD-02":{system:"REAL_FIELD",formula:F.forall("a","Field",F.forall("b","Field",F.forall("c","Field",F.eq(T.add(T.add(T.variable("a","Field"),T.variable("b","Field")),T.variable("c","Field")),T.add(T.variable("a","Field"),T.add(T.variable("b","Field"),T.variable("c","Field")))))))},
 "FIELD-03":{system:"REAL_FIELD",formula:F.forall("a","Field",F.and(F.eq(T.add(T.variable("a","Field"),T.rational(0,1)),T.variable("a","Field")),F.eq(T.add(T.rational(0,1),T.variable("a","Field")),T.variable("a","Field"))))},
 "FIELD-04":{system:"REAL_FIELD",formula:F.forall("a","Field",F.exists("b","Field",F.eq(T.add(T.variable("a","Field"),T.variable("b","Field")),T.rational(0,1))))},
 "FIELD-05":{system:"REAL_FIELD",formula:F.forall("a","Field",F.forall("b","Field",F.eq(T.multiply(T.variable("a","Field"),T.variable("b","Field")),T.multiply(T.variable("b","Field"),T.variable("a","Field")))))},
 "FIELD-06":{system:"REAL_FIELD",formula:F.forall("a","Field",F.forall("b","Field",F.forall("c","Field",F.eq(T.multiply(T.multiply(T.variable("a","Field"),T.variable("b","Field")),T.variable("c","Field")),T.multiply(T.variable("a","Field"),T.multiply(T.variable("b","Field"),T.variable("c","Field")))))))},
 "FIELD-07":{system:"REAL_FIELD",formula:F.and(F.not(F.eq(T.rational(1,1),T.rational(0,1))),F.forall("a","Field",F.and(F.eq(T.multiply(T.variable("a","Field"),T.rational(1,1)),T.variable("a","Field")),F.eq(T.multiply(T.rational(1,1),T.variable("a","Field")),T.variable("a","Field")))))},
 "FIELD-08":{system:"REAL_FIELD",formula:F.forall("a","Field",F.implies(F.not(F.eq(T.variable("a","Field"),T.rational(0,1))),F.exists("b","Field",F.eq(T.multiply(T.variable("a","Field"),T.variable("b","Field")),T.rational(1,1)))))},
 "FIELD-09":{system:"REAL_FIELD",formula:F.forall("a","Field",F.forall("b","Field",F.forall("c","Field",F.eq(T.multiply(T.variable("a","Field"),T.add(T.variable("b","Field"),T.variable("c","Field"))),T.add(T.multiply(T.variable("a","Field"),T.variable("b","Field")),T.multiply(T.variable("a","Field"),T.variable("c","Field")))))))},
 "EUCLID-01":{system:"EUCLID_GEOMETRY",formula:F.forall("A","Point",F.forall("B","Point",F.implies(F.not(F.eq(T.variable("A","Point"),T.variable("B","Point"))),F.exists("l","Line",F.and(F.incident(T.variable("A","Point"),T.variable("l","Line")),F.incident(T.variable("B","Point"),T.variable("l","Line")))))))},
 "EUCLID-02":{system:"EUCLID_GEOMETRY",formula:EUCLID_SEGMENT_EXTENSION},
 "PROB-01":{system:"KOLMOGOROV",formula:F.forall("A","Event",F.not(F.lt(T.measure(T.variable("A","Event")),T.real(0,1))))},
 "PROB-02":{system:"KOLMOGOROV",formula:F.eq(T.measure(T.sampleSpace()),T.real(1,1))},
 "ZFC-01":{system:"ZFC",formula:F.forall("A","Set",F.forall("B","Set",F.implies(F.forall("z","Set",F.and(F.implies(F.member(T.variable("z","Set"),T.variable("A","Set")),F.member(T.variable("z","Set"),T.variable("B","Set"))),F.implies(F.member(T.variable("z","Set"),T.variable("B","Set")),F.member(T.variable("z","Set"),T.variable("A","Set"))))),F.eq(T.variable("A","Set"),T.variable("B","Set")))))},
 "ZFC-02":{system:"ZFC",formula:F.exists("E","Set",F.forall("x","Set",F.not(F.member(T.variable("x","Set"),T.variable("E","Set")))))},
 "ZFC-03":{system:"ZFC",formula:F.forall("a","Set",F.forall("b","Set",F.exists("c","Set",F.forall("x","Set",
  equivalent(F.member(T.variable("x","Set"),T.variable("c","Set")),disjunction(
   F.eq(T.variable("x","Set"),T.variable("a","Set")),
   F.eq(T.variable("x","Set"),T.variable("b","Set"))
  ))
 ))))},
 "ZFC-04":{system:"ZFC",formula:F.forall("A","Set",F.exists("B","Set",F.forall("x","Set",
  equivalent(F.member(T.variable("x","Set"),T.variable("B","Set")),F.exists("y","Set",F.and(
   F.member(T.variable("y","Set"),T.variable("A","Set")),
   F.member(T.variable("x","Set"),T.variable("y","Set"))
  )))
 )))},
 "ZFC-05":{system:"ZFC",formula:F.forall("A","Set",F.exists("P","Set",F.forall("X","Set",
  equivalent(F.member(T.variable("X","Set"),T.variable("P","Set")),F.forall("y","Set",F.implies(
   F.member(T.variable("y","Set"),T.variable("X","Set")),
   F.member(T.variable("y","Set"),T.variable("A","Set"))
  )))
 )))},
 "ZFC-06":{system:"ZFC",formula:F.exists("I","Set",F.and(
  F.exists("E","Set",F.and(
   F.forall("z","Set",F.not(F.member(T.variable("z","Set"),T.variable("E","Set")))),
   F.member(T.variable("E","Set"),T.variable("I","Set"))
  )),
  F.forall("x","Set",F.implies(F.member(T.variable("x","Set"),T.variable("I","Set")),F.exists("Y","Set",F.and(
   F.forall("z","Set",equivalent(
    F.member(T.variable("z","Set"),T.variable("Y","Set")),
    disjunction(F.member(T.variable("z","Set"),T.variable("x","Set")),F.eq(T.variable("z","Set"),T.variable("x","Set")))
   )),
   F.member(T.variable("Y","Set"),T.variable("I","Set"))
  ))))
 ))},
 "ZFC-09":{system:"ZFC",formula:F.forall("X","Set",F.implies(
  F.exists("z","Set",F.member(T.variable("z","Set"),T.variable("X","Set"))),
  F.exists("y","Set",F.and(
   F.member(T.variable("y","Set"),T.variable("X","Set")),
   F.forall("z","Set",F.implies(F.member(T.variable("z","Set"),T.variable("y","Set")),F.not(F.member(T.variable("z","Set"),T.variable("X","Set")))))
  ))
 ))}
});
const AXIOM_SCHEMAS=deepFreeze({
 "PEANO-04":{system:"PEANO_N",rule:"induction",description:"From P(0) and ∀k(P(k)→P(S(k))), derive ∀n P(n)."}
});
const err=(code,message,stepId)=>({valid:false,code,message,stepId:stepId||null});
function verify(p){
 if(!exactKeys(p,["version","system","assumptions","steps","conclusion"])||p.version!==1||!Object.hasOwn(SYSTEMS,p.system)||!denseArray(p.assumptions)||!denseArray(p.steps)||!p.steps.length||typeof p.conclusion!=="string")return err("MALFORMED_PROOF","Malformed proof envelope or unknown system.");
 const sys=SYSTEMS[p.system],allowedSorts=new Set(sys.sorts),available=new Map(),used=[],usedSchemas=[];
 for(const a of p.assumptions){if(!exactKeys(a,["id","formula"])||typeof a.id!=="string"||available.has(a.id)||!validFormula(a.formula,{},allowedSorts))return err("INVALID_ASSUMPTION","Assumptions need unique IDs and well-typed formulas.");available.set(a.id,{formula:a.formula,origin:"assumption",dependencies:new Set([a.id])});}
 for(const s of p.steps){
  if(!isObj(s)||typeof s.id!=="string"||available.has(s.id))return err("INVALID_STEP","Each step needs a unique ID.",s&&s.id);
  if(!validStepShape(s)){if(typeof s.rule==="string"&&!["assumption","axiom","eq_refl","eq_symm","eq_trans","and_intro","and_left","and_right","imp_elim","imp_intro","forall_elim","forall_intro","exists_intro","exists_elim","induction"].includes(s.rule))return err("UNKNOWN_RULE","Rule is not part of the audited kernel.",s.id);return err("INVALID_STEP","Step contains missing, unexpected, or malformed fields.",s.id);}
  if(s.rule==="axiom"){const registered=AXIOMS[s.axiomId];if(!registered||registered.system!==p.system||!sys.enabledAxioms.includes(s.axiomId))return err("AXIOM_NOT_AVAILABLE","Axiom is unknown, not formalized, or unavailable in this system.",s.id);}
  if(s.rule==="induction"){const schema=AXIOM_SCHEMAS[s.axiomId];if(!schema||schema.system!==p.system||!sys.enabledAxiomSchemas.includes(s.axiomId))return err("AXIOM_SCHEMA_NOT_AVAILABLE","Axiom schema is unknown or unavailable in this formal system.",s.id);}
  if(!validFormula(s.formula,{},allowedSorts))return err("INVALID_STEP","Proof step formula is not well-typed in its declared formal system.",s.id);
  const ids=s.premises||[];if(!Array.isArray(ids))return err("INVALID_PREMISES","Premises must be an array.",s.id);
  const refs=ids.map(id=>available.get(id));if(refs.some(x=>!x))return err("UNKNOWN_PREMISE","Missing or forward proof reference.",s.id);
  let e=null;
  switch(s.rule){
   case "assumption":{const a=p.assumptions.find(x=>x.id===s.assumption);if(a&&!ids.length)e=a.formula;break;}
   case "axiom":{const a=AXIOMS[s.axiomId];if(ids.length)return err("RULE_MISMATCH","Axiom steps cannot have premises.",s.id);if(!a||a.system!==p.system||!sys.enabledAxioms.includes(s.axiomId))return err("AXIOM_NOT_AVAILABLE","Axiom is unknown, not formalized, or unavailable in this system.",s.id);e=a.formula;used.push(s.axiomId);break;}
   case "eq_refl":if(s.term&&termSort(s.term)&&!ids.length)e=F.eq(s.term,s.term);break;
   case "eq_symm":if(refs.length===1&&refs[0].formula.kind==="eq")e=F.eq(refs[0].formula.right,refs[0].formula.left);break;
   case "eq_trans":if(refs.length===2&&refs.every(x=>x.formula.kind==="eq")&&stable(refs[0].formula.right)===stable(refs[1].formula.left))e=F.eq(refs[0].formula.left,refs[1].formula.right);break;
   case "and_intro":if(refs.length===2)e=F.and(refs[0].formula,refs[1].formula);break;
   case "and_left":if(refs.length===1&&refs[0].formula.kind==="and")e=refs[0].formula.left;break;
   case "and_right":if(refs.length===1&&refs[0].formula.kind==="and")e=refs[0].formula.right;break;
   case "imp_elim":if(refs.length===2){const i=refs.find(x=>x.formula.kind==="implies"),a=refs.find(x=>x!==i);if(i&&a&&stable(i.formula.left)===stable(a.formula))e=i.formula.right;}break;
   case "imp_intro":{const r=refs.length===1?refs[0]:null,d=available.get(s.discharge);if(r&&d&&d.origin==="assumption"&&r.dependencies.has(s.discharge)&&s.formula.kind==="implies"&&stable(d.formula)===stable(s.formula.left)&&stable(r.formula)===stable(s.formula.right))e=s.formula;break;}
   case "forall_elim":if(refs.length===1&&refs[0].formula.kind==="forall"&&s.term&&termSort(s.term)===refs[0].formula.sort){const candidate=substitute(refs[0].formula.body,refs[0].formula.name,s.term);if(candidate&&validFormula(candidate,{},allowedSorts))e=candidate;}break;
   case "exists_intro":{
    const goal=s.formula,witness=s.term;
    if(refs.length===1&&goal.kind==="exists"&&termSort(witness)===goal.sort){
     const instance=substitute(goal.body,goal.name,witness);
     if(instance&&validFormula(instance,{},allowedSorts)&&stable(refs[0].formula)===stable(instance))e=goal;
    }
    break;
   }
   case "exists_elim":{
    const existential=refs[0].formula,minor=refs[1],variable=s.variable,discharged=available.get(s.discharge);
    if(existential.kind!=="exists"||!discharged||discharged.origin!=="assumption"||!minor.dependencies.has(s.discharge)||refs[0].dependencies.has(s.discharge))return err("INVALID_EXISTS_ELIMINATION_SCOPE","Existential elimination needs a minor proof using a temporary witness assumption, and that assumption cannot support the existential premise.",s.id);
    if(variable===existential.name||allVariableNames(existential.body).has(variable)||freeVariableNames(existential).has(variable)||freeVariableNames(s.formula).has(variable))return err("INVALID_EXISTS_EIGENVARIABLE","Existential witness variable must be fresh from the existential premise and conclusion.",s.id);
    const expectedWitness=substitute(existential.body,existential.name,T.variable(variable,existential.sort));
    if(!expectedWitness||!validFormula(expectedWitness,{},allowedSorts)||stable(discharged.formula)!==stable(expectedWitness)||stable(s.formula)!==stable(minor.formula))return err("RULE_MISMATCH","Discharged assumption must be the existential body for the fresh witness, and the conclusion must match the minor proof.",s.id);
    const remainingDependencies=new Set([...refs[0].dependencies,...minor.dependencies]);remainingDependencies.delete(s.discharge);
    if(hasFreeVariableInDependencies([{dependencies:remainingDependencies}],variable,available))return err("EXISTS_EIGENVARIABLE_IN_ASSUMPTION","Existential witness variable must not occur free in any remaining undischarged assumption.",s.id);
    e=minor.formula;
    break;
   }
   case "forall_intro":{
    const goal=s.formula,variable=s.variable;
    if(goal.kind!=="forall"||variable===goal.name||allVariableNames(goal.body).has(variable))return err("INVALID_EIGENVARIABLE","Universal-introduction variable must be fresh from the quantified property and its binders.",s.id);
    if(hasFreeVariableInDependencies(refs,variable,available))return err("EIGENVARIABLE_IN_ASSUMPTION","Universal-introduction variable must not occur free in any undischarged assumption used by the premise.",s.id);
    const instance=substitute(goal.body,goal.name,T.variable(variable,goal.sort));
    if(instance&&validFormula(instance,{},allowedSorts)&&stable(refs[0].formula)===stable(instance))e=goal;
    break;
   }
   case "induction":{
    const goal=s.formula,variable=s.variable;
    if(goal.kind!=="forall"||goal.sort!=="Nat"||variable===goal.name||allVariableNames(goal.body).has(variable))return err("INVALID_INDUCTION_VARIABLE","Induction variable must be fresh and distinct from every variable and binder in the property.",s.id);
    if(hasFreeVariableInDependencies(refs,variable,available))return err("INDUCTION_VARIABLE_IN_ASSUMPTION","Induction variable must not occur free in any undischarged assumption used by the base or successor step.",s.id);
    const base=substitute(goal.body,goal.name,T.numeral(0));
    const inductionVariable=T.variable(variable,"Nat");
    const before=substitute(goal.body,goal.name,inductionVariable);
    const after=substitute(goal.body,goal.name,T.succ(inductionVariable));
    if(!base||!before||!after||!validFormula(base,{},allowedSorts))break;
    const requiredStep=F.forall(variable,"Nat",F.implies(before,after));
    if(validFormula(requiredStep,{},allowedSorts)&&stable(refs[0].formula)===stable(base)&&stable(refs[1].formula)===stable(requiredStep))e=goal;
    break;
   }
   default:return err("UNKNOWN_RULE","Rule is not part of the audited kernel.",s.id);
  }
  if(!e||stable(e)!==stable(s.formula))return err("RULE_MISMATCH","Conclusion does not follow from the selected rule and premises.",s.id);
  if(s.rule==="induction")usedSchemas.push(s.axiomId);
  const dependencies=new Set();
  if(s.rule==="assumption")dependencies.add(s.assumption);
  else refs.forEach(ref=>ref.dependencies.forEach(id=>dependencies.add(id)));
  if(s.rule==="imp_intro"||s.rule==="exists_elim")dependencies.delete(s.discharge);
  available.set(s.id,{formula:s.formula,origin:s.rule,dependencies});
 }
 const last=available.get(p.conclusion);if(!last||!p.steps.some(x=>x.id===p.conclusion))return err("MISSING_CONCLUSION","Conclusion must reference a derived step.");
 return {valid:true,system:p.system,conclusion:clone(last.formula),openAssumptions:[...last.dependencies].sort(),usedAxioms:[...new Set(used)],usedAxiomSchemas:[...new Set(usedSchemas)],checkedSteps:p.steps.length,trace:p.steps.map(x=>({id:x.id,rule:x.rule,formula:clone(x.formula),premises:(x.premises||[]).slice(),axiomId:x.axiomId||null,term:x.term?clone(x.term):null,variable:x.variable||null,discharge:x.discharge||null}))};
}
function verifyWorkingTrace(trace){
 if(!exactKeys(trace,["kind","proof"],["claimedConclusion"])||trace.kind!=="ultron-proof-trace")return err("UNTRUSTED_TRACE","Working must be a strictly shaped structured proof trace.");
 const r=verify(trace.proof);if(!r.valid)return r;
 if(Object.prototype.hasOwnProperty.call(trace,"claimedConclusion")&&stable(trace.claimedConclusion)!==stable(r.conclusion))return err("FORGED_TRACE","Claimed conclusion differs from replayed derivation.");
 return Object.assign({},r,{traceValidated:true,diagnosisEligible:true});
}
const api=Object.freeze({SYSTEMS,AXIOMS,AXIOM_SCHEMAS,T,F,termSort,validFormula,verify,verifyWorkingTrace});
if(typeof module!=="undefined"&&module.exports)module.exports=api;root.ULTRON_PROOF_KERNEL=api;
})(typeof globalThis!=="undefined"?globalThis:this);
