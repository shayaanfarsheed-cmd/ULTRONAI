# ULTRON Axiom Bank — research notes and scope

Version 1.0.0. This bank is an educational, curated reference catalog, not a formal proof assistant or a complete library of mathematical foundations.

## Research findings and design rules

An axiom is a starting assumption inside a specified formal system. It is not a theorem that has been proved from other assumptions. A definition fixes terminology, while a theorem must be derived. Rules of inference govern valid derivations. Different presentations may choose different primitive terms and axiom lists; therefore every entry is tagged with a system and domain.

The initial catalog covers the following systems. The Peano signature/structure entry is identified separately from axioms; Separation and Replacement are identified as axiom schemas rather than individual one-off axioms:
- **Peano natural-number axioms:** successor closure, zero not being a successor, injectivity of successor, and induction. The exact presentation varies; some versions begin at 0 and others at 1. [University of Florida notes](https://people.clas.ufl.edu/groisser/files/peano_axioms.pdf), [Toho University notes](https://www.lab2.toho-u.ac.jp/sci/is/tsuchiya/teaching/classB/lecture/B.pdf).
- **Field axioms:** commutativity, associativity, identities, inverses (multiplicative inverse only for nonzero values), and distributivity. [UIC real-number notes](https://homepages.math.uic.edu/~saunders/MATH313/INRA/INRA_chapters0and1.pdf), [LibreTexts real-number axioms](https://math.libretexts.org/Bookshelves/Mathematical_Logic_and_Proof/An_Introduction_to_Proof_via_Inquiry-Based_Learning_(Ernst)/05%3A_New_Page/5.01%3A_New_Page).
- **Ordered-field axioms:** trichotomy, transitivity, order preservation under addition, and order preservation under multiplication by a positive value. Rationals and reals are both ordered fields. [Portland State analysis text](https://content.library.pdx.edu/files/PDXScholar/Math/Introduction-to-Mathematical-Analysis-I-3rd-Edition/20/).
- **Completeness of the real numbers:** every nonempty real subset bounded above has a least upper bound. This is stronger than ordered-field structure and must not be assumed for rational numbers. [UIC notes](https://homepages.math.uic.edu/~saunders/MATH313/INRA/INRA_chapters0and1.pdf), [Bayreuth foundations notes](https://www.mathe2.uni-bayreuth.de/stoll/teaching/FoundationsOfHigherMathematics-WS2025/LectureNotes-FoundationsOfHigherMathematics.pdf).
- **Euclid's five geometry postulates:** line, segment extension, circle construction, equality of right angles, and the parallel postulate. The fifth postulate is a substantive choice; alternatives lead to non-Euclidean geometries. [University of Glasgow notes](https://www.maths.gla.ac.uk/wws/cabripages/klein/hilbert.html), [Euclid's Elements guide](https://www.euclids-elements.org/elements/books/bookI/postulates/post5/).
- **Kolmogorov probability axioms:** non-negativity, normalization of the sample space, and countable additivity for pairwise-disjoint events. Disjointness is a required condition, not an optional detail. [Cambridge University Press excerpt](https://assets.cambridge.org/97811071/78915/excerpt/9781107178915_excerpt.pdf), [Boston University probability notes](https://www.cs.bu.edu/faculty/snyder/cs237/Handouts%20and%20Web%20Documents/Handouts/WeissChapterOne.pdf).
- **ZFC set theory:** extensionality, empty set, pairing, union, power set, infinity, separation and replacement schemas, foundation, and choice. Choice is an additional axiom beyond ZF. [Stanford Encyclopedia of Philosophy](https://plato.stanford.edu/entries/set-theory/zf.html), [TU Darmstadt ZFC notes](https://wwwevs.mathematik.tu-darmstadt.de/index.php?evsdir=1059&evsfile=zfc.pdf).

## Important limitations

1. The catalog deliberately does not claim to be exhaustive.
2. Axiom lists are presentation-dependent; identifiers are ULTRON catalog identifiers, not universal textbook numbering.
3. A topic-to-axiom tag is a learning association, not proof that the existing JavaScript solver derives its result from that axiom.
4. Existing foundation question solvers remain deterministic arithmetic procedures. This bank does not yet provide machine-checked derivations from formal axioms.
5. The existing structured reasoning kernel independently checks final answers and deterministic replay, but does not formally prove intermediate natural-language steps.
6. Euclidean geometry, real-field, probability and set-theory axioms must not be mixed without an explicit compatible formal context.
7. The natural-number Peano system and field system are different structures. Natural numbers are not a field because nonzero natural numbers do not all have multiplicative inverses in the natural numbers.
8. The bank is static code, not an external AI service and not generated training data. It does not write user questions or answers to storage.

## Future work

- Add explicit typed formal-language expressions and scope checking.
- Add a proof kernel with a small, audited inference-rule set.
- Store proof dependencies as axiom/theorem identifiers.
- Add theorem libraries only with independently checkable proofs.
- Connect topic lessons to axioms only when the formal domain is known.
- Expand beyond the current foundation topics after coverage and tests are established.
