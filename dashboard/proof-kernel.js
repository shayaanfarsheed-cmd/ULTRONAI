(function (root) {
"use strict";
function deepFreeze(value){if(value&&typeof value==="object"&&!Object.isFrozen(value)){Object.keys(value).forEach(key=>deepFreeze(value[key]));Object.freeze(value);}return value;}
const SYSTEMS=deepFreeze({
 PEANO_N:{label:"Peano arithmetic",sorts:["Nat"],enabledAxioms:["PEANO-03"]},
 REAL_FIELD:{label:"Field theory",sorts:["Field"],enabledAxioms:["FIELD-01"]},
 ORDERED_FIELD:{label:"Ordered-field theory",sorts:["Field"],enabledAxioms:[]},
 COMPLETE_REAL:{label:"Complete real field",sorts:["Field"],enabledAxioms:[]},
 EUCLID_GEOMETRY:{label:"Euclidean geometry",sorts:["Point","Line"],enabledAxioms:[]},
 KOLMOGOROV:{label:"Kolmogorov probability",sorts:["Event","Probability"],enabledAxioms:[]},
 ZFC:{label:"Zermelo–Fraenkel set theory with Choice",sorts:["Set"],enabledAxioms:[]}
});
const T=Object.freeze({
 variable:(name,sort)=>({kind:"var",name,sort}), numeral:value=>({kind:"nat",value}),
 succ:value=>({kind:"succ",value}), add:(left,right)=>({kind:"add",left,right}),
 multiply:(left,right)=>({kind:"mul",left,right}),
 rational:(numerator,denominator)=>({kind:"rational",numerator,denominator}),
 point:name=>({kind:"point",name}), event:name=>({kind:"event",name}), set:name=>({kind:"set",name})
});
const F=Object.freeze({
 eq:(left,right)=>({kind:"eq",left,right}), lt:(left,right)=>({kind:"lt",left,right}),
 and:(left,right)=>({kind:"and",left,right}), implies:(left,right)=>({kind:"implies",left,right}),
 forall:(name,sort,body)=>({kind:"forall",name,sort,body}),
 member:(term,set)=>({kind:"member",term,set}), predicate:(name,args)=>({kind:"predicate",name,args:args||[]})
});
const isObj=x=>!!x&&typeof x==="object"&&!Array.isArray(x), stable=x=>JSON.stringify(x), clone=x=>JSON.parse(JSON.stringify(x));
function termSort(t,bound={}) {
 if(!isObj(t))return null;
 switch(t.kind){
 case "var":return typeof t.name==="string"&&typeof t.sort==="string"&&(!bound[t.name]||bound[t.name]===t.sort)?(bound[t.name]||t.sort):null;
 case "nat":return Number.isSafeInteger(t.value)&&t.value>=0?"Nat":null;
 case "succ":return termSort(t.value,bound)==="Nat"?"Nat":null;
 case "add":case "mul":{const a=termSort(t.left,bound),b=termSort(t.right,bound);return a&&a===b&&(a==="Nat"||a==="Field")?a:null;}
 case "rational":return Number.isSafeInteger(t.numerator)&&Number.isSafeInteger(t.denominator)&&t.denominator!==0?"Field":null;
 case "point":return typeof t.name==="string"&&t.name?"Point":null;
 case "event":return typeof t.name==="string"&&t.name?"Event":null;
 case "set":return typeof t.name==="string"&&t.name?"Set":null;
 default:return null;
 }
}
function validFormula(f,bound={},allowedSorts=null) {
 if(!isObj(f))return false;
 switch(f.kind){
 case "eq":{const sort=termSort(f.left,bound);return !!sort&&sort===termSort(f.right,bound)&&(!allowedSorts||allowedSorts.has(sort));}
 case "lt":{const sort=termSort(f.left,bound);return ["Nat","Field"].includes(sort)&&sort===termSort(f.right,bound)&&(!allowedSorts||allowedSorts.has(sort));}
 case "and":case "implies":return validFormula(f.left,bound,allowedSorts)&&validFormula(f.right,bound,allowedSorts);
 case "forall":{if(typeof f.name!=="string"||!["Nat","Field","Point","Line","Event","Probability","Set"].includes(f.sort)||(allowedSorts&&!allowedSorts.has(f.sort)))return false;return validFormula(f.body,Object.assign({},bound,{[f.name]:f.sort}),allowedSorts);}
 case "member":{const a=termSort(f.term,bound),b=termSort(f.set,bound);return !!a&&b==="Set"&&(!allowedSorts||(allowedSorts.has(a)&&allowedSorts.has(b)));}
 case "predicate":return typeof f.name==="string"&&!!f.name&&Array.isArray(f.args)&&f.args.every(x=>{const sort=termSort(x,bound);return !!sort&&(!allowedSorts||allowedSorts.has(sort));});
 default:return false;
 }
}
function freeVariableNames(node,bound=new Set(),out=new Set()){
 if(!isObj(node))return out;
 if(node.kind==="var"){if(!bound.has(node.name))out.add(node.name);return out;}
 if(node.kind==="forall"){const next=new Set(bound);next.add(node.name);freeVariableNames(node.body,next,out);return out;}
 for(const value of Object.values(node)){if(Array.isArray(value))value.forEach(x=>freeVariableNames(x,bound,out));else if(isObj(value))freeVariableNames(value,bound,out);}
 return out;
}
function substitute(node,name,replacement){
 if(!isObj(node))return node;
 if(node.kind==="var"&&node.name===name)return clone(replacement);
 if(node.kind==="forall"&&node.name===name)return clone(node);
 if(node.kind==="forall"&&freeVariableNames(replacement).has(node.name))return null;
 const out={};for(const k of Object.keys(node))out[k]=Array.isArray(node[k])?node[k].map(x=>substitute(x,name,replacement)):isObj(node[k])?substitute(node[k],name,replacement):node[k];return out;
}
const AXIOMS=deepFreeze({
 "PEANO-03":{system:"PEANO_N",formula:F.forall("m","Nat",F.forall("n","Nat",F.implies(F.eq(T.succ(T.variable("m","Nat")),T.succ(T.variable("n","Nat"))),F.eq(T.variable("m","Nat"),T.variable("n","Nat")))))},
 "FIELD-01":{system:"REAL_FIELD",formula:F.forall("a","Field",F.forall("b","Field",F.eq(T.add(T.variable("a","Field"),T.variable("b","Field")),T.add(T.variable("b","Field"),T.variable("a","Field")))))}
});
const err=(code,message,stepId)=>({valid:false,code,message,stepId:stepId||null});
function verify(p){
 if(!isObj(p)||p.version!==1||!Object.hasOwn(SYSTEMS,p.system)||!Array.isArray(p.assumptions)||!Array.isArray(p.steps)||!p.steps.length||typeof p.conclusion!=="string")return err("MALFORMED_PROOF","Malformed proof envelope or unknown system.");
 const sys=SYSTEMS[p.system],allowedSorts=new Set(sys.sorts),available=new Map(),used=[];
 for(const a of p.assumptions){if(!isObj(a)||typeof a.id!=="string"||available.has(a.id)||!validFormula(a.formula,{},allowedSorts))return err("INVALID_ASSUMPTION","Assumptions need unique IDs and well-typed formulas.");available.set(a.id,{formula:a.formula,origin:"assumption",dependencies:new Set([a.id])});}
 for(const s of p.steps){
  if(!isObj(s)||typeof s.id!=="string"||available.has(s.id))return err("INVALID_STEP","Each step needs a unique ID.",s&&s.id);
  if(s.rule==="axiom"){const registered=AXIOMS[s.axiomId];if(!registered||registered.system!==p.system||!sys.enabledAxioms.includes(s.axiomId))return err("AXIOM_NOT_AVAILABLE","Axiom is unknown, not formalized, or unavailable in this system.",s.id);}
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
   default:return err("UNKNOWN_RULE","Rule is not part of the audited kernel.",s.id);
  }
  if(!e||stable(e)!==stable(s.formula))return err("RULE_MISMATCH","Conclusion does not follow from the selected rule and premises.",s.id);
  const dependencies=new Set();
  if(s.rule==="assumption")dependencies.add(s.assumption);
  else refs.forEach(ref=>ref.dependencies.forEach(id=>dependencies.add(id)));
  if(s.rule==="imp_intro")dependencies.delete(s.discharge);
  available.set(s.id,{formula:s.formula,origin:s.rule,dependencies});
 }
 const last=available.get(p.conclusion);if(!last||!p.steps.some(x=>x.id===p.conclusion))return err("MISSING_CONCLUSION","Conclusion must reference a derived step.");
 return {valid:true,system:p.system,conclusion:clone(last.formula),openAssumptions:[...last.dependencies].sort(),usedAxioms:[...new Set(used)],checkedSteps:p.steps.length,trace:p.steps.map(x=>({id:x.id,rule:x.rule,formula:clone(x.formula),premises:(x.premises||[]).slice(),axiomId:x.axiomId||null}))};
}
function verifyWorkingTrace(trace){
 if(!isObj(trace)||trace.kind!=="ultron-proof-trace")return err("UNTRUSTED_TRACE","Working must be a structured proof trace.");
 const r=verify(trace.proof);if(!r.valid)return r;
 if(trace.claimedConclusion&&stable(trace.claimedConclusion)!==stable(r.conclusion))return err("FORGED_TRACE","Claimed conclusion differs from replayed derivation.");
 return Object.assign({},r,{traceValidated:true,diagnosisEligible:true});
}
const api=Object.freeze({SYSTEMS,AXIOMS,T,F,termSort,validFormula,verify,verifyWorkingTrace});
if(typeof module!=="undefined"&&module.exports)module.exports=api;root.ULTRON_PROOF_KERNEL=api;
})(typeof globalThis!=="undefined"?globalThis:this);
