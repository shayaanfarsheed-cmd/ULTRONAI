# ULTRON Formal Proof Kernel — Stage 4

## Trust boundary

The browser-side kernel is a deterministic proof replayer. It validates typed syntax, isolated formal-system contexts, exact axiom identifiers, proof references, inference rules and assumption dependencies. It is not a general theorem prover or a Lean/Coq replacement. It does not establish consistency of the axioms and does not prove that the neural model has learned mathematics.

## Typed language

Terms include typed variables, natural numerals, successor, natural/field addition and multiplication, field and real rational literals, points, lines, typed betweenness relations, events, the sample space, probability measures and sets. Formula constructors include equality, strict order, incidence, conjunction, implication, negation, universal/existential quantification, membership and named predicates. AST nodes use closed schemas: unknown fields, malformed values, incompatible sorts and sparse arrays are rejected.

The `Real` sort is deliberately narrow: rational real literals and probability-measure results are represented, but general real arithmetic and a complete real-field signature are not implemented.

## Isolated formal contexts

Seven contexts are declared and do not inherit axioms from one another:

- `PEANO_N`: Peano arithmetic. Executable finite axioms: PEANO-02 and PEANO-03. PEANO-04 is an explicit induction schema, available only through the dedicated induction rule.
- `REAL_FIELD`: all nine researched field axioms FIELD-01 through FIELD-09 are represented as exact typed formulas.
- `ORDERED_FIELD` and `COMPLETE_REAL`: declared but have no executable axioms yet.
- `EUCLID_GEOMETRY`: EUCLID-01, the existence of a common line through two distinct points; and EUCLID-02, extension of a nonzero segment to a further point on the same line.
- `KOLMOGOROV`: PROB-01 (nonnegative measure) and PROB-02 (sample-space measure one).
- `ZFC`: ZFC-01 extensionality, ZFC-02 empty-set existence, ZFC-03 pairing, ZFC-04 union, ZFC-05 power set, ZFC-06 infinity and ZFC-09 foundation.

Each executable axiom is bound to its exact Axiom Bank identifier and active context. A proof cannot use an axiom from another system or replace its formula with a forged statement.


## Euclidean segment extension

The geometry AST has a typed `between(first, middle, last)` formula. EUCLID-02 states that for any distinct points A and B there exist a point C and a line l such that A, B and C are incident with l and B lies between A and C. This is the segment-extension postulate with an explicit common-line and betweenness condition; it is not a numeric distance calculation.

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

- PROB-03 countable additivity remains disabled: the language has no countable event sequences, countable unions or infinite sums.
- EUCLID-03 through EUCLID-05 remain disabled: circle construction, angle measure and parallel behavior need additional geometric objects and side conditions.
- ZFC-07 separation and ZFC-08 replacement remain schemas; no formula-metavariable/schema-instantiation mechanism exists.
- ZFC-10 choice remains disabled; the language does not yet model indexed families and choice functions.
- General real arithmetic, ordered-field laws and completeness axioms remain unimplemented.
- There is no free-form or handwriting proof parser, and no general negation introduction/elimination rule.
- The kernel does not decide theoremhood, prove axiom consistency or establish soundness of axioms beyond the trusted formalization assumptions.

