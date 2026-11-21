# ULTRON Formal Proof Kernel — Stage 4

## Trust boundary
The browser-side kernel is a deterministic proof replayer. It checks typed syntax, system boundaries, references and inference rules. It is not a general theorem prover or a Lean/Coq replacement, and it does not prove the neural model has learned mathematics.

## Typed language
Terms: typed variables, natural numerals, successor, natural/field addition and multiplication, field and real literals, points, lines, events, sample spaces, probability measures, sets. Empty-set existence is expressed by the ZFC-02 existential formula. Formulas: equality, strict order, incidence, conjunction, implication, negation, universal and existential quantification, membership and named predicates. Unknown nodes and ill-typed equalities are rejected.

## Formal contexts
Seven isolated contexts are declared: Peano arithmetic, real fields, ordered fields, complete real fields, Euclidean geometry, Kolmogorov probability and ZFC. No context inherits another system's axioms. Only explicitly machine-formalized entries are executable. The currently executable entries are PEANO-02 (zero is not a successor), PEANO-03 (successor injectivity), FIELD-01 (addition commutativity), FIELD-02 (addition associativity), FIELD-03 (additive identity), FIELD-04 (additive inverse existence), FIELD-05 (multiplication commutativity), FIELD-06 (multiplication associativity), FIELD-07 (multiplicative identity and 0≠1), FIELD-08 (multiplicative inverse for nonzero values), and FIELD-09 (distributivity), EUCLID-01 (a line through any two distinct points), PROB-01 (probability measure is greater than or equal to zero), PROB-02 (sample-space probability one), ZFC-01 (extensionality), and ZFC-02 (empty-set existence). PROB-03 countable additivity and the other geometric and set-theoretic entries remain reference-only until sequence, union, construction and schema operators are represented. PEANO-04 is handled by its dedicated schema rule rather than a finite axiom formula.

## Audited rules
assumption, axiom, eq_refl, eq_symm, eq_trans, and_intro, and_left, and_right, imp_elim, imp_intro, forall_elim, eigenvariable-checked forall_intro, witness-checked exists_intro, scoped exists_elim and the schema-gated induction rule are replayed. The induction rule is enabled only for PEANO-04 in the Peano context and requires a checked base instance P(0) plus the checked successor step ∀k(P(k)→P(S(k))). Each proof records PEANO-04 as a schema dependency. For forall_intro, the eigenvariable must be fresh from every variable and binder inside the quantified property and must not occur free in any undischarged assumption used by the premise. For induction, the induction variable has the same freshness requirement across both premises. Every premise must refer backward to an existing assumption or step. The checker recomputes the conclusion. Axiom IDs are checked against the exact active context.


## Newly executable formal foundations — pending validation

The following initial statements are represented by exact Axiom Bank IDs and are enabled only in their own contexts:

- `EUCLID-01`: for any two distinct points, there exists a line incident with both. The AST now has a distinct `Line` term sort and a typed `incident(Point, Line)` formula. The antecedent explicitly requires point inequality.
- `PROB-01`: every event has nonnegative measure, represented as the negation of a strictly negative measure.
- `PROB-02`: the sample space has measure one. The probability context uses a dedicated `Real` sort, a sample-space term and a measure term whose argument must have sort `Event`.
- `ZFC-01`: extensionality, represented as equality of sets whose members are equivalent in both directions for every set.
- `ZFC-02`: existence of a set with no members, i.e. the empty-set existence axiom.

These are exact finite formulas, not a claim that the complete theories are implemented. The probability context does not yet implement countable additivity (`PROB-03)): the language lacks sequence, countable-union and infinite-sum operators. The geometry context does not yet implement construction rules beyond the first postulate. ZFC pairing, union, power set, separation, replacement, foundation and choice remain disabled. The ordered-field and complete-real contexts remain isolated and currently have no executable axioms. The `Real` sort is currently limited to typed rational literals and probability-measure results; general real arithmetic and field laws over that sort are not implemented.

## Validated working traces
A trace must use kind "ultron-proof-trace" and contain a proof envelope. verifyWorkingTrace replays every step and compares an optional claimed conclusion. Free-form prose, unknown rules and forged conclusions are rejected. Tutoring may use a trace as evidence only after validation; this is not yet a misconception classifier.

## Limitations
No free-form/handwriting parser, negation introduction/elimination rules, general arithmetic over the Real sort, geometric construction rules beyond EUCLID-01, countable probability additivity, or ZFC pairing/union/power-set/separation/replacement/foundation/choice rules. Ordered/completeness contexts currently have no executable axioms. Universal introduction is restricted to the single checked-premise rule with explicit eigenvariable side conditions. The kernel does not establish consistency of the underlying axioms.


The negation connective is now representable in well-typed formulas, but the kernel intentionally has no general negation introduction or elimination rules. Only exact registered axiom statements can currently use it. PEANO-01 successor closure remains enforced as a typed-constructor/sort invariant rather than an independently replayable formula. FIELD-04, FIELD-07 and FIELD-08 are enabled with typed existential formulas and distinguished rational constants 0 and 1. Their witness reasoning is governed by the scoped exists_intro and exists_elim rules. Ordered-field, completeness, Euclidean, probability and ZFC entries remain reference-only until their signatures and side conditions are formalized.


The PEANO-04 induction schema is represented as a dedicated inference rule rather than a fabricated finite axiom formula. Its proof step names `axiomId: "PEANO-04"`, a fresh `variable`, and exactly two premises in base/step order. The checker constructs the expected instances from the quantified conclusion and rejects mismatched base cases, successor steps, cross-system use and variable capture. It reports the schema separately in `usedAxiomSchemas`.


Universal introduction (`forall_intro`) takes exactly one verified premise and a fresh eigenvariable. The checker reconstructs the expected premise by substituting that variable into the quantified goal body, then rejects the step when the eigenvariable is free in any undischarged assumption supporting the premise. It is not a parser for natural-language universal claims.


Existential formulas now have a typed AST node and capture-aware substitution under nested existential binders. This allows the proof kernel to represent the full FIELD-04 and FIELD-08 existence clauses. FIELD-07 uses rational field literals as the distinguished 0 and 1 constants in this field signature and explicitly records 0≠1. Existential introduction checks an explicit witness by reconstructing the quantified body. Existential elimination requires a temporary witness assumption used only by the minor proof, checks that assumption against the existential body, rejects witness leakage into the conclusion or other open assumptions, and removes the discharged assumption from the resulting dependency set.


The `exists_elim` rule takes exactly two premises in order: an existential major premise and a minor proof. Its `variable` is an eigenvariable and `discharge` names the temporary assumption matching the existential body instantiated at that variable. The eigenvariable must not occur free in the major premise, conclusion or any other undischarged assumption. The temporary assumption must occur in the minor proof's dependency set and must not support the major premise. A successful rule removes only that assumption from the result's open assumptions.


## Newly formalized contexts

The geometry context has a typed `Line` term and an incidence formula. EUCLID-01 includes the distinct-points antecedent and an existential line incident with both points; it is not asserted for coincident points.

The probability context has sample-space and measure terms whose output sort is a dedicated `Real` sort. PROB-01 is represented as the negation of a negative measure, and PROB-02 fixes the probability of the whole sample space to one. PROB-03 remains disabled because the language does not yet represent countable event sequences, countable unions and infinite sums.

The ZFC context formalizes extensionality as two-way membership implication for every set and existence of an empty set. Remaining ZFC construction and schema axioms stay disabled until their full operators and side conditions are implemented.
