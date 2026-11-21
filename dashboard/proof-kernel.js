(function (root) {
"use strict";
function deepFreeze(value){if(value&&typeof value==="object"&&!Object.isFrozen(value)){Object.keys(value).forEach(key=>deepFreeze(value[key]));Object.freeze(value);}return value;}
const SYSTEMS=deepFreeze({
 PEANO_N:{label:"Peano arithmetic",sorts:["Nat"],enabledAxioms:["PEANO-02","PEANO-03"],enabledAxiomSchemas:["PEANO-04"]},
 REAL_FIELD:{label:"Field theory",sorts:["Field"],enabledAxioms:["FIELD-01","FIELD-02","FIELD-03","FIELD-04","FIELD-05","FIELD-06","FIELD-07","FIELD-08","FIELD-09"],enabledAxiomSchemas:[]},
 ORDERED_FIELD:{label:"Ordered-field theory",sorts:["Field"],enabledAxioms:["FIELD-01","FIELD-02","FIELD-03","FIELD-04","FIELD-05","FIELD-06","FIELD-07","FIELD-08","FIELD-09"].concat(["ORDER-01","ORDER-02","ORDER-03","ORDER-04"]),enabledAxiomSchemas:[]},
 COMPLETE_REAL:{label:"Complete real field",sorts:["Field","RealSet"],enabledAxioms:["FIELD-01","FIELD-02","FIELD-03","FIELD-04","FIELD-05","FIELD-06","FIELD-07","FIELD-08","FIELD-09"].concat(["ORDER-01","ORDER-02","ORDER-03","ORDER-04","COMPLETE-01"]),enabledAxiomSchemas:[]},
 EUCLID_GEOMETRY:{label:"Euclidean geometry",sorts:["Point","Line","Circle","Angle"],enabledAxioms:["EUCLID-01","EUCLID-02","EUCLID-03","EUCLID-04","EUCLID-05"],enabledAxiomSchemas:[]},
 KOLMOGOROV:{label:"Kolmogorov probability",sorts:["Event","Real","EventSequence"],enabledAxioms:["PROB-01","PROB-02","PROB-03"],enabledAxiomSchemas:[]},
 ZFC:{label:"Zermelo–Fraenkel set theory with Choice",sorts:["Set"],enabledAxioms:["ZFC-01","ZFC-02","ZFC-03","ZFC-04","ZFC-05","ZFC-06","ZFC-09","ZFC-10"],enabledAxiomSchemas:["ZFC-07","ZFC-08"]}
});
const T=Object.freeze({
 variable:(name,sort)=>({kind:"var",name,sort}), numeral:value=>({kind:"nat",value}),
 succ:value=>({kind:"succ",value}), add:(left,right)=>({kind:"add",left,right}),
 multiply:(left,right)=>({kind:"mul",left,right}),
 rational:(numerator,denominator)=>({kind:"rational",numerator,denominator}),
 point:name=>({kind:"point",name}), line:name=>({kind:"line",name}), event:name=>({kind:"event",name}), set:name=>({kind:"set",name}),
 real:(numerator,denominator)=>({kind:"real",numerator,denominator}),
 sampleSpace:()=>({kind:"sampleSpace"}), measure:event=>({kind:"measure",event}), countableUnion:sequence=>({kind:"countableUnion",sequence}), countableSum:sequence=>({kind:"countableSum",sequence})
});
const F=Object.freeze({
 eq:(left,right)=>({kind:"eq",left,right}), lt:(left,right)=>({kind:"lt",left,right}), le:(left,right)=>({kind:"le",left,right}),
 and:(left,right)=>({kind:"and",left,right}), implies:(left,right)=>({kind:"implies",left,right}),
 forall:(name,sort,body)=>({kind:"forall",name,sort,body}), exists:(name,sort,body)=>({kind:"exists",name,sort,body}), not:formula=>({kind:"not",formula}),
 member:(term,set)=>({kind:"member",term,set}), incident:(point,line)=>({kind:"incident",point,line}), between:(first,middle,last)=>({kind:"between",first,middle,last}), circleCenter:(circle,center)=>({kind:"circleCenter",circle,center}), onCircle:(point,circle)=>({kind:"onCircle",point,circle}), rightAngle:angle=>({kind:"rightAngle",angle}), angleEqual:(left,right)=>({kind:"angleEqual",left,right}), sameSideInteriorAngles:(firstAngle,secondAngle,firstLine,secondLine,transversal)=>({kind:"sameSideInteriorAngles",firstAngle,secondAngle,firstLine,secondLine,transversal}), angleSumLessThanTwoRightAngles:(firstAngle,secondAngle)=>({kind:"angleSumLessThanTwoRightAngles",firstAngle,secondAngle}), linesMeetOnSameSide:(firstLine,secondLine,transversal)=>({kind:"linesMeetOnSameSide",firstLine,secondLine,transversal}), pairwiseDisjoint:sequence=>({kind:"pairwiseDisjoint",sequence}), familyOfNonemptySets:(family,indexSet)=>familyOfNonemptySetsFormula(family,indexSet), choiceFunction:(choice,indexSet,family)=>choiceFunctionFormula(choice,indexSet,family), predicate:(name,args)=>({kind:"predicate",name,args:args||[]})
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
  case "separation":return exactKeys(step,base.concat(["schemaId","sourceSet","predicate","predicateVariable","elementVariable","subsetVariable"]))&&typeof step.schemaId==="string"&&isObj(step.sourceSet)&&isObj(step.predicate)&&["predicateVariable","elementVariable","subsetVariable"].every(k=>typeof step[k]==="string"&&step[k].length>0);
  case "replacement":return exactKeys(step,base.concat(["schemaId","sourceSet","predicate","inputVariable","outputVariable","uniquenessVariable","imageElementVariable","imageSetVariable"]))&&typeof step.schemaId==="string"&&isObj(step.sourceSet)&&isObj(step.predicate)&&["inputVariable","outputVariable","uniquenessVariable","imageElementVariable","imageSetVariable"].every(k=>typeof step[k]==="string"&&step[k].length>0);
  default:return false;
 }
}
function termSort(t,bound={}) {
 if(!isObj(t))return null;
 switch(t.kind){
 case "var":{if(!exactKeys(t,["kind","name","sort"])||typeof t.name!=="string"||!t.name||typeof t.sort!=="string"||!t.sort)return null;const isBound=Object.prototype.hasOwnProperty.call(bound,t.name);return !isBound||bound[t.name]===t.sort?(isBound?bound[t.name]:t.sort):null;}
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
 case "countableUnion":return exactKeys(t,["kind","sequence"])&&termSort(t.sequence,bound)==="EventSequence"?"Event":null;
 case "countableSum":return exactKeys(t,["kind","sequence"])&&termSort(t.sequence,bound)==="EventSequence"?"Real":null;
 default:return null;
 }
}
function validFormula(f,bound={},allowedSorts=null) {
 if(!isObj(f))return false;
 switch(f.kind){
 case "eq":{if(!exactKeys(f,["kind","left","right"]))return false;const sort=termSort(f.left,bound);return !!sort&&sort===termSort(f.right,bound)&&(!allowedSorts||allowedSorts.has(sort));}
 case "lt":{if(!exactKeys(f,["kind","left","right"]))return false;const sort=termSort(f.left,bound);return ["Nat","Field","Real"].includes(sort)&&sort===termSort(f.right,bound)&&(!allowedSorts||allowedSorts.has(sort));}
 case "le":{if(!exactKeys(f,["kind","left","right"]))return false;const sort=termSort(f.left,bound);return ["Nat","Field","Real"].includes(sort)&&sort===termSort(f.right,bound)&&(!allowedSorts||allowedSorts.has(sort));}
 case "and":case "implies":return exactKeys(f,["kind","left","right"])&&validFormula(f.left,bound,allowedSorts)&&validFormula(f.right,bound,allowedSorts);
 case "not":return exactKeys(f,["kind","formula"])&&validFormula(f.formula,bound,allowedSorts);
 case "forall":case "exists":{if(!exactKeys(f,["kind","name","sort","body"])||typeof f.name!=="string"||!f.name||!["Nat","Field","Real","Point","Line","Circle","Angle","Event","EventSequence","Probability","Set","RealSet"].includes(f.sort)||(allowedSorts&&!allowedSorts.has(f.sort)))return false;const nextBound=Object.assign(Object.create(null),bound,{[f.name]:f.sort});return validFormula(f.body,nextBound,allowedSorts);}
 case "member":{if(!exactKeys(f,["kind","term","set"]))return false;const a=termSort(f.term,bound),b=termSort(f.set,bound);const compatible=b==="Set"||(b==="RealSet"&&a==="Field");return !!a&&compatible&&(!allowedSorts||(allowedSorts.has(a)&&allowedSorts.has(b)));}
 case "incident":return exactKeys(f,["kind","point","line"])&&termSort(f.point,bound)==="Point"&&termSort(f.line,bound)==="Line"&&(!allowedSorts||(allowedSorts.has("Point")&&allowedSorts.has("Line")));
 case "between":return exactKeys(f,["kind","first","middle","last"])&&termSort(f.first,bound)==="Point"&&termSort(f.middle,bound)==="Point"&&termSort(f.last,bound)==="Point"&&(!allowedSorts||allowedSorts.has("Point"));
 case "circleCenter":return exactKeys(f,["kind","circle","center"])&&termSort(f.circle,bound)==="Circle"&&termSort(f.center,bound)==="Point"&&(!allowedSorts||(allowedSorts.has("Circle")&&allowedSorts.has("Point")));
 case "onCircle":return exactKeys(f,["kind","point","circle"])&&termSort(f.point,bound)==="Point"&&termSort(f.circle,bound)==="Circle"&&(!allowedSorts||(allowedSorts.has("Circle")&&allowedSorts.has("Point")));
 case "rightAngle":return exactKeys(f,["kind","angle"])&&termSort(f.angle,bound)==="Angle"&&(!allowedSorts||allowedSorts.has("Angle"));
 case "angleEqual":return exactKeys(f,["kind","left","right"])&&termSort(f.left,bound)==="Angle"&&termSort(f.right,bound)==="Angle"&&(!allowedSorts||allowedSorts.has("Angle"));
 case "sameSideInteriorAngles":return exactKeys(f,["kind","firstAngle","secondAngle","firstLine","secondLine","transversal"])&&termSort(f.firstAngle,bound)==="Angle"&&termSort(f.secondAngle,bound)==="Angle"&&termSort(f.firstLine,bound)==="Line"&&termSort(f.secondLine,bound)==="Line"&&termSort(f.transversal,bound)==="Line"&&(!allowedSorts||(allowedSorts.has("Angle")&&allowedSorts.has("Line")));
 case "angleSumLessThanTwoRightAngles":return exactKeys(f,["kind","firstAngle","secondAngle"])&&termSort(f.firstAngle,bound)==="Angle"&&termSort(f.secondAngle,bound)==="Angle"&&(!allowedSorts||allowedSorts.has("Angle"));
 case "linesMeetOnSameSide":return exactKeys(f,["kind","firstLine","secondLine","transversal"])&&termSort(f.firstLine,bound)==="Line"&&termSort(f.secondLine,bound)==="Line"&&termSort(f.transversal,bound)==="Line"&&(!allowedSorts||allowedSorts.has("Line"));
 case "pairwiseDisjoint":return exactKeys(f,["kind","sequence"])&&termSort(f.sequence,bound)==="EventSequence"&&(!allowedSorts||allowedSorts.has("EventSequence"));

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
function boundVariableNames(node,out=new Set()){
 if(!isObj(node))return out;
 if(node.kind==="forall"||node.kind==="exists")out.add(node.name);
 for(const value of Object.values(node)){if(Array.isArray(value))value.forEach(x=>boundVariableNames(x,out));else if(isObj(value))boundVariableNames(value,out);}
 return out;
}
function separationSchemaFormula(step,allowedSorts){
 const {sourceSet,predicate,predicateVariable,elementVariable,subsetVariable}=step;
 if(!isObj(sourceSet)||sourceSet.kind!=="var"||termSort(sourceSet)!=="Set"||!validFormula(predicate,{},allowedSorts))return null;
 if(![predicateVariable,elementVariable,subsetVariable].every(x=>typeof x==="string"&&x.length>0))return null;
 if(predicateVariable===sourceSet.name)return null;
 if(new Set([elementVariable,subsetVariable]).size!==2)return null;
 if([elementVariable,subsetVariable].includes(sourceSet.name))return null;
 const free=freeVariableNames(predicate),all=allVariableNames(predicate),bound=boundVariableNames(predicate);
 if(!free.has(predicateVariable)||bound.has(predicateVariable)||all.has(elementVariable)||all.has(subsetVariable))return null;
 const instance=substitute(predicate,predicateVariable,T.variable(elementVariable,"Set"));
 if(!instance||!validFormula(instance,{},allowedSorts))return null;
 const element=T.variable(elementVariable,"Set"),subset=T.variable(subsetVariable,"Set");
 return F.exists(subsetVariable,"Set",F.forall(elementVariable,"Set",equivalent(
  F.member(element,subset),
  F.and(F.member(element,sourceSet),instance)
 )));
}
function replacementSchemaFormula(step,allowedSorts){
 const {sourceSet,predicate,inputVariable,outputVariable,uniquenessVariable,imageElementVariable,imageSetVariable}=step;
 if(!isObj(sourceSet)||sourceSet.kind!=="var"||termSort(sourceSet)!=="Set"||!validFormula(predicate,{},allowedSorts))return null;
 const names=[inputVariable,outputVariable,uniquenessVariable,imageElementVariable,imageSetVariable];
 if(!names.every(x=>typeof x==="string"&&x.length>0)||new Set(names).size!==names.length)return null;
 if([inputVariable,outputVariable,uniquenessVariable,imageElementVariable,imageSetVariable].includes(sourceSet.name))return null;
 const free=freeVariableNames(predicate),all=allVariableNames(predicate),bound=boundVariableNames(predicate);
 if(!free.has(inputVariable)||!free.has(outputVariable)||bound.has(inputVariable)||bound.has(outputVariable))return null;
 if([uniquenessVariable,imageElementVariable,imageSetVariable].some(x=>all.has(x)))return null;
 const x=T.variable(inputVariable,"Set"),y=T.variable(outputVariable,"Set");
 const z=T.variable(uniquenessVariable,"Set"),w=T.variable(imageElementVariable,"Set"),image=T.variable(imageSetVariable,"Set");
 const phiXz=substitute(predicate,outputVariable,z),phiXw=substitute(predicate,outputVariable,w);
 if(!phiXz||!phiXw||!validFormula(phiXz,{},allowedSorts)||!validFormula(phiXw,{},allowedSorts))return null;
 const uniqueOutput=F.exists(outputVariable,"Set",F.and(
  predicate,
  F.forall(uniquenessVariable,"Set",F.implies(phiXz,F.eq(z,y)))
 ));
 const functionalOnSource=F.forall(inputVariable,"Set",F.implies(F.member(x,sourceSet),uniqueOutput));
 const imageMembership=F.exists(inputVariable,"Set",F.and(F.member(x,sourceSet),phiXw));
 const imageExists=F.exists(imageSetVariable,"Set",F.forall(imageElementVariable,"Set",equivalent(F.member(w,image),imageMembership)));
 return F.implies(functionalOnSource,imageExists);
}

const equivalent=(a,b)=>F.and(F.implies(a,b),F.implies(b,a));
const disjunction=(a,b)=>F.not(F.and(F.not(a),F.not(b)));

function orderedPairFormula(pair,first,second){
 const singleton=T.variable("__op_singleton","Set"),unordered=T.variable("__op_unordered","Set");
 const z=T.variable("__op_z","Set"),w=T.variable("__op_w","Set"),element=T.variable("__op_element","Set");
 const singletonDef=F.forall("__op_z","Set",equivalent(F.member(z,singleton),F.eq(z,first)));
 const unorderedDef=F.forall("__op_w","Set",equivalent(F.member(w,unordered),disjunction(F.eq(w,first),F.eq(w,second))));
 const outerDef=F.forall("__op_element","Set",equivalent(F.member(element,pair),disjunction(F.eq(element,singleton),F.eq(element,unordered))));
 return F.exists("__op_singleton","Set",F.exists("__op_unordered","Set",F.and(singletonDef,F.and(unorderedDef,outerDef))));
}
function functionGraphFormula(graph,indexSet){
 const p=T.variable("__fg_pair","Set"),x=T.variable("__fg_first","Set"),y=T.variable("__fg_value","Set");
 const allMembersArePairs=F.forall("__fg_pair","Set",F.implies(
  F.member(p,graph),F.exists("__fg_first","Set",F.exists("__fg_value","Set",orderedPairFormula(p,x,y)))
 ));
 const i=T.variable("__fg_index","Set"),v=T.variable("__fg_result","Set"),q=T.variable("__fg_other_pair","Set"),z=T.variable("__fg_other_value","Set");
 const eachIndexHasUniqueValue=F.forall("__fg_index","Set",F.implies(
  F.member(i,indexSet),
  F.exists("__fg_result","Set",F.and(
   F.exists("__fg_pair","Set",F.and(F.member(p,graph),orderedPairFormula(p,i,v))),
   F.forall("__fg_other_value","Set",F.implies(
    F.exists("__fg_other_pair","Set",F.and(F.member(q,graph),orderedPairFormula(q,i,z))),
    F.eq(z,v)
   ))
  ))
 ));
 const index=T.variable("__fg_domain_index","Set"),value=T.variable("__fg_domain_value","Set");
 const noPairsOutsideDomain=F.forall("__fg_pair","Set",F.implies(
  F.member(p,graph),
  F.exists("__fg_domain_index","Set",F.and(
   F.member(index,indexSet),
   F.exists("__fg_domain_value","Set",orderedPairFormula(p,index,value))
  ))
 ));
 return F.and(allMembersArePairs,F.and(eachIndexHasUniqueValue,noPairsOutsideDomain));
}
function familyOfNonemptySetsFormula(family,indexSet){
 const i=T.variable("__fam_index","Set"),set=T.variable("__fam_set","Set"),p=T.variable("__fam_pair","Set"),x=T.variable("__fam_element","Set");
 const familyValue=F.exists("__fam_pair","Set",F.and(F.member(p,family),orderedPairFormula(p,i,set)));
 const nonempty=F.exists("__fam_element","Set",F.member(x,set));
 return F.and(functionGraphFormula(family,indexSet),F.forall("__fam_index","Set",F.implies(
  F.member(i,indexSet),F.exists("__fam_set","Set",F.and(familyValue,nonempty))
 )));
}
function choiceFunctionFormula(choice,indexSet,family){
 const i=T.variable("__choice_index","Set"),set=T.variable("__choice_set","Set"),value=T.variable("__choice_value","Set");
 const p=T.variable("__choice_family_pair","Set"),q=T.variable("__choice_choice_pair","Set");
 const familyValue=F.exists("__choice_family_pair","Set",F.and(F.member(p,family),orderedPairFormula(p,i,set)));
 const chosenValue=F.exists("__choice_choice_pair","Set",F.and(F.member(q,choice),orderedPairFormula(q,i,value)));
 return F.and(functionGraphFormula(choice,indexSet),F.forall("__choice_index","Set",F.forall("__choice_set","Set",F.forall("__choice_value","Set",F.implies(
  F.and(familyValue,chosenValue),F.member(value,set)
 )))));
}

const pointVar=name=>T.variable(name,"Point");
const lineVar=name=>T.variable(name,"Line");
const and4=(a,b,c,d)=>F.and(a,F.and(b,F.and(c,d)));
const angleVar=name=>T.variable(name,"Angle");
const sequenceVar=name=>T.variable(name,"EventSequence");
const PROB_COUNTABLE_ADDITIVITY=F.forall("s","EventSequence",F.implies(
 F.pairwiseDisjoint(sequenceVar("s")),
 F.eq(T.measure(T.countableUnion(sequenceVar("s"))),T.countableSum(sequenceVar("s")))
));
const EUCLID_PARALLEL_POSTULATE=F.forall("l1","Line",
 F.forall("l2","Line",
  F.forall("t","Line",
   F.forall("a","Angle",
    F.forall("b","Angle",
     F.implies(
      F.and(
       F.sameSideInteriorAngles(angleVar("a"),angleVar("b"),lineVar("l1"),lineVar("l2"),lineVar("t")),
       F.angleSumLessThanTwoRightAngles(angleVar("a"),angleVar("b"))
      ),
      F.linesMeetOnSameSide(lineVar("l1"),lineVar("l2"),lineVar("t"))
     )
    )
   )
  )
 )
);
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
const fieldVar=name=>T.variable(name,"Field");
const orderA=fieldVar("a"),orderB=fieldVar("b"),zeroField=T.rational(0,1);
const orderAB=F.lt(orderA,orderB),equalAB=F.eq(orderA,orderB),orderBA=F.lt(orderB,orderA);
const ORDER_TRICHOTOMY=F.forall("a","Field",F.forall("b","Field",F.and(
 F.not(F.and(orderAB,equalAB)),
 F.and(
  F.not(F.and(orderAB,orderBA)),
  F.and(
   F.not(F.and(equalAB,orderBA)),
   F.not(F.and(F.not(orderAB),F.and(F.not(equalAB),F.not(orderBA))))
  )
 )
)));
const COMPLETE_LEAST_UPPER_BOUND=F.forall("A","RealSet",F.implies(
 F.and(
  F.exists("n","Field",F.member(fieldVar("n"),T.variable("A","RealSet"))),
  F.exists("b","Field",F.forall("bx","Field",F.implies(
   F.member(fieldVar("bx"),T.variable("A","RealSet")),F.not(F.lt(fieldVar("b"),fieldVar("bx")))
  )))
 ),
 F.exists("s","Field",F.and(
  F.forall("sx","Field",F.implies(
   F.member(fieldVar("sx"),T.variable("A","RealSet")),F.not(F.lt(fieldVar("s"),fieldVar("sx")))
  )),
  F.forall("u","Field",F.implies(
   F.forall("ux","Field",F.implies(
    F.member(fieldVar("ux"),T.variable("A","RealSet")),F.not(F.lt(fieldVar("u"),fieldVar("ux")))
   )),
   F.not(F.lt(fieldVar("u"),fieldVar("s")))
  ))
 ))
));
const AXIOMS=deepFreeze({
 "PEANO-02":{system:"PEANO_N",formula:F.forall("n","Nat",F.not(F.eq(T.succ(T.variable("n","Nat")),T.numeral(0))))},
 "PEANO-03":{system:"PEANO_N",formula:F.forall("m","Nat",F.forall("n","Nat",F.implies(F.eq(T.succ(T.variable("m","Nat")),T.succ(T.variable("n","Nat"))),F.eq(T.variable("m","Nat"),T.variable("n","Nat")))))},
 "FIELD-01":{system:"REAL_FIELD",systems:["REAL_FIELD","ORDERED_FIELD","COMPLETE_REAL"],formula:F.forall("a","Field",F.forall("b","Field",F.eq(T.add(T.variable("a","Field"),T.variable("b","Field")),T.add(T.variable("b","Field"),T.variable("a","Field")))))},
 "FIELD-02":{system:"REAL_FIELD",systems:["REAL_FIELD","ORDERED_FIELD","COMPLETE_REAL"],formula:F.forall("a","Field",F.forall("b","Field",F.forall("c","Field",F.eq(T.add(T.add(T.variable("a","Field"),T.variable("b","Field")),T.variable("c","Field")),T.add(T.variable("a","Field"),T.add(T.variable("b","Field"),T.variable("c","Field")))))))},
 "FIELD-03":{system:"REAL_FIELD",systems:["REAL_FIELD","ORDERED_FIELD","COMPLETE_REAL"],formula:F.forall("a","Field",F.and(F.eq(T.add(T.variable("a","Field"),T.rational(0,1)),T.variable("a","Field")),F.eq(T.add(T.rational(0,1),T.variable("a","Field")),T.variable("a","Field"))))},
 "FIELD-04":{system:"REAL_FIELD",systems:["REAL_FIELD","ORDERED_FIELD","COMPLETE_REAL"],formula:F.forall("a","Field",F.exists("b","Field",F.eq(T.add(T.variable("a","Field"),T.variable("b","Field")),T.rational(0,1))))},
 "FIELD-05":{system:"REAL_FIELD",systems:["REAL_FIELD","ORDERED_FIELD","COMPLETE_REAL"],formula:F.forall("a","Field",F.forall("b","Field",F.eq(T.multiply(T.variable("a","Field"),T.variable("b","Field")),T.multiply(T.variable("b","Field"),T.variable("a","Field")))))},
 "FIELD-06":{system:"REAL_FIELD",systems:["REAL_FIELD","ORDERED_FIELD","COMPLETE_REAL"],formula:F.forall("a","Field",F.forall("b","Field",F.forall("c","Field",F.eq(T.multiply(T.multiply(T.variable("a","Field"),T.variable("b","Field")),T.variable("c","Field")),T.multiply(T.variable("a","Field"),T.multiply(T.variable("b","Field"),T.variable("c","Field")))))))},
 "FIELD-07":{system:"REAL_FIELD",systems:["REAL_FIELD","ORDERED_FIELD","COMPLETE_REAL"],formula:F.and(F.not(F.eq(T.rational(1,1),T.rational(0,1))),F.forall("a","Field",F.and(F.eq(T.multiply(T.variable("a","Field"),T.rational(1,1)),T.variable("a","Field")),F.eq(T.multiply(T.rational(1,1),T.variable("a","Field")),T.variable("a","Field")))))},
 "FIELD-08":{system:"REAL_FIELD",systems:["REAL_FIELD","ORDERED_FIELD","COMPLETE_REAL"],formula:F.forall("a","Field",F.implies(F.not(F.eq(T.variable("a","Field"),T.rational(0,1))),F.exists("b","Field",F.eq(T.multiply(T.variable("a","Field"),T.variable("b","Field")),T.rational(1,1)))))},
 "FIELD-09":{system:"REAL_FIELD",systems:["REAL_FIELD","ORDERED_FIELD","COMPLETE_REAL"],formula:F.forall("a","Field",F.forall("b","Field",F.forall("c","Field",F.eq(T.multiply(T.variable("a","Field"),T.add(T.variable("b","Field"),T.variable("c","Field"))),T.add(T.multiply(T.variable("a","Field"),T.variable("b","Field")),T.multiply(T.variable("a","Field"),T.variable("c","Field")))))))},
 "ORDER-01":{system:"ORDERED_FIELD",systems:["ORDERED_FIELD","COMPLETE_REAL"],formula:ORDER_TRICHOTOMY},
 "ORDER-02":{system:"ORDERED_FIELD",systems:["ORDERED_FIELD","COMPLETE_REAL"],formula:F.forall("a","Field",F.forall("b","Field",F.forall("c","Field",F.implies(F.and(F.lt(fieldVar("a"),fieldVar("b")),F.lt(fieldVar("b"),fieldVar("c"))),F.lt(fieldVar("a"),fieldVar("c"))))))},
 "ORDER-03":{system:"ORDERED_FIELD",systems:["ORDERED_FIELD","COMPLETE_REAL"],formula:F.forall("a","Field",F.forall("b","Field",F.forall("c","Field",F.implies(F.lt(fieldVar("a"),fieldVar("b")),F.lt(T.add(fieldVar("a"),fieldVar("c")),T.add(fieldVar("b"),fieldVar("c")))))))},
 "ORDER-04":{system:"ORDERED_FIELD",systems:["ORDERED_FIELD","COMPLETE_REAL"],formula:F.forall("a","Field",F.forall("b","Field",F.forall("c","Field",F.implies(F.and(F.lt(fieldVar("a"),fieldVar("b")),F.lt(zeroField,fieldVar("c"))),F.lt(T.multiply(fieldVar("a"),fieldVar("c")),T.multiply(fieldVar("b"),fieldVar("c")))))))},
 "COMPLETE-01":{system:"COMPLETE_REAL",formula:COMPLETE_LEAST_UPPER_BOUND},

 "EUCLID-01":{system:"EUCLID_GEOMETRY",formula:F.forall("A","Point",F.forall("B","Point",F.implies(F.not(F.eq(T.variable("A","Point"),T.variable("B","Point"))),F.exists("l","Line",F.and(F.incident(T.variable("A","Point"),T.variable("l","Line")),F.incident(T.variable("B","Point"),T.variable("l","Line")))))))},
 "EUCLID-02":{system:"EUCLID_GEOMETRY",formula:EUCLID_SEGMENT_EXTENSION},
 "EUCLID-03":{system:"EUCLID_GEOMETRY",formula:F.forall("O","Point",F.forall("A","Point",F.exists("c","Circle",F.and(
  F.circleCenter(T.variable("c","Circle"),T.variable("O","Point")),
  F.onCircle(T.variable("A","Point"),T.variable("c","Circle"))
 ))))},
 "EUCLID-04":{system:"EUCLID_GEOMETRY",formula:F.forall("A","Angle",F.forall("B","Angle",F.implies(
  F.and(F.rightAngle(T.variable("A","Angle")),F.rightAngle(T.variable("B","Angle"))),
  F.angleEqual(T.variable("A","Angle"),T.variable("B","Angle"))
 )))},
 "EUCLID-05":{system:"EUCLID_GEOMETRY",formula:EUCLID_PARALLEL_POSTULATE},
 "PROB-01":{system:"KOLMOGOROV",formula:F.forall("A","Event",F.le(T.real(0,1),T.measure(T.variable("A","Event"))))},
 "PROB-02":{system:"KOLMOGOROV",formula:F.eq(T.measure(T.sampleSpace()),T.real(1,1))},
 "PROB-03":{system:"KOLMOGOROV",formula:PROB_COUNTABLE_ADDITIVITY},
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
 ))},
 "ZFC-10":{system:"ZFC",formula:F.forall("I","Set",F.forall("A","Set",F.implies(
  F.familyOfNonemptySets(T.variable("A","Set"),T.variable("I","Set")),
  F.exists("f","Set",F.choiceFunction(T.variable("f","Set"),T.variable("I","Set"),T.variable("A","Set")))
 )))}
});
function axiomAvailable(axiom,system){return !!axiom&&(axiom.system===system||(Array.isArray(axiom.systems)&&axiom.systems.includes(system)));}
const AXIOM_SCHEMAS=deepFreeze({
 "PEANO-04":{system:"PEANO_N",rule:"induction",description:"From P(0) and ∀k(P(k)→P(S(k))), derive ∀n P(n)."},
 "ZFC-07":{system:"ZFC",rule:"separation",description:"For any formula φ(x), the elements of a set X satisfying φ form a set."},
 "ZFC-08":{system:"ZFC",rule:"replacement",description:"The image of a set under a formula defining a unique output for each input is a set."}
});
const err=(code,message,stepId)=>({valid:false,code,message,stepId:stepId||null});
function verify(p){
 if(!exactKeys(p,["version","system","assumptions","steps","conclusion"])||p.version!==1||!Object.hasOwn(SYSTEMS,p.system)||!denseArray(p.assumptions)||!denseArray(p.steps)||!p.steps.length||typeof p.conclusion!=="string")return err("MALFORMED_PROOF","Malformed proof envelope or unknown system.");
 const sys=SYSTEMS[p.system],allowedSorts=new Set(sys.sorts),available=new Map(),used=[],usedSchemas=[];
 for(const a of p.assumptions){if(!exactKeys(a,["id","formula"])||typeof a.id!=="string"||available.has(a.id)||!validFormula(a.formula,{},allowedSorts))return err("INVALID_ASSUMPTION","Assumptions need unique IDs and well-typed formulas.");available.set(a.id,{formula:a.formula,origin:"assumption",dependencies:new Set([a.id])});}
 for(const s of p.steps){
  if(!isObj(s)||typeof s.id!=="string"||available.has(s.id))return err("INVALID_STEP","Each step needs a unique ID.",s&&s.id);
  if(!validStepShape(s)){if(typeof s.rule==="string"&&!["assumption","axiom","eq_refl","eq_symm","eq_trans","and_intro","and_left","and_right","imp_elim","imp_intro","forall_elim","forall_intro","exists_intro","exists_elim","induction","separation","replacement"].includes(s.rule))return err("UNKNOWN_RULE","Rule is not part of the audited kernel.",s.id);return err("INVALID_STEP","Step contains missing, unexpected, or malformed fields.",s.id);}
  if(s.rule==="axiom"){const registered=AXIOMS[s.axiomId];if(!axiomAvailable(registered,p.system)||!sys.enabledAxioms.includes(s.axiomId))return err("AXIOM_NOT_AVAILABLE","Axiom is unknown, not formalized, or unavailable in this system.",s.id);}
  if(s.rule==="induction"){const schema=AXIOM_SCHEMAS[s.axiomId];if(!schema||schema.system!==p.system||!sys.enabledAxiomSchemas.includes(s.axiomId))return err("AXIOM_SCHEMA_NOT_AVAILABLE","Axiom schema is unknown or unavailable in this formal system.",s.id);}
  if(s.rule==="separation"||s.rule==="replacement"){const schema=AXIOM_SCHEMAS[s.schemaId];if(!schema||schema.rule!==s.rule||schema.system!==p.system||!sys.enabledAxiomSchemas.includes(s.schemaId))return err("AXIOM_SCHEMA_NOT_AVAILABLE","Axiom schema is unknown or unavailable in this formal system.",s.id);}
  if(!validFormula(s.formula,{},allowedSorts))return err("INVALID_STEP","Proof step formula is not well-typed in its declared formal system.",s.id);
  const ids=s.premises||[];if(!Array.isArray(ids))return err("INVALID_PREMISES","Premises must be an array.",s.id);
  const refs=ids.map(id=>available.get(id));if(refs.some(x=>!x))return err("UNKNOWN_PREMISE","Missing or forward proof reference.",s.id);
  let e=null;
  switch(s.rule){
   case "assumption":{const a=p.assumptions.find(x=>x.id===s.assumption);if(a&&!ids.length)e=a.formula;break;}
   case "axiom":{const a=AXIOMS[s.axiomId];if(ids.length)return err("RULE_MISMATCH","Axiom steps cannot have premises.",s.id);if(!axiomAvailable(a,p.system)||!sys.enabledAxioms.includes(s.axiomId))return err("AXIOM_NOT_AVAILABLE","Axiom is unknown, not formalized, or unavailable in this system.",s.id);e=a.formula;used.push(s.axiomId);break;}
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
   case "separation":e=separationSchemaFormula(s,allowedSorts);break;
   case "replacement":e=replacementSchemaFormula(s,allowedSorts);break;
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
  if(s.rule==="induction")usedSchemas.push(s.axiomId);else if(s.rule==="separation"||s.rule==="replacement")usedSchemas.push(s.schemaId);
  const dependencies=new Set();
  if(s.rule==="assumption")dependencies.add(s.assumption);
  else refs.forEach(ref=>ref.dependencies.forEach(id=>dependencies.add(id)));
  if(s.rule==="imp_intro"||s.rule==="exists_elim")dependencies.delete(s.discharge);
  available.set(s.id,{formula:s.formula,origin:s.rule,dependencies});
 }
 const last=available.get(p.conclusion);if(!last||!p.steps.some(x=>x.id===p.conclusion))return err("MISSING_CONCLUSION","Conclusion must reference a derived step.");
 return {valid:true,system:p.system,conclusion:clone(last.formula),openAssumptions:[...last.dependencies].sort(),usedAxioms:[...new Set(used)],usedAxiomSchemas:[...new Set(usedSchemas)],checkedSteps:p.steps.length,trace:p.steps.map(x=>({id:x.id,rule:x.rule,formula:clone(x.formula),premises:(x.premises||[]).slice(),axiomId:x.axiomId||null,schemaId:x.schemaId||null,sourceSet:x.sourceSet?clone(x.sourceSet):null,predicate:x.predicate?clone(x.predicate):null,predicateVariable:x.predicateVariable||null,elementVariable:x.elementVariable||null,subsetVariable:x.subsetVariable||null,inputVariable:x.inputVariable||null,outputVariable:x.outputVariable||null,uniquenessVariable:x.uniquenessVariable||null,imageElementVariable:x.imageElementVariable||null,imageSetVariable:x.imageSetVariable||null,term:x.term?clone(x.term):null,variable:x.variable||null,discharge:x.discharge||null}))};
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
