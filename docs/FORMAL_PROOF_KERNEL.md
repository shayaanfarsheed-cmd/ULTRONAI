# ULTRON Formal Proof Kernel — Stage 4

## Trust boundary

The browser-side kernel is a deterministic proof replayer. It validates typed syntax, isolated formal-system contexts, exact axiom identifiers, proof references, inference rules and assumption dependencies. It is not a general theorem prover or a Lean/Coq replacement. It does not establish consistency of the axioms and does not prove that the neural model has learned mathematics.

## Typed language

Terms include typed variables, natural numerals, successor, natural/field addition and multiplication, field and real rational literals, points, lines, typed betweenness relations, circles, circle centres/incidence, angles, right-angle/equality and parallel-intersection predicates, events, event sequences, the sample space, probability measures, countable unions/sums and sets and a dedicated `RealSet` domain for subsets of field values. Formula constructors include equality, strict order, incidence, conjunction, implication, negation, universal/existential quantification, membership and named predicates. AST nodes use closed schemas: unknown fields, malformed values, incompatible sorts and sparse arrays are rejected.

The `Real` sort is deliberately narrow: rational real literals and probability-measure results are represented, but general real arithmetic and a complete real-field signature are not implemented.

## Isolated formal contexts

Seven contexts are declared and do not inherit axioms from one another:

- `PEANO_N`: Peano arithmetic. Executable finite axioms: PEANO-02 and PEANO-03. PEANO-04 is an explicit induction schema, available only through the dedicated induction rule.
- `REAL_FIELD`: all nine researched field axioms FIELD-01 through FIELD-09 are represented as exact typed formulas.
- `ORDERED_FIELD`: explicitly enables FIELD-01 through FIELD-09 plus ORDER-01 trichotomy, ORDER-02 strict-order transitivity, ORDER-03 translation invariance and ORDER-04 multiplication by a positive factor.
- `COMPLETE_REAL`: explicitly enables the same field and order axioms plus COMPLETE-01, the least-upper-bound property. `RealSet` is a separate typed domain of subsets of field values; membership only accepts a `Field` element and a `RealSet` container.
- `EUCLID_GEOMETRY`: EUCLID-01, the existence of a common line through two distinct points; EUCLID-02, extension of a nonzero segment to a further point on the same line; EUCLID-03, construction of a circle with any chosen centre and a radius fixed by a point; EUCLID-04, equality of all right angles; and EUCLID-05, the same-side interior-angle parallel postulate.
- `KOLMOGOROV`: PROB-01 (zero is less than or equal to every event measure), PROB-02 (sample-space measure one) and PROB-03 (countable additivity over pairwise-disjoint event sequences).
- `ZFC`: finite axioms ZFC-01 extensionality, ZFC-02 empty-set existence, ZFC-03 pairing, ZFC-04 union, ZFC-05 power set, ZFC-06 infinity and ZFC-09 foundation; schemas ZFC-07 separation and ZFC-08 replacement.

Each executable axiom is bound to its exact Axiom Bank identifier and active context. A proof cannot use an axiom from another system or replace its formula with a forged statement.





## Euclidean parallel postulate

The Euclidean signature includes typed relations for a pair of same-side interior angles formed by two lines and a transversal, for their sum being less than two right angles, and for the two lines meeting on that same side. EUCLID-05 universally states that the first two conditions imply the third. This is the Axiom Bank's original-form statement at the relation level. The relations are primitive: the checker does not yet calculate angle sums or construct the transversal configuration from coordinates.

## Euclidean right-angle equality

The geometry context has a typed `Angle` sort and two strict formula nodes: `rightAngle(Angle)` and `angleEqual(Angle, Angle)`. EUCLID-04 states that any two right angles are equal. These are primitive relations in the formal signature; the kernel does not yet construct angles from rays, calculate angle measures or prove that a particular geometric construction is a right angle.

## Euclidean circle construction

The geometry context includes a `Circle` sort and typed `circleCenter(Circle, Point)` and `onCircle(Point, Circle)` formulas. EUCLID-03 states that for any chosen centre O and radius-defining point A, there exists a circle c with centre O and with A on the circle. This formalizes the construction postulate without inventing numeric distance or circumference operations.

## Euclidean segment extension

The geometry AST has a typed `between(first, middle, last)` formula. EUCLID-02 states that for any distinct points A and B there exist a point C and a line l such that A, B and C are incident with l and B lies between A and C. This is the segment-extension postulate with an explicit common-line and betweenness condition; it is not a numeric distance calculation.


## Probability countable additivity

The probability context has an `EventSequence` sort, countable-union and countable-sum term operators, and a typed `pairwiseDisjoint(EventSequence)` formula. PROB-03 states that for every pairwise-disjoint event sequence s, the measure of its countable union equals the countable sum of its event measures. The sequence, disjointness, union and sum symbols are primitive in this first-order signature; the kernel checks their sorts and exact axiom formula but does not evaluate infinite series, enumerate the sequence or prove measure-theoretic convergence.


## ZFC separation and replacement schemas

The checker does not register ZFC-07 or ZFC-08 as ordinary finite axioms. It exposes dedicated schema-instance rules:

- `separation` (ZFC-07) takes a source set, a typed predicate and an explicit predicate variable, then constructs the exact comprehension formula: a subset exists whose members are exactly the source-set members satisfying the predicate.
- `replacement` (ZFC-08) takes a typed relation with designated input/output variables. It constructs the premise that each source-set member has exactly one output, then the conclusion that the image set exists. The checker substitutes the output variable with fresh uniqueness/image variables and rejects binder capture.
- Both rules are available only in ZFC, have exact closed step schemas, preserve their schema identifiers and parameters in validated trace metadata, and record schema use separately from finite axiom use.

These are formula-schema instances, not a general meta-logic. Predicate parameters are represented as free set variables; the language still has no unrestricted formula metavariable or generic schema-instantiation engine.

## ZFC formulas

- **ZFC-01 — Extensionality:** two sets are equal when every set is a member of one exactly when it is a member of the other.
- **ZFC-02 — Empty set:** a set exists with no members.
- **ZFC-03 — Pairing:** for any two sets, a set exists whose members are exactly those two sets. The membership disjunction is expressed using De Morgan's law over the existing negation and conjunction nodes.
- **ZFC-04 — Union:** for every set of sets, a set exists whose members are exactly the elements of members of that family.
- **ZFC-05 — Power set:** for every set, a set exists whose members are exactly its subsets.
- **ZFC-06 — Infinity:** an inductive set exists. The formula requires an empty set as a member and, for every member x, a member Y whose elements are exactly the elements of x together with x (the set-theoretic successor x∪{x}).
- **ZFC-09 — Foundation:** every nonempty set has a member y such that no element of y is also a member of the original set. This is the formula-level statement that y is disjoint from the original set.

These are finite axiom formulas. They do not add a general set-construction evaluator or a set-theory decision procedure.

## Audited inference rules

The replayed rules are assumption, axiom, equality reflexivity/symmetry/transitivity, conjunction introduction/elimination, implication elimination/introduction, universal elimination/introduction, existential introduction/elimination and the schema-gated induction rule.

- Implication introduction must discharge an assumption that is actually present in the premise dependency set.
- Universal introduction reconstructs the quantified goal instance and enforces eigenvariable freshness against the property and every undischarged assumption used by the premise.
- Existential introduction reconstructs the existential body from the explicit witness and verified premise.
- Existential elimination checks the major existential premise, the matching temporary witness assumption, use of that assumption by the minor proof, no major-premise dependency on the discharged assumption, and no eigenvariable leakage into the conclusion or other open assumptions.
- Induction is enabled only for PEANO-04 and checks both P(0) and the successor step ∀k(P(k)→P(S(k))), including freshness and open-assumption side conditions.

Every premise must refer backward to an existing assumption or step. The checker recomputes each conclusion and tracks open assumptions, used axioms and schema dependencies.

## Validated working traces

A working trace must use the exact `ultron-proof-trace` envelope and contain a structured proof. The checker replays every step and compares an optional claimed conclusion with the replayed result. Free-form prose, unknown rules and forged conclusions are rejected. A validated trace is evidence for later tutoring; it is not yet a full misconception classifier.

## Deliberately unimplemented

- The probability signature represents countable sequences, unions and sums as primitive typed symbols; it does not evaluate infinite series or establish convergence/measure-theoretic properties beyond the registered PROB-03 axiom.
- The Angle and Line relations used by EUCLID-04/05 are primitive symbols. The kernel does not calculate angle measures, derive a right angle from perpendicular lines, or construct the same-side interior-angle configuration from coordinates.
- ZFC-07 separation and ZFC-08 replacement are schema instances generated by dedicated proof-step rules. Separation accepts a typed formula with one designated free set variable; replacement accepts a typed relation with designated input/output variables and checks unique-output functionality before constructing the image-set conclusion. Fresh binder names are enforced to prevent capture.
- ZFC-10 choice is stated using typed primitive relations for a family of nonempty sets indexed by a set and a choice function for that family. The kernel checks the relation argument sorts and exact axiom formula, but does not yet encode functions as sets of ordered pairs or evaluate function application.
- General real arithmetic beyond rational literals and the registered field operations remains unimplemented. The completeness axiom assumes the `RealSet` domain denotes subsets of the ordered field; it does not implement a general set-construction calculus or a numerical supremum evaluator.
- There is no free-form or handwriting proof parser, and no general negation introduction/elimination rule.
- The kernel does not decide theoremhood, prove axiom consistency or establish soundness of axioms beyond the trusted formalization assumptions.



The probability language distinguishes strict order (`lt`) from non-strict order (`le`). PROB-01 is encoded directly as `0 ≤ μ(A)` for every event, rather than relying on an unproved equivalence between nonnegativity and the negation of a strict inequality. Both order nodes enforce exact AST shape and matching numeric sorts; the probability context tests ensure field rationals cannot be substituted for Real values.


## Ordered-field and completeness formalization

The ordered-field context explicitly lists all nine field axioms as available alongside ORDER-01 through ORDER-04; this is a deliberate shared registration, not implicit inheritance. Trichotomy is encoded as exactly one of a<b, a=b, or b<a, using only the existing conjunction and negation connectives. Strict-order transitivity, addition invariance, and multiplication by a positive element are stated with typed Field terms.

The complete-real context explicitly lists those same field/order axioms and COMPLETE-01. A RealSet variable denotes a subset of the Field domain. COMPLETE-01 states: every nonempty RealSet that is bounded above has a least upper bound, expressed as an upper bound that is less than or equal to every other upper bound. The checker validates the complete quantified formula and the Field/RealSet membership sorts; it does not compute suprema.


For COMPLETE-01, the non-strict comparisons are expanded as the negation of the reverse strict comparison (x ≤ y is represented by ¬(y < x)). ORDER-01 trichotomy makes this equivalent to the usual non-strict order. This avoids treating the standalone `le` relation used by the probability context as if it were automatically connected to the ordered-field strict order.


## ZFC-10 — axiom of choice

The ZFC context enables the exact Axiom Bank identifier ZFC-10. Its formula is universally quantified over an index set and a family; if the typed `familyOfNonemptySets(family, indexSet)` relation holds, there exists a set satisfying `choiceFunction(choice, indexSet, family)`. Both relation nodes are closed-schema formulas that accept only Set-valued arguments, and the axiom is replayed only in ZFC.

This is an explicit relation-level formal signature. The current kernel does not yet represent a function as a set of Kuratowski ordered pairs, define function domain/application, or derive the two relations from membership formulas. Those internal graph semantics remain a future extension; the current implementation does not claim a constructive choice algorithm.
