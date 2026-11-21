# ULTRON Formal Proof Kernel — Stage 4

## Trust boundary
The browser-side kernel is a deterministic proof replayer. It checks typed syntax, system boundaries, references and inference rules. It is not a general theorem prover or a Lean/Coq replacement, and it does not prove the neural model has learned mathematics.

## Typed language
Terms: typed variables, natural numerals, successor, natural/field addition and multiplication, rational field literals, points, events and sets. Formulas: equality, strict order, conjunction, implication, negation, universal and existential quantification, membership and named predicates. Unknown nodes and ill-typed equalities are rejected.

## Formal contexts
Seven isolated contexts are declared: Peano arithmetic, real fields, ordered fields, complete real fields, Euclidean geometry, Kolmogorov probability and ZFC. No context inherits another system's axioms. Only explicitly machine-formalized entries are executable. The currently executable entries are PEANO-02 (zero is not a successor), PEANO-03 (successor injectivity), FIELD-01 (addition commutativity), FIELD-02 (addition associativity), FIELD-03 (additive identity), FIELD-04 (additive inverse existence), FIELD-05 (multiplication commutativity), FIELD-06 (multiplication associativity), FIELD-07 (multiplicative identity and 0≠1), FIELD-08 (multiplicative inverse for nonzero values), and FIELD-09 (distributivity). Other Axiom Bank statements remain reference-only when their full logical signature or side conditions are not represented; PEANO-04 is handled by its dedicated schema rule rather than a finite axiom formula.

## Audited rules
assumption, axiom, eq_refl, eq_symm, eq_trans, and_intro, and_left, and_right, imp_elim, imp_intro, forall_elim, eigenvariable-checked forall_intro, witness-checked exists_intro, scoped exists_elim and the schema-gated induction rule are replayed. The induction rule is enabled only for PEANO-04 in the Peano context and requires a checked base instance P(0) plus the checked successor step ∀k(P(k)→P(S(k))). Each proof records PEANO-04 as a schema dependency. For forall_intro, the eigenvariable must be fresh from every variable and binder inside the quantified property and must not occur free in any undischarged assumption used by the premise. For induction, the induction variable has the same freshness requirement across both premises. Every premise must refer backward to an existing assumption or step. The checker recomputes the conclusion. Axiom IDs are checked against the exact active context.

## Validated working traces
A trace must use kind "ultron-proof-trace" and contain a proof envelope. verifyWorkingTrace replays every step and compares an optional claimed conclusion. Free-form prose, unknown rules and forged conclusions are rejected. Tutoring may use a trace as evidence only after validation; this is not yet a misconception classifier.

## Limitations
No free-form/handwriting parser, negation introduction/elimination rules, inequality arithmetic, geometric construction rules, probability measure rules or ZFC schemas. Ordered/completeness contexts currently have no executable axioms. Universal introduction is restricted to the single checked-premise rule with explicit eigenvariable side conditions. The kernel does not establish consistency of the underlying axioms.


The negation connective is now representable in well-typed formulas, but the kernel intentionally has no general negation introduction or elimination rules. Only exact registered axiom statements can currently use it. PEANO-01 successor closure remains enforced as a typed-constructor/sort invariant rather than an independently replayable formula. FIELD-04, FIELD-07 and FIELD-08 are not enabled because the current language does not fully encode the required existential and nonzero/inverse conditions. Ordered-field, completeness, Euclidean, probability and ZFC entries remain reference-only until their signatures and side conditions are formalized.


The PEANO-04 induction schema is represented as a dedicated inference rule rather than a fabricated finite axiom formula. Its proof step names `axiomId: "PEANO-04"`, a fresh `variable`, and exactly two premises in base/step order. The checker constructs the expected instances from the quantified conclusion and rejects mismatched base cases, successor steps, cross-system use and variable capture. It reports the schema separately in `usedAxiomSchemas`.


Universal introduction (`forall_intro`) takes exactly one verified premise and a fresh eigenvariable. The checker reconstructs the expected premise by substituting that variable into the quantified goal body, then rejects the step when the eigenvariable is free in any undischarged assumption supporting the premise. It is not a parser for natural-language universal claims.


Existential formulas now have a typed AST node and capture-aware substitution under nested existential binders. This allows the proof kernel to represent the full FIELD-04 and FIELD-08 existence clauses. FIELD-07 uses rational field literals as the distinguished 0 and 1 constants in this field signature and explicitly records 0≠1. Existential introduction checks an explicit witness by reconstructing the quantified body. Existential elimination requires a temporary witness assumption used only by the minor proof, checks that assumption against the existential body, rejects witness leakage into the conclusion or other open assumptions, and removes the discharged assumption from the resulting dependency set.


The `exists_elim` rule takes exactly two premises in order: an existential major premise and a minor proof. Its `variable` is an eigenvariable and `discharge` names the temporary assumption matching the existential body instantiated at that variable. The eigenvariable must not occur free in the major premise, conclusion or any other undischarged assumption. The temporary assumption must occur in the minor proof's dependency set and must not support the major premise. A successful rule removes only that assumption from the result's open assumptions.
