# ULTRON Formal Proof Kernel — Stage 4

## Trust boundary
The browser-side kernel is a deterministic proof replayer. It checks typed syntax, system boundaries, references and inference rules. It is not a general theorem prover or a Lean/Coq replacement, and it does not prove the neural model has learned mathematics.

## Typed language
Terms: typed variables, natural numerals, successor, natural/field addition and multiplication, rational field literals, points, events and sets. Formulas: equality, strict order, conjunction, implication, negation, universal quantification, membership and named predicates. Unknown nodes and ill-typed equalities are rejected.

## Formal contexts
Seven isolated contexts are declared: Peano arithmetic, real fields, ordered fields, complete real fields, Euclidean geometry, Kolmogorov probability and ZFC. No context inherits another system's axioms. Only explicitly machine-formalized entries are executable. The currently executable entries are PEANO-02 (zero is not a successor), PEANO-03 (successor injectivity), FIELD-01 (addition commutativity), FIELD-02 (addition associativity), FIELD-03 (additive identity), FIELD-05 (multiplication commutativity), FIELD-06 (multiplication associativity), and FIELD-09 (distributivity). Other Axiom Bank statements remain reference-only when their full logical signature or side conditions are not represented; PEANO-04 is handled by its dedicated schema rule rather than a finite axiom formula.

## Audited rules
assumption, axiom, eq_refl, eq_symm, eq_trans, and_intro, and_left, and_right, imp_elim, imp_intro, forall_elim and the schema-gated induction rule are replayed. The induction rule is enabled only for PEANO-04 in the Peano context and requires a checked base instance P(0) plus the checked successor step ∀k(P(k)→P(S(k))). Each proof records PEANO-04 as a schema dependency. The induction variable must be fresh from every variable and binder inside P, and must not occur free in any undischarged assumption used by either premise. Every premise must refer backward to an existing assumption or step. The checker recomputes the conclusion. Axiom IDs are checked against the exact active context.

## Validated working traces
A trace must use kind "ultron-proof-trace" and contain a proof envelope. verifyWorkingTrace replays every step and compares an optional claimed conclusion. Free-form prose, unknown rules and forged conclusions are rejected. Tutoring may use a trace as evidence only after validation; this is not yet a misconception classifier.

## Limitations
No free-form/handwriting parser, existential quantifier, negation introduction/elimination rules, inequality arithmetic, geometric construction rules, probability measure rules or ZFC schemas. Ordered/completeness contexts currently have no executable axioms. Universal introduction is intentionally not exposed until eigenvariable side-condition support is complete. The kernel does not establish consistency of the underlying axioms.


The negation connective is now representable in well-typed formulas, but the kernel intentionally has no general negation introduction or elimination rules. Only exact registered axiom statements can currently use it. PEANO-01 successor closure remains enforced as a typed-constructor/sort invariant rather than an independently replayable formula. FIELD-04, FIELD-07 and FIELD-08 are not enabled because the current language does not fully encode the required existential and nonzero/inverse conditions. Ordered-field, completeness, Euclidean, probability and ZFC entries remain reference-only until their signatures and side conditions are formalized.


The PEANO-04 induction schema is represented as a dedicated inference rule rather than a fabricated finite axiom formula. Its proof step names `axiomId: "PEANO-04"`, a fresh `variable`, and exactly two premises in base/step order. The checker constructs the expected instances from the quantified conclusion and rejects mismatched base cases, successor steps, cross-system use and variable capture. It reports the schema separately in `usedAxiomSchemas`.
