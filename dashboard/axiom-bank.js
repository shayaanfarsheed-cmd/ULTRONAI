(function (root) {
  "use strict";

  // Axioms are scoped to formal systems. These records are educational references,
  // not a claim that every topic silently assumes every listed axiom.
  const SYSTEMS = Object.freeze({
    PEANO_N: { label: "Peano arithmetic (natural numbers)", domain: "natural_numbers", description: "A second-order successor-and-induction presentation; equivalent presentations vary in whether zero or one is the initial natural number.", references: ["https://people.clas.ufl.edu/groisser/files/peano_axioms.pdf", "https://www.lab2.toho-u.ac.jp/sci/is/tsuchiya/teaching/classB/lecture/B.pdf"] },
    REAL_FIELD: { label: "Real numbers as a field", domain: "real_number_arithmetic", description: "The field laws govern addition and multiplication; they do not by themselves supply order or completeness.", references: ["https://homepages.math.uic.edu/~saunders/MATH313/INRA/INRA_chapters0and1.pdf", "https://math.libretexts.org/Bookshelves/Mathematical_Logic_and_Proof/An_Introduction_to_Proof_via_Inquiry-Based_Learning_(Ernst)/05%3A_New_Page/5.01%3A_New_Page"] },
    ORDERED_FIELD: { label: "Ordered field", domain: "ordered_real_or_rational_arithmetic", description: "A field equipped with a compatible linear order. Both rational and real numbers are ordered fields.", references: ["https://content.library.pdx.edu/files/PDXScholar/Math/Introduction-to-Mathematical-Analysis-I-3rd-Edition/20/", "https://math.libretexts.org/Bookshelves/Mathematical_Logic_and_Proof/An_Introduction_to_Proof_via_Inquiry-Based_Learning_(Ernst)/05%3A_New_Page/5.01%3A_New_Page"] },
    COMPLETE_REAL: { label: "Complete ordered real field", domain: "real_analysis_limits", description: "The least-upper-bound property distinguishes the real numbers from incomplete ordered fields such as the rationals.", references: ["https://homepages.math.uic.edu/~saunders/MATH313/INRA/INRA_chapters0and1.pdf", "https://www.mathe2.uni-bayreuth.de/stoll/teaching/FoundationsOfHigherMathematics-WS2025/LectureNotes-FoundationsOfHigherMathematics.pdf"] },
    EUCLID_GEOMETRY: { label: "Euclidean plane geometry", domain: "euclidean_geometry", description: "Euclid's five postulates form a classical geometry foundation. The parallel postulate is not a theorem of the first four in neutral geometry; changing it leads to non-Euclidean geometries.", references: ["https://www.maths.gla.ac.uk/wws/cabripages/klein/hilbert.html", "https://www.euclids-elements.org/elements/books/bookI/postulates/post5/"] },
    KOLMOGOROV: { label: "Kolmogorov probability", domain: "probability_measure", description: "Probability is a measure on a sample space/event sigma-algebra; countable additivity applies to pairwise-disjoint events.", references: ["https://assets.cambridge.org/97811071/78915/excerpt/9781107178915_excerpt.pdf", "https://www.cs.bu.edu/faculty/snyder/cs237/Handouts%20and%20Web%20Documents/Handouts/WeissChapterOne.pdf"] },
    ZFC: { label: "Zermelo–Fraenkel set theory with Choice", domain: "set_theory", description: "A foundational axiom system for sets. Separation and Replacement are axiom schemas, not single finite formulas; Choice is an additional principle.", references: ["https://plato.stanford.edu/entries/set-theory/zf.html", "https://wwwevs.mathematik.tu-darmstadt.de/index.php?evsdir=1059&evsfile=zfc.pdf"] }
  });

  function deepFreeze(value) {
    if (!value || typeof value !== "object" || Object.isFrozen(value)) return value;
    Object.freeze(value);
    Object.keys(value).forEach(key => deepFreeze(value[key]));
    return value;
  }
  deepFreeze(SYSTEMS);

  const ENTRIES = [
    ["PEANO-00","PEANO_N","natural-number-structure","The natural-number structure is given by a set, a distinguished initial element and a successor function.","There exist N, 0 in N, and S:N→N.","The natural numbers, zero and successor are the primitive structure in this presentation of Peano arithmetic.","Specify the natural-number domain and successor operation before applying Peano axioms.","foundation",["whole_number_arithmetic"]],
    ["PEANO-01","PEANO_N","successor-closure","A natural number's successor is a natural number.","For every n in N, S(n) is in N.","The successor operation stays inside the natural-number domain.","A successor step cannot leave N.","foundation",["whole_number_arithmetic","order_of_operations","pre_algebra"]],
    ["PEANO-02","PEANO_N","zero-is-not-successor","The initial natural number is not the successor of any natural number.","For every n in N, S(n) ≠ 0.","The number system has a designated starting point.","Do not identify zero with a successor value.","foundation",["whole_number_arithmetic"]],
    ["PEANO-03","PEANO_N","successor-injective","Equal successors have equal predecessors.","S(m) = S(n) implies m = n.","Successor does not merge two distinct natural numbers.","If two successor expressions are equal, their inputs must be equal.","foundation",["whole_number_arithmetic"]],
    ["PEANO-04","PEANO_N","mathematical-induction","A property holding at the base value and preserved by successor holds for every natural number.","If P(0) and for every n, P(n) implies P(S(n)), then P(n) for all n in N.","Induction proves statements for all natural numbers from a base case and an inductive step.","State both the base case and the inductive step.","proof",["whole_number_arithmetic","exponents_and_roots"]],
    ["FIELD-01","REAL_FIELD","addition-commutativity","Addition is commutative.","For all a,b in F, a+b=b+a.","The order of addends does not change the sum.","Reorder addends when it makes a calculation easier.","foundation",["whole_number_arithmetic","fractions","decimals","integers","pre_algebra"]],
    ["FIELD-02","REAL_FIELD","addition-associativity","Addition is associative.","For all a,b,c in F, (a+b)+c=a+(b+c).","Grouping addends does not change the sum.","Regroup additions without changing their order.","foundation",["whole_number_arithmetic","fractions","decimals","integers"]],
    ["FIELD-03","REAL_FIELD","additive-identity","Zero is the additive identity.","For all a in F, a+0=0+a=a.","Adding zero leaves a value unchanged.","A zero term can be removed from a sum.","foundation",["whole_number_arithmetic","integers","pre_algebra"]],
    ["FIELD-04","REAL_FIELD","additive-inverse","Every field element has an additive inverse.","For every a in F, there exists -a in F with a+(-a)=0.","A value can be cancelled by its additive inverse.","Use the opposite value to isolate an unknown in an equation.","foundation",["integers","pre_algebra","linear_equations"]],
    ["FIELD-05","REAL_FIELD","multiplication-commutativity","Multiplication is commutative.","For all a,b in F, ab=ba.","The order of factors does not change the product.","Reorder factors when useful.","foundation",["whole_number_arithmetic","fractions","decimals"]],
    ["FIELD-06","REAL_FIELD","multiplication-associativity","Multiplication is associative.","For all a,b,c in F, (ab)c=a(bc).","Regrouping factors does not change their product.","Regroup factors without changing their order.","foundation",["whole_number_arithmetic","fractions","decimals"]],
    ["FIELD-07","REAL_FIELD","multiplicative-identity","One is the multiplicative identity and is distinct from zero.","There exists 1 in F, 1≠0, and for every a, a·1=1·a=a.","Multiplying by one leaves a value unchanged.","A factor of one can be removed.","foundation",["whole_number_arithmetic","fractions","decimals"]],
    ["FIELD-08","REAL_FIELD","multiplicative-inverse","Every nonzero field element has a multiplicative inverse.","For every a≠0 in F, there exists a⁻¹ with a·a⁻¹=1.","Division by a nonzero value corresponds to multiplying by its inverse.","Check that the divisor is nonzero before using an inverse.","foundation",["fractions","linear_equations","ratios_and_proportions"]],
    ["FIELD-09","REAL_FIELD","distributivity","Multiplication distributes over addition.","For all a,b,c in F, a(b+c)=ab+ac.","A factor outside parentheses multiplies each term inside.","Expand or factor expressions using the same equality.","foundation",["pre_algebra","linear_equations","integers"]],
    ["ORDER-01","ORDERED_FIELD","trichotomy","Exactly one of less than, equal to, or greater than holds for any two ordered-field elements.","Exactly one of a<b, a=b, b<a holds.","The order compares every pair consistently.","Compare values using one of the three mutually exclusive cases.","foundation",["integers","inequalities"]],
    ["ORDER-02","ORDERED_FIELD","order-transitivity","Less-than is transitive.","If a<b and b<c, then a<c.","A chain of strict inequalities can be combined.","Link inequalities only when the middle terms match.","foundation",["inequalities"]],
    ["ORDER-03","ORDERED_FIELD","addition-preserves-order","Adding the same value to both sides preserves strict order.","If a<b, then a+c<b+c.","A common addend does not reverse or destroy an inequality.","Add or subtract the same amount on both sides.","foundation",["inequalities","linear_equations"]],
    ["ORDER-04","ORDERED_FIELD","positive-multiplication-preserves-order","Multiplying both sides by a positive value preserves strict order.","If a<b and 0<c, then ac<bc.","The positivity condition is essential.","Before multiplying an inequality, determine the sign of the factor.","foundation",["inequalities"]],
    ["COMPLETE-01","COMPLETE_REAL","least-upper-bound","Every nonempty subset of the real numbers that is bounded above has a least upper bound in the real numbers.","If A⊆R is nonempty and bounded above, sup(A) exists in R.","Completeness rules out gaps that occur in other ordered fields.","Use only in a real-number setting; this is stronger than field and order laws.","advanced",[]],
    ["EUCLID-01","EUCLID_GEOMETRY","line-through-two-points","A straight line can be drawn through any two distinct points.","Given distinct points A and B, a line through A and B exists.","This is a Euclidean incidence postulate.","Check that the geometry model and distinct-point condition apply.","foundation",["basic_geometry"]],
    ["EUCLID-02","EUCLID_GEOMETRY","extend-segment","A finite straight segment can be extended along its line.","A given segment can be extended continuously along its supporting line.","This is a construction postulate in Euclid's geometry.","Use only for Euclidean straight-line constructions.","foundation",["basic_geometry"]],
    ["EUCLID-03","EUCLID_GEOMETRY","draw-circle","A circle can be drawn with any chosen centre and radius determined by a point.","Given centre O and point A, a circle centred at O through A can be constructed.","This is a Euclidean construction postulate.","The radius is the distance from centre to the given point.","foundation",["basic_geometry"]],
    ["EUCLID-04","EUCLID_GEOMETRY","right-angles-equal","All right angles are equal to one another.","Any two right angles have equal measure.","This is a Euclidean angle postulate.","Requires the Euclidean geometry setting.","foundation",["basic_geometry"]],
    ["EUCLID-05","EUCLID_GEOMETRY","parallel-postulate","Euclid's fifth postulate fixes the parallel behaviour of Euclidean geometry.","In Euclid's original form, sufficiently small same-side interior angles imply the two lines meet on that side.","This distinguishes Euclidean geometry from alternatives with different parallel axioms.","Do not silently use this postulate in neutral or non-Euclidean geometry.","advanced",["basic_geometry","pythagorean_theorem"]],
    ["PROB-01","KOLMOGOROV","nonnegative-probability","The probability of every event is nonnegative.","For every event A, P(A)≥0.","Probability measures assign no event a negative mass.","Confirm the object is an event in the probability space.","foundation",["basic_probability"]],
    ["PROB-02","KOLMOGOROV","total-probability-one","The probability of the whole sample space is one.","The probability measure assigns the entire sample space Ω probability one: P(Ω)=1.","Some outcome in the sample space is certain.","Use only for the full sample space Ω.","foundation",["basic_probability"]],
    ["PROB-03","KOLMOGOROV","countable-additivity","Probability is countably additive over pairwise-disjoint events.","For pairwise-disjoint A₁,A₂,…, P(⋃Aᵢ)=ΣP(Aᵢ).","The disjointness condition is required; overlapping events cannot simply be summed.","Check pairwise disjointness before adding probabilities.","advanced",["basic_probability"]],
    ["ZFC-01","ZFC","extensionality","Sets with exactly the same elements are equal.","If for every z, z∈A iff z∈B, then A=B.","A set is determined by its members.","Compare membership of every possible element.","advanced",[]],
    ["ZFC-02","ZFC","empty-set","An empty set exists.","There exists a set with no members; it is denoted ∅.","The empty set provides a basic set-theoretic object.","Distinguish the empty set from a set containing the empty set.","advanced",[]],
    ["ZFC-03","ZFC","pairing","For any two sets, a set containing exactly those two sets exists.","For all A,B, the set {A,B} exists.","Pairing permits finite set construction.","Repeated values produce a singleton set.","advanced",[]],
    ["ZFC-04","ZFC","union","The union of a set of sets exists.","For every X there is ⋃X containing exactly the elements of members of X.","Union collects elements one level inside a family of sets.","Distinguish X from ⋃X.","advanced",[]],
    ["ZFC-05","ZFC","power-set","Every set has a set of all its subsets.","For every X, the power set P(X) exists.","The power set collects all subsets of X.","A subset is not the same thing as an element of X.","advanced",[]],
    ["ZFC-06","ZFC","infinity","An inductive set exists, allowing construction of the natural numbers.","There exists a set containing ∅ and closed under successor.","This supplies an infinite set in ZF.","This is a set-existence axiom, not the induction principle itself.","advanced",[]],
    ["ZFC-07","ZFC","separation-schema","A definable subcollection of an existing set is a set.","For each permitted formula φ and set X, {x∈X:φ(x)} exists.","Separation restricts comprehension to subsets of an already existing set.","Do not use unrestricted comprehension over all objects.","advanced",[]],
    ["ZFC-08","ZFC","replacement-schema","The image of a set under a definable functional relation is a set.","If each x∈X has a unique y satisfying φ(x,y), the collection of such y is a set.","Replacement supports constructions that collect definable outputs.","This is an axiom schema, with one instance per formula.","advanced",[]],
    ["ZFC-09","ZFC","foundation","Every nonempty set has an element disjoint from the original set.","For every nonempty X, some y∈X satisfies y∩X=∅.","Foundation excludes descending membership loops in standard well-founded set theory.","Treat as a ZF foundation assumption, not a property of every possible set theory.","advanced",[]],
    ["ZFC-10","ZFC","choice","Every family of nonempty sets admits a choice function.","For an index set I and a family (Aᵢ)ᵢ∈I of nonempty sets, there exists a function f with domain I such that f(i)∈Aᵢ for every i∈I.","Choice is an additional axiom in ZFC, not part of ZF alone.","Do not assume constructive selection from the statement alone.","advanced",[]]
  ].map(row => Object.freeze({
    id: row[0], system: row[1], key: row[2], category: row[0] === "PEANO-00" ? "structure" : (/schema$/.test(row[2]) ? "schema" : "axiom"),
    name: row[3], formal: row[4], meaning: row[5], teaching: row[6],
    level: row[7], topics: Object.freeze(row[8].slice()),
    references: SYSTEMS[row[1]].references,
    systemLabel: SYSTEMS[row[1]].label,
    domain: SYSTEMS[row[1]].domain
  }));

  const byId = Object.freeze(Object.fromEntries(ENTRIES.map(entry => [entry.id, entry])));
  function get(id) { return byId[id] || null; }
  function list(options) {
    const filter = options || {};
    return ENTRIES.filter(entry =>
      (!filter.system || entry.system === filter.system) &&
      (!filter.topic || entry.topics.includes(filter.topic)) &&
      (!filter.level || entry.level === filter.level) &&
      (!filter.query || [entry.id, entry.key, entry.name, entry.formal, entry.meaning, entry.systemLabel].join(" ").toLowerCase().includes(String(filter.query).toLowerCase()))
    );
  }
  function forTopic(topic, options) {
    const filter = options || {};
    return list({ topic, level: filter.level }).map(entry => Object.freeze({
      id: entry.id, category: entry.category, name: entry.name, formal: entry.formal, meaning: entry.meaning,
      teaching: entry.teaching, system: entry.system, systemLabel: entry.systemLabel,
      domain: entry.domain, references: entry.references
    }));
  }
  function explain(id) {
    const entry = get(id);
    if (!entry) return { found: false, message: "Unknown axiom identifier." };
    return { found: true, entry, caution: "This statement is valid only within its named formal system and domain. Axioms are assumptions of that system, not universal facts independent of assumptions." };
  }
  const api = Object.freeze({
    version: "1.0.0",
    entries: Object.freeze(ENTRIES),
    systems: SYSTEMS,
    count: ENTRIES.length,
    get, list, forTopic, explain
  });
  if (typeof module !== "undefined" && module.exports) module.exports = api;
  root.ULTRON_AXIOM_BANK = api;
})(typeof globalThis !== "undefined" ? globalThis : this);
