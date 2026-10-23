# M1-09 isolation fix validation

Verdict: PASS at 0d1575242d01b75035af158def47cc8030eb1215,
against base 9d66353dd4136abccda85ee4d1b49fb88d7fae3c.
Stable patch ID: 47edd7cc1d10ec842d894803a307d56085079342.

This continues the independent isolation review in report.md. The original
FAIL and raw receipts remain unchanged. The complete b509d09..0d15752 delta
was reviewed, including admission identities, extraction identity, chronology,
format handling, fixture changes, and output timing. Receipt 11 records the
exact revision, clean checkout, patch ID, Python 3.13.11 and uv 0.11.31.

## Findings closed

- Malformed mapping kind and encoding now pass through text validation before
  enum membership and before processing table rows. Allowed fields depend on
  the chosen kind. Meanings require a nonempty object of nonempty strings.
  History adequacy decision now receives the same string-shape validation.
  Receipts 13 and 14 rerun the original frozen malformed bundles and record
  exit 2 with source-specific mapping field errors, without a traceback.
- XLSX extraction now contains RuntimeError, including NotImplementedError,
  and records unreadable content as unresolved. Receipt 15 reruns the original
  malformed compression input and records exit 0 with an explicit XLSX
  unresolved reason. It does not claim successful extraction. The PDF
  boundary receives equivalent exception containment.

## Delta and regression evidence

Receipt 12 reruns the original adversarial probe at the new head. Directory
and collection admission pass with evaluator-path open/traversal tripwires;
ZIP admission passes with evaluator-member content access forbidden.
The separate outer-ZIP malformed compression path remains a named rejection.
A fresh ordinary-runtime subprocess succeeds while dex.eval and dex.demo
imports are forbidden. Event rebuild equals persisted state while restricted
interpretation is replaced by a failing tripwire.

Receipt 16 passes four focused checks: future delivery cannot execute now,
grouping a previously admitted identity cannot duplicate it, disjoint records
remain valid while overlap is rejected, and delivery identity survives reopen
and replay. No duplicate full suite or performance run was performed.

The revised extraction identity is derived from source/revision, original
digest, and extractor version, with the extractor version retained separately
in immutable extraction evidence. This introduces no evaluator or company
lookup. Future source, delivery and case availability checks precede workspace
opening. Per-record admission keys are validated and tracked in the same pure
reducer, scoped by company and delivery. Refused batches remain unappended.
Distinct records and distinct delivery resends retain separate membership.

The delta adds no evaluator selector, key loader, SandboxWorkspace path,
source-granted authority, replay I/O, interpretation, or effect dispatch.
Program verification and persisted approval remain required. M1-07 recovery
and M1-08 authority, grants, revocation, trust and sampling paths are unchanged.
The ordinary-run fixture's second text document exercises the corrected
source-specific extraction identity through the existing catalog.

This PASS applies to this exact head/base and reviewed patch. Unchanged
boundaries retain the earlier static review; changed boundaries have current
focused evidence. Any further product delta needs applicability review.
Gates, all ten live CLI lanes and performance remain the verifier's coverage.
No production authentication, adapters, UI, OCR or later milestone behavior
is claimed. No product/test edits, commits, pushes or PR operations were made.
