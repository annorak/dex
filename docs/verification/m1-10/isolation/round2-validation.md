# M1-10 second isolation fix validation

Verdict: PASS at ecd4b9a against milestone base c7c1976.
The focused fix parent is b9d6794. Raw receipts 15 through 19 retain exact
revisions, argv, checkout status, stdout, stderr and exit status.

The same independent reviewer inspected the complete two-file delta and
repinned the existing isolated checkout. final-validation.md and all earlier
failure receipts remain unchanged.

Receipt 15 proves the learning-view decoder, shared lineage validator,
recording validator, recording parser and event types are byte-identical
to the previously reviewed head. Receipt 16 contains the complete delta:
production edits change only alias-exclusion closure inside projection.
The runtime recording filter and serialization paths are unchanged.
The prior recording-lineage proof therefore remains applicable.

The revised closure processes newly restricted original hashes after parent
and alias propagation. Each newly processed hash advances a finite set;
propagation only adds selectors. It retains the known partial primary
extraction while excluding ambiguous alternate extractions and their parents.
No metadata permission, resolver, runtime hook or authority path was added.
The delta adds no comments or suppression directives.

Receipt 17 passes ten focused cases: nested raw MIME aliases at depths zero,
one and two in both source orders, and permitted versus excluded recording
producers. Restricted raw aliases disappear while permitted message bodies
and primary learning rows remain available.

Receipt 18 reruns the independent recording probe at the new head. Projection
successfully omits the exam-produced recording and its payload. A forged
saved view fails decoding and all six serialization destinations with the
lineage error. Receipt 19 retains a permitted learning producer with the
identical payload text in all five company-scoped destinations. No keyword
or company-name permission rule substitutes for provenance.

No new actionable isolation finding remains. The separate correctness
reviewer owns the original nested-alias reproducer. No product edits,
full-suite run or performance measurement were performed. CPU-heavy work
ended after receipt 19. This PASS applies to the named head/base and complete
reviewed delta; later product changes need applicability review.
