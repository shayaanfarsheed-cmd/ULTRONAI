(function (root) {
  "use strict";
  const MAX_QUESTION_LENGTH = 1000;
  const TOPICS = {
    whole_number_arithmetic: {label:"Whole-number arithmetic",concept:"Whole-number arithmetic",rule:"Addition, subtraction, multiplication and exact division operate on whole numbers.",method:"Read the operator, calculate with integer arithmetic, then independently check the result."},
    fractions: {label:"Fractions",concept:"Fractions",rule:"For addition/subtraction use a common denominator; for multiplication multiply across; for division multiply by the reciprocal.",method:"Parse both fractions, calculate exactly, and reduce to lowest terms."},
    decimals: {label:"Decimals",concept:"Decimals",rule:"Align decimal places before addition or subtraction.",method:"Convert decimal strings to exact scaled integers, calculate, then format without trailing zeros."},
    percentages: {label:"Percentages",concept:"Percentages",rule:"p percent of n = (p / 100) × n.",method:"Multiply the percentage by the amount, divide by 100, and reduce the fraction."},
    ratios_and_proportions: {label:"Ratios and proportions",concept:"Ratios",rule:"Equivalent ratios are formed by dividing both terms by the same greatest common divisor.",method:"Find the greatest common divisor and divide both ratio terms."},
    integers: {label:"Integers",concept:"Positive and negative integers",rule:"Signed addition and subtraction follow number-line rules.",method:"Evaluate the signed expression and retain the sign of the result."},
    order_of_operations: {label:"Order of operations",concept:"Order of operations",rule:"Multiplication is performed before addition; equal-priority operations are evaluated left to right.",method:"Evaluate multiplication first, then the remaining addition."},
    pre_algebra: {label:"Pre-algebra",concept:"One-step equations",rule:"Keep an equation balanced by applying the inverse operation to both sides.",method:"Undo the addition or subtraction attached to x to isolate x."},
    linear_equations: {label:"Linear equations",concept:"Linear equations",rule:"Apply inverse operations to both sides; undo addition before multiplication.",method:"Subtract the constant, then divide by the coefficient of x."},
    inequalities: {label:"Inequalities",concept:"Linear inequalities",rule:"Solve like an equation. Dividing by a negative reverses the inequality sign.",method:"Find the boundary and preserve direction for the positive coefficients supported here."},
    exponents_and_roots: {label:"Exponents and roots",concept:"Exponents and square roots",rule:"a² means a × a; √n is the non-negative value whose square is n.",method:"Use integer multiplication or confirm an exact integer square root."},
    basic_geometry: {label:"Basic geometry",concept:"Rectangle geometry",rule:"Area = length × width; perimeter = 2 × (length + width).",method:"Identify area or perimeter, then substitute the dimensions."},
    basic_statistics: {label:"Basic statistics",concept:"Mean (average)",rule:"Mean = sum of all values divided by the number of values.",method:"Add the values, divide by the count, and simplify exactly."},
    basic_probability: {label:"Basic probability",concept:"Basic probability",rule:"Probability = favourable outcomes / total equally likely outcomes.",method:"Form the favourable-to-total fraction and reduce it."}
    ,median_and_range: {label:"Median and range",concept:"Median and range",rule:"Sort the values; median is the middle and range is maximum minus minimum.",method:"Sort five values, select the third, subtract the smallest from the largest."}
    ,simple_interest: {label:"Simple interest",concept:"Simple interest",rule:"I = principal × rate × time / 100.",method:"Multiply principal, percentage rate and years, then divide by 100."}
    ,unit_conversion: {label:"Metric unit conversion",concept:"Metric unit conversion",rule:"Use exact metric scale factors.",method:"Multiply by the supported conversion factor."}
    ,pythagorean_theorem: {label:"Pythagorean theorem",concept:"Pythagorean theorem",rule:"For a right triangle c² = a² + b².",method:"Add squared legs and take the exact integer square root."}
  };
  const TOPIC_KEYS = Object.keys(TOPICS);
  const fail = message => { throw new Error(message); };
  function gcd(a,b) { a=a<0n?-a:a; b=b<0n?-b:b; while(b){const t=a%b;a=b;b=t;} return a||1n; }
  function fraction(n,d) { if(d===0n) fail("Division by zero"); if(d<0n){n=-n;d=-d;} const g=gcd(n,d); return {n:n/g,d:d/g}; }
  function ftext(f) { return f.d===1n?String(f.n):String(f.n)+"/"+String(f.d); }
  function parseFraction(s) { const m=/^(-?\d+)(?:\/(\d+))?$/.exec(s); if(!m) fail("Invalid fraction"); return fraction(BigInt(m[1]),BigInt(m[2]||"1")); }
  function add(a,b) { return fraction(a.n*b.d+b.n*a.d,a.d*b.d); }
  function sub(a,b) { return fraction(a.n*b.d-b.n*a.d,a.d*b.d); }
  function mul(a,b) { return fraction(a.n*b.n,a.d*b.d); }
  function div(a,b) { return fraction(a.n*b.d,a.d*b.n); }
  function decimalValue(s) { if(!/^-?\d+(?:\.\d+)?$/.test(s)) fail("Invalid decimal"); const neg=s[0]==="-"; const raw=neg?s.slice(1):s; const p=raw.split("."); const scale=10n**BigInt((p[1]||"").length); const n=BigInt(p[0]+(p[1]||"")); return fraction(neg?-n:n,scale); }
  function decimalText(f) { let d=f.d, twos=0, fives=0; while(d%2n===0n){d/=2n;twos++;} while(d%5n===0n){d/=5n;fives++;} if(d!==1n)return ftext(f); const scale=Math.max(twos,fives); if(scale===0)return String(f.n); const scaled=f.n*(2n**BigInt(scale-twos))*(5n**BigInt(scale-fives)); const negative=scaled<0n?"-":""; const digits=String(scaled<0n?-scaled:scaled).padStart(scale+1,"0"); return (negative+digits.slice(0,-scale)+"."+digits.slice(-scale)).replace(/\.?0+$/,""); }
  function solve(topic, question) {
    if(!TOPICS[topic]) fail("Choose a supported topic.");
    if(typeof question!=="string" || !question.trim() || question.length>MAX_QUESTION_LENGTH) fail("Enter a question of 1–1,000 characters.");
    const q=question.trim(); let answer, steps;
    let m;
    if(topic==="whole_number_arithmetic" || topic==="integers") {
      m=/^Calculate: (-?\d+) ([+*/-]) (-?\d+)$/.exec(q); if(!m) fail("Use: Calculate: 12 + 5");
      const a=BigInt(m[1]), b=BigInt(m[3]), op=m[2]; let v;
      if(op==="+")v=a+b; else if(op==="-")v=a-b; else if(op==="*")v=a*b; else {if(b===0n||a%b!==0n)fail("Only exact integer division is supported.");v=a/b;}
      answer=String(v); steps=topic==="integers"?["Apply the signed-integer operation.",m[1]+" "+op+" "+m[3]+" = "+answer+"."]: [m[1]+" "+op+" "+m[3]+" = "+answer+"."];
    } else if(topic==="fractions") {
      m=/^Calculate: \((\d+\/\d+)\) ([+*/-]) \((\d+\/\d+)\)$/.exec(q); if(!m)fail("Use: Calculate: (1/2) + (1/4)");
      const a=parseFraction(m[1]),b=parseFraction(m[3]),op=m[2]; let r;
      if(op==="+")r=add(a,b); else if(op==="-")r=sub(a,b); else if(op==="*")r=mul(a,b); else r=div(a,b);
      answer=ftext(r); steps=op==="+"||op==="-"?["Find a common denominator.", "Combine the numerators and simplify to "+answer+"."]:op==="*"?["Multiply the numerators and denominators.", "Reduce the result to "+answer+"."]:["Multiply by the reciprocal of the second fraction.","Simplify to "+answer+"."];
    } else if(topic==="decimals") {
      m=/^Calculate: (-?\d+(?:\.\d+)?) ([+-]) (-?\d+(?:\.\d+)?)$/.exec(q); if(!m)fail("Use: Calculate: 2.5 + 1.25");
      const a=decimalValue(m[1]),b=decimalValue(m[3]),r=m[2]==="+"?add(a,b):sub(a,b);
      answer=decimalText(r); steps=["Align the decimal places.","Calculate exactly: "+m[1]+" "+m[2]+" "+m[3]+" = "+answer+"."];
    } else if(topic==="percentages") {
      m=/^Percentage: (\d+)% of (\d+)$/.exec(q); if(!m)fail("Use: Percentage: 25% of 80");
      answer=ftext(fraction(BigInt(m[1])*BigInt(m[2]),100n)); steps=["Convert the percentage to a fraction over 100.","Multiply by the amount to get "+answer+"."];
    } else if(topic==="ratios_and_proportions") {
      m=/^Simplify ratio: (\d+):(\d+)$/.exec(q); if(!m)fail("Use: Simplify ratio: 12:8");
      const a=BigInt(m[1]),b=BigInt(m[2]); if(a===0n&&b===0n)fail("The ratio 0:0 is undefined."); const g=gcd(a,b); answer=String(a/g)+":"+String(b/g); steps=["Find the greatest common divisor: "+g+".","Divide both parts by "+g+" to get "+answer+"."];
    } else if(topic==="order_of_operations") {
      m=/^Calculate: (\d+) \+ (\d+) \* (\d+)$/.exec(q); if(!m)fail("Use: Calculate: 3 + 4 * 5");
      const [a,b,c]=m.slice(1).map(BigInt), p=b*c; answer=String(a+p); steps=["Multiply first: "+b+" × "+c+" = "+p+".","Add: "+a+" + "+p+" = "+answer+"."];
    } else if(topic==="pre_algebra") {
      m=/^Solve: x ([+-]) (\d+) = (-?\d+)$/.exec(q); if(!m)fail("Use: Solve: x + 4 = 10");
      const n=BigInt(m[3])-(m[1]==="+"?BigInt(m[2]):-BigInt(m[2])); answer="x = "+n; steps=["Apply the inverse operation to both sides.","Isolate the variable: "+answer+"."];
    } else if(topic==="linear_equations") {
      m=/^Solve: (\d+)\*x \+ (-?\d+) = (-?\d+)$/.exec(q); if(!m)fail("Use: Solve: 3*x + 2 = 11");
      const a=BigInt(m[1]),b=BigInt(m[2]),c=BigInt(m[3]),d=c-b; if(a===0n||d%a!==0n)fail("This version supports non-zero coefficients and integer solutions."); answer="x = "+(d/a); steps=["Subtract "+b+" from both sides: "+a+"*x = "+d+".","Divide by "+a+" to get "+answer+"."];
    } else if(topic==="inequalities") {
      m=/^Solve: (\d+)\*x \+ (-?\d+) ([<>]) (-?\d+)$/.exec(q); if(!m)fail("Use: Solve: 2*x + 1 < 9");
      const a=BigInt(m[1]),b=BigInt(m[2]),c=BigInt(m[4]),d=c-b;if(a===0n||d%a!==0n)fail("This version supports positive coefficients and integer boundaries.");answer="x "+m[3]+" "+(d/a);steps=["Isolate x at the boundary.","Because the coefficient is positive, the inequality direction stays the same: "+answer+"."];
    } else if(topic==="exponents_and_roots") {
      m=/^Calculate: (\d+) \*\* 2$/.exec(q); const r=/^Calculate: sqrt\((\d+)\)$/.exec(q);
      if(m){const n=BigInt(m[1]),v=n*n;answer=String(v);steps=["Square means multiply the number by itself.",""+n+" × "+n+" = "+answer+"."];}
      else if(r){const n=BigInt(r[1]);let lo=0n,hi=n+1n;while(lo+1n<hi){const mid=(lo+hi)/2n;if(mid*mid<=n)lo=mid;else hi=mid;}if(lo*lo!==n)fail("Only exact integer square roots are supported.");answer=String(lo);steps=["Find the non-negative number whose square is the radicand.","√"+n+" = "+answer+"."];}
      else fail("Use: Calculate: 9 ** 2 or Calculate: sqrt(81)");
    } else if(topic==="basic_geometry") {
      m=/^(Area|Perimeter) of rectangle: length (\d+), width (\d+)$/.exec(q);if(!m)fail("Use: Area of rectangle: length 8, width 3");
      const l=BigInt(m[2]),w=BigInt(m[3]),v=m[1]==="Area"?l*w:2n*(l+w);answer=String(v);steps=m[1]==="Area"?["Area = length × width.",""+l+" × "+w+" = "+answer+"."]:["Perimeter = 2 × (length + width).","2 × ("+l+" + "+w+") = "+answer+"."];
    } else if(topic==="basic_statistics") {
      m=/^Mean of: ([0-9, ]+)$/.exec(q);if(!m)fail("Use: Mean of: 4, 6, 8");
      const vals=m[1].split(",").map(s=>s.trim());if(!vals.length||vals.some(s=>! /^\d+$/.test(s)))fail("Provide comma-separated whole numbers.");const total=vals.reduce((s,v)=>s+BigInt(v),0n);answer=ftext(fraction(total,BigInt(vals.length)));steps=["Add the values to get "+total+".","Divide by "+vals.length+" values to get "+answer+"."];
    } else if(topic==="basic_probability") {
      m=/^Probability: (\d+) favorable, (\d+) total$/.exec(q);if(!m)fail("Use: Probability: 2 favorable, 6 total");
      const a=BigInt(m[1]),b=BigInt(m[2]);if(b<=0n||a>b)fail("Favourable outcomes must be between zero and the positive total.");answer=ftext(fraction(a,b));steps=["Probability = favourable outcomes ÷ total outcomes.",""+a+"/"+b+" simplifies to "+answer+"."];
    } else if(topic==="median_and_range") {
      m=/^Median and range of: ([0-9, ]+)$/.exec(q);if(!m)fail("Use five comma-separated whole numbers.");
      const values=m[1].split(",").map(s=>s.trim()).map(s=>{if(!/^\d+$/.test(s))fail("Invalid value");return BigInt(s);}).sort((a,b)=>a<b?-1:a>b?1:0);
      if(values.length!==5)fail("Median and range requires five values.");
      const median=values[2],spread=values[4]-values[0];answer="median="+median+"; range="+spread;
      steps=["Sort the five values: "+values.join(", ")+".","The middle value is "+median+", and the range is "+values[4]+" - "+values[0]+" = "+spread+".","Step 3: "+answer+"."];
    } else if(topic==="simple_interest") {
      m=/^Simple interest: principal (\d+), rate (\d+)%, time (\d+) years$/.exec(q);if(!m)fail("Invalid simple-interest question.");
      const principal=BigInt(m[1]),rate=BigInt(m[2]),years=BigInt(m[3]);answer=ftext(fraction(principal*rate*years,100n));
      steps=["Use I = P * r * t / 100.","I = "+principal+" * "+rate+" * "+years+" / 100 = "+answer+"."];
    } else if(topic==="unit_conversion") {
      m=/^Convert: (\d+) (m|cm|kg) to (cm|mm|g)$/.exec(q);if(!m)fail("Invalid unit-conversion question.");
      const factors={"m:cm":100n,"cm:mm":10n,"kg:g":1000n},factor=factors[m[2]+":"+m[3]];if(!factor)fail("Unsupported unit conversion.");
      const amount=BigInt(m[1]);answer=String(amount*factor);steps=["1 "+m[2]+" = "+factor+" "+m[3]+".",m[1]+" * "+factor+" = "+answer+" "+m[3]+"."];
    } else if(topic==="pythagorean_theorem") {
      m=/^Hypotenuse of right triangle: legs (\d+), (\d+)$/.exec(q);if(!m)fail("Invalid Pythagorean question.");
      const a=BigInt(m[1]),b=BigInt(m[2]),square=a*a+b*b;let root=0n;while((root+1n)*(root+1n)<=square)root++;if(root*root!==square)fail("Triangle legs do not produce an integer hypotenuse.");
      answer=String(root);steps=["Use c * c = a * a + b * b = "+a+"^2 + "+b+"^2.","c = sqrt("+square+") = "+root+"."];
    } else fail("No solver for this topic.");
    return {topic,question:q,answer,steps,knowledge:{concept:TOPICS[topic].concept,rule:TOPICS[topic].rule,method:TOPICS[topic].method},verified:false};
  }
  // Independent answer checker: re-parses the question and recomputes its result.
  function verify(topic, question, answer) {
    try {
      const q=String(question).trim(); let m, expected;
      // Deliberately separate arithmetic helpers: verification does not call solver helpers.
      const checkGcd=(a,b)=>{a=a<0n?-a:a;b=b<0n?-b:b;while(b){const t=a%b;a=b;b=t;}return a||1n;};
      const checkFraction=(n,d)=>{if(d===0n)throw new Error("zero denominator");if(d<0n){n=-n;d=-d;}const g=checkGcd(n,d);return {n:n/g,d:d/g};};
      const checkText=f=>f.d===1n?String(f.n):String(f.n)+"/"+String(f.d);
      const checkParse=s=>{const p=/^(-?\d+)(?:\/(\d+))?$/.exec(s);if(!p)throw new Error("invalid fraction");return checkFraction(BigInt(p[1]),BigInt(p[2]||"1"));};
      const checkAdd=(a,b)=>checkFraction(a.n*b.d+b.n*a.d,a.d*b.d);
      const checkSub=(a,b)=>checkFraction(a.n*b.d-b.n*a.d,a.d*b.d);
      const checkMul=(a,b)=>checkFraction(a.n*b.n,a.d*b.d);
      const checkDiv=(a,b)=>checkFraction(a.n*b.d,a.d*b.n);
      const checkDecimal=s=>{if(!/^-?\d+(?:\.\d+)?$/.test(s))throw new Error("invalid decimal");const neg=s[0]==="-",raw=neg?s.slice(1):s,p=raw.split("."),den=10n**BigInt((p[1]||"").length),num=BigInt(p[0]+(p[1]||""));return checkFraction(neg?-num:num,den);};
      const checkDecimalText=value=>{let d=value.d,twos=0,fives=0;while(d%2n===0n){d/=2n;twos++;}while(d%5n===0n){d/=5n;fives++;}if(d!==1n)return checkText(value);const scale=Math.max(twos,fives);if(!scale)return String(value.n);const n=value.n*(2n**BigInt(scale-twos))*(5n**BigInt(scale-fives)),negative=n<0n?"-":"",digits=String(n<0n?-n:n).padStart(scale+1,"0");return (negative+digits.slice(0,-scale)+"."+digits.slice(-scale)).replace(/\.?0+$/,"");};
      if(topic==="whole_number_arithmetic"||topic==="integers") {
        m=/^Calculate: (-?\d+) ([+*/-]) (-?\d+)$/.exec(q);if(!m)return false;
        const a=BigInt(m[1]),b=BigInt(m[3]); if(m[2]==="+")expected=String(a+b);else if(m[2]==="-")expected=String(a-b);else if(m[2]==="*")expected=String(a*b);else {if(b===0n||a%b!==0n)return false;expected=String(a/b);}
      } else if(topic==="fractions") {
        m=/^Calculate: \((\d+\/\d+)\) ([+*/-]) \((\d+\/\d+)\)$/.exec(q);if(!m)return false;const a=checkParse(m[1]),b=checkParse(m[3]);expected=checkText(m[2]==="+"?checkAdd(a,b):m[2]==="-"?checkSub(a,b):m[2]==="*"?checkMul(a,b):checkDiv(a,b));
      } else if(topic==="decimals") {
        m=/^Calculate: (-?\d+(?:\.\d+)?) ([+-]) (-?\d+(?:\.\d+)?)$/.exec(q);if(!m)return false;expected=checkDecimalText(m[2]==="+"?checkAdd(checkDecimal(m[1]),checkDecimal(m[3])):checkSub(checkDecimal(m[1]),checkDecimal(m[3])));
      } else if(topic==="percentages") {m=/^Percentage: (\d+)% of (\d+)$/.exec(q);if(!m)return false;expected=checkText(checkFraction(BigInt(m[1])*BigInt(m[2]),100n));
      } else if(topic==="ratios_and_proportions") {m=/^Simplify ratio: (\d+):(\d+)$/.exec(q);if(!m)return false;const a=BigInt(m[1]),b=BigInt(m[2]);if(a===0n&&b===0n)return false;const g=checkGcd(a,b);expected=String(a/g)+":"+String(b/g);
      } else if(topic==="order_of_operations") {m=/^Calculate: (\d+) \+ (\d+) \* (\d+)$/.exec(q);if(!m)return false;expected=String(BigInt(m[1])+BigInt(m[2])*BigInt(m[3]));
      } else if(topic==="pre_algebra") {m=/^Solve: x ([+-]) (\d+) = (-?\d+)$/.exec(q);if(!m)return false;expected="x = "+(BigInt(m[3])-(m[1]==="+"?BigInt(m[2]):-BigInt(m[2])));
      } else if(topic==="linear_equations") {m=/^Solve: (\d+)\*x \+ (-?\d+) = (-?\d+)$/.exec(q);if(!m)return false;const a=BigInt(m[1]),d=BigInt(m[3])-BigInt(m[2]);if(a===0n||d%a!==0n)return false;expected="x = "+(d/a);
      } else if(topic==="inequalities") {m=/^Solve: (\d+)\*x \+ (-?\d+) ([<>]) (-?\d+)$/.exec(q);if(!m)return false;const a=BigInt(m[1]),d=BigInt(m[4])-BigInt(m[2]);if(a===0n||d%a!==0n)return false;expected="x "+m[3]+" "+(d/a);
      } else if(topic==="exponents_and_roots") {m=/^Calculate: (\d+) \*\* 2$/.exec(q);if(m)expected=String(BigInt(m[1])**2n);else {m=/^Calculate: sqrt\((\d+)\)$/.exec(q);if(!m)return false;const n=BigInt(m[1]);let r=0n;while((r+1n)*(r+1n)<=n)r++;if(r*r!==n)return false;expected=String(r);}
      } else if(topic==="basic_geometry") {m=/^(Area|Perimeter) of rectangle: length (\d+), width (\d+)$/.exec(q);if(!m)return false;const l=BigInt(m[2]),w=BigInt(m[3]);expected=String(m[1]==="Area"?l*w:2n*(l+w));
      } else if(topic==="basic_statistics") {m=/^Mean of: ([0-9, ]+)$/.exec(q);if(!m)return false;const a=m[1].split(",").map(s=>s.trim());if(a.some(s=>! /^\d+$/.test(s)))return false;expected=checkText(checkFraction(a.reduce((t,v)=>t+BigInt(v),0n),BigInt(a.length)));
      } else if(topic==="basic_probability") {m=/^Probability: (\d+) favorable, (\d+) total$/.exec(q);if(!m)return false;const a=BigInt(m[1]),b=BigInt(m[2]);if(b<=0n||a>b)return false;expected=checkText(checkFraction(a,b));
      } else if(topic==="median_and_range") {m=/^Median and range of: ([0-9, ]+)$/.exec(q);if(!m)return false;const a=m[1].split(",").map(s=>s.trim());if(a.length!==5||a.some(s=>!/^\d+$/.test(s)))return false;const v=a.map(BigInt).sort((x,y)=>x<y?-1:x>y?1:0);expected="median="+v[2]+"; range="+(v[4]-v[0]);
      } else if(topic==="simple_interest") {m=/^Simple interest: principal (\d+), rate (\d+)%, time (\d+) years$/.exec(q);if(!m)return false;expected=checkText(checkFraction(BigInt(m[1])*BigInt(m[2])*BigInt(m[3]),100n));
      } else if(topic==="unit_conversion") {m=/^Convert: (\d+) (m|cm|kg) to (cm|mm|g)$/.exec(q);if(!m)return false;const factors={"m:cm":100n,"cm:mm":10n,"kg:g":1000n},factor=factors[m[2]+":"+m[3]];if(!factor)return false;expected=String(BigInt(m[1])*factor);
      } else if(topic==="pythagorean_theorem") {m=/^Hypotenuse of right triangle: legs (\d+), (\d+)$/.exec(q);if(!m)return false;const n=BigInt(m[1])**2n+BigInt(m[2])**2n;let r=0n;while((r+1n)*(r+1n)<=n)r++;if(r*r!==n)return false;expected=String(r);
      } else return false;
      return String(answer).trim()===expected;
    } catch (_) { return false; }
  }
  function generate(topic,index) {
    const n=(index*17+7)%90+2, b=(index*11+3)%30+2;
    switch(topic) {
      case "whole_number_arithmetic": return "Calculate: "+n+" + "+b;
      case "fractions": return "Calculate: ("+n+"/"+(n+1)+") + ("+b+"/"+(b+1)+")";
      case "decimals": return "Calculate: "+(n/10).toFixed(1)+" + "+(b/100).toFixed(2);
      case "percentages": return "Percentage: "+((index*7)%90+10)+"% of "+n;
      case "ratios_and_proportions": return "Simplify ratio: "+(n*2)+":"+(b*2);
      case "integers": return "Calculate: -"+n+" + "+b;
      case "order_of_operations": return "Calculate: "+n+" + "+b+" * 3";
      case "pre_algebra": return "Solve: x + "+b+" = "+(n+b);
      case "linear_equations": return "Solve: 2*x + "+b+" = "+(2*n+b);
      case "inequalities": return "Solve: 2*x + "+b+" < "+(2*n+b);
      case "exponents_and_roots": return "Calculate: "+n+" ** 2";
      case "basic_geometry": return "Area of rectangle: length "+n+", width "+b;
      case "basic_statistics": return "Mean of: "+n+", "+b+", "+(n+b);
      case "basic_probability": return "Probability: "+(b%Math.max(1,n))+" favorable, "+n+" total";
      case "median_and_range": return "Median and range of: "+[n,b,n+b,n+2,b+1].join(", ");
      case "simple_interest": return "Simple interest: principal "+n+", rate 5%, time 2 years";
      case "unit_conversion": return "Convert: "+n+" m to cm";
      case "pythagorean_theorem": return "Hypotenuse of right triangle: legs 3, 4";
      default: fail("Unsupported topic");
    }
  }
  // Score only frozen, held-out test cases. Expected answers are consulted after solving.
  function evaluateHeldout(dataset) {
    if (!dataset || dataset.dataset_id !== "ultron-heldout-foundation-v1" || dataset.frozen !== true || !Array.isArray(dataset.examples) || dataset.examples.length === 0) fail("Invalid frozen evaluation dataset.");
    const ids = new Set();
    const perTopic = Object.create(null);
    const cases = dataset.examples.map(sample => {
      if (!sample || sample.split !== "test" || typeof sample.sample_id !== "string" || !sample.sample_id || ids.has(sample.sample_id) || !TOPICS[sample.topic] || typeof sample.question !== "string" || typeof sample.answer !== "string") fail("Evaluation dataset contains an invalid or non-test sample.");
      ids.add(sample.sample_id);
      const solved = solve(sample.topic, sample.question);
      const independentlyVerified = verify(sample.topic, sample.question, solved.answer);
      const passed = independentlyVerified && solved.answer === sample.answer;
      if (!perTopic[sample.topic]) perTopic[sample.topic] = { total: 0, passed: 0 };
      perTopic[sample.topic].total += 1;
      if (passed) perTopic[sample.topic].passed += 1;
      return { sampleId: sample.sample_id, topic: sample.topic, question: sample.question, expected: sample.answer, actual: solved.answer, independentlyVerified, passed };
    });
    const passed = cases.filter(item => item.passed).length;
    return { datasetId: dataset.dataset_id, total: cases.length, passed, failed: cases.length - passed, accuracy: passed / cases.length, perTopic, cases };
  }
  const api={TOPICS,TOPIC_KEYS,MAX_QUESTION_LENGTH,solve,verify,generate,evaluateHeldout};
  if(typeof module!=="undefined"&&module.exports)module.exports=api;
  root.ULTRON_MATH_AGENT=api;
})(typeof globalThis!=="undefined"?globalThis:this);
