# ULTRON Formal Proof Kernel — Stage 4

## Trust boundary
The browser-side kernel is a deterministic proof replayer. It checks typed syntax, system boundaries, references and inference rules. It is not a general theorem prover or a Lean/Coq replacement, and it does not prove the neural model has learned mathematics.

## Typed language
Terms: typed variables, natural numerals, successor, natural/field addition and multiplication, rational field literals, points, events and sets. Formulas: equality, strict order, conjunction, implication, universal quantification, membership and named predicates. Unknown nodes and ill-typed equalities are rejected.

## Formal contexts
Seven isolated contexts are declared: Peano arithmetic, real fields, ordered fields, complete real fields, Euclidean geometry, Kolmogorov probability and ZFC. No context inherits another system's axioms. Only explicitly machine-formalized entries are executable. This first kernel slice formalizes PEANO-03 (successor injectivity) and FIELD-01 (addition commutativity). Remaining Axiom Bank entries are reference-only, including schemas and statements requiring richer signatures or side conditions.

## Audited rules
assumption, axiom, eq_refl, eq_symm, eq_trans, and_intro, and_left, and_right, imp_elim, imp_intro and forall_elim are replayed. Every premise must refer backward to an existing assumption or step. The checker recomputes the conclusion. Axiom IDs are checked against the exact active context.

## Validated working traces
A trace must use kind "ultron-proof-trace" and contain a proof envelope. verifyWorkingTrace replays every step and compares an optional claimed conclusion. Free-form prose, unknown rules and forged conclusions are rejected. Tutoring may use a trace as evidence only after validation; this is not yet a misconception classifier.

## Limitations
No free-form/handwriting parser, existential quantifier, negation, induction rule, inequality arithmetic, geometric construction rules, probability measure rules or ZFC schemas. Ordered/completeness contexts currently have no executable axioms. Universal introduction is intentionally not exposed until eigenvariable side-condition support is complete. The kernel does not establish consistency of the underlying axioms.
