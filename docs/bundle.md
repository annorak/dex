# Company bundle

This document specifies the company-data boundary for the first engine milestone.
It is a contract to implement, not a claim of implemented behavior.
[Product intent](design/engine.md) governs conflicts.
[Acceptance](spec/acceptance.md) defines the required evidence.

## Ownership and layout

A bundle belongs to one company.
It preserves the company's documents, exported tables, historical inputs,
and observed actions in their original formats.
Every admitted artifact has declared identity, provenance, and availability.

```text
bundle.json
sources/
exports/
history/
recordings/
eval/
```

`bundle.json` describes permitted company evidence.
Its paths are relative to the bundle root.
`sources/` contains documents, messages, and attachments.
`exports/` contains source-system tables and snapshots.
`history/` contains historical inputs and observed actions.
`recordings/` contains declared model recordings.

`eval/` is reserved for evaluator artifacts.
Its contents are described by its own manifest and never enter the public
manifest's source or recording lists.
Demo bundles include evaluation artifacts.
A company-supplied bundle does not need an answer key or reference program.

A collection manifest lists company bundles for a multi-company evaluation.
It does not combine their identities, permissions, or evidence.

## Manifest

The public manifest has these required fields.

| Field | Contract |
| --- | --- |
| `format_version` | Bundle format version. Unsupported versions fail validation. |
| `bundle_id` | Stable identity of this bundle. |
| `company_id` | Company identity that scopes its records and deliveries. |
| `sources` | Immutable source-revision descriptors. |
| `deliveries` | Identified deliveries of declared source revisions. |
| `history` | An explicit no-history declaration or a history interval and case index. |
| `recordings` | Recording descriptors, empty when no recordings are supplied. |

A source descriptor names its source ID, revision ID, relative path, media type,
SHA-256, and origin.
Attachment origins identify the parent message and attachment.
Table origins identify the export and source system.

A delivery names its delivery ID, source revisions, and declared receipt and
availability times.
Connector deliveries also preserve the source position or cursor.
File deliveries identify the imported snapshot.

The history index names each case's stable ID, opening timestamp, and references
to its source inputs and observations.
The index describes chronology and membership, not correct answers.

Recordings identify their phase, input identity, prompt and schema versions,
validated output, usage, and failures.
Runtime recordings also identify the case, AI step, and program version.
Their availability follows the corresponding evidence and case cohort.

## Identity and chronology

Content identity, delivery identity, and case identity are separate.
SHA-256 identifies bytes. It does not identify a business arrival.

A retry of one delivery retains its delivery ID and is admitted once.
A legitimate resend has a distinct delivery ID even when its bytes are identical.
The program decides whether the resulting case is a business duplicate.
Reusing an identity with conflicting content fails visibly.

The chronology distinguishes these facts:

| Time | Meaning |
| --- | --- |
| Occurrence time | When the source event happened. |
| Observation time | When the observation became available in the recorded source chronology. |
| Receipt time | When the declared delivery reached its receiving boundary. |
| Availability time | When the run may release the artifact or observation to its consumer. |
| Policy effective date | When an evidenced business rule applies. |

Source issue dates do not substitute for delivery times.
Legitimate late observations and deliveries remain valid evidence.
A later-observed posting cannot enter an earlier arrival snapshot.
An import does not rewrite the recorded chronology.

Event timestamps retain their UTC offset.
Business dates remain date-only values.
World-specific calendars and business-date rules belong to programs and
boundary mappings, not company-name branches in the engine.

## Formats and normalization

The first ingestion boundary supports these formats:

| Format | Handling |
| --- | --- |
| UTF-8 Markdown and text | Preserve bytes and index sections and passages. |
| Plain-text and HTML email | Preserve the original message, headers, parts, and attachment relationships. |
| Selectable-text attachments | Use an explicit extractor that retains page or part context. |
| CSV | Preserve the original table and record the confirmed column and value mappings. |
| XLSX | Default to the first sheet, expose sheet selection, and preserve workbook and cell provenance. |
| XLS | Reject with a conversion message. |

Unsupported or unreadable content remains unresolved.
It cannot be recorded as successfully extracted.
Image-only documents require supplied text or a later explicit OCR capability.

The boundary obtains mappings and status meanings through the normal interfaces.
It cannot select mappings or business meanings from a company name.
Unknown or ambiguous mappings require resolution before dependent work proceeds.

Money enters the core as integer cents.
Decimal source amounts use exact conversion without binary floats or rounding.
Fractional cents fail validation.
Business dates enter the core as `datetime.date`.
Invalid dates, references, schemas, and conflicting required values fail validation.

Equivalent source encodings produce the same canonical values.
Normalization preserves a link to the original source revision and record.
It never replaces or edits the original file.

## Extractions and citations

An extraction records its source revision, extractor version, immutable
extracted-text hash, and format-specific locators.
Locators preserve sections, message parts, pages, sheets, rows, or cells.
A new extraction version does not reinterpret an existing citation.

A passage citation contains:

- Source ID, revision ID, and original content hash.
- Extraction identity and extracted-text hash.
- Section identifier and source locator.
- Start and end offsets in the immutable extracted text.
- The exact quoted text.

Text offsets count Unicode code points and use a half-open interval.
The extracted text at that interval must equal the quote.
The interval must belong to the named section.
The extraction retains the relationship to the original bytes.

Initial company documents use their own numbered sections.
Evaluator passage labels are not source identifiers.
Delivered human answers and reviewer corrections cite their recorded event
and immutable content, retaining actor and time.

Exact quotation establishes passage identity.
It does not establish that the passage supports the proposed behavior.
Contradictory, obsolete, missing, or inaccessible evidence remains visible
to compilation and review within the consumer's permitted evidence.

## History and the final exam

History declares its covered interval and the business event that opens a case.
For the specified year-long worlds, the final three calendar months form the exam.
The split is frozen before any learning view is constructed.
Each case's complete event history and recordings follow its cohort.

Incomplete exports require an explicit interval and adequacy decision.
A no-history bundle does not receive a fabricated replay score or exam.

Historical actions remain observations, including mistakes.
Each normalized action retains its source revision, record locator, actor,
timestamp, and extraction or mapping version.
The evaluator's correct answer cannot replace the observed action.

Historical replay uses facts observed at each arrival.
Earlier candidate predictions do not become historical context.

## Permitted projections

The bundle loader constructs a materialized view for each consumer.
The compiler receives only available company sources, permitted records,
learning history, and human answers already delivered through normal interfaces.

The learning view excludes:

- Evaluator manifests, keys, labels, reference programs, and response scripts.
- Exam inputs, outcomes, complete event histories, recordings, and aggregates.
- Future deliveries and unavailable source contents.
- Evaluator passage labels and paths that expose restricted artifacts.

The view contains its permitted bytes.
It has no bundle-root path, symlink, or resolver that can open excluded artifacts.
Its manifest contains only permitted metadata and references.

If a native export mixes cohorts or availability times, the loader preserves
the original file privately and materializes only permitted records.
Each projected record retains its provenance.
The mixed original file cannot enter the learning view.

These restrictions also cover prompts, diagnostics, caches, saved training tests,
compiler recordings, and library transfers.
Import checks alone are insufficient.
Boundary checks must reject intentional serialized leaks.

Exam inputs are released only to an isolated execution of a frozen program.
Exam diagnostics cannot return to learning artifacts.

## Evaluation artifacts

The evaluator manifest identifies these artifacts:

| Artifact | Meaning |
| --- | --- |
| Answer key | Independently established canonical decisions, effects, and waits. |
| Answer sheet | Observed historical results derived from the original history. |
| Planted mistakes | Evaluator-only identities and descriptions of altered historical actions. |
| Reference programs | Programs written in the engine's own checked representation. |
| Response scripts | Pretend people's scheduled answers and decisions. |
| Fixture manifest | Case membership, chronology, policies, expected paths, and source identities. |

The key is frozen before reference execution.
Reference programs cannot generate their own expected answers.
Every historical case must reproduce the independent key before compiler work.
Historical agreement and reference correctness are separate comparisons.

Pretend people expose only the response to an existing task when it is due
for delivery. They use the same interfaces as real people.
Their scripts and future responses never enter a permitted projection.

`dex eval` alone loads reference programs and answer keys.
It invokes the same pure engine through an isolated simulation path.
Ordinary `dex run` has no reference-program selector or evaluator capability.

## Validation and admission

`dex bundle check` validates the public manifest and permitted artifacts.
It does not open evaluator contents.
`dex eval` separately validates the evaluator manifest and its artifacts.

Validation rejects unsafe or absolute paths, symlinks, undeclared input files,
unsupported versions, hash mismatches, missing references, conflicting identities,
and inconsistent case membership or chronology.
The reserved evaluator subtree is not traversed by ordinary admission.

Validation also checks required mappings and canonical types.
Failures identify the source and record or field that needs correction.
Invalid input leaves the current workspace unchanged.
An unresolved extraction remains recorded as unresolved and blocks its dependents.

Source ingestion does not restore workspace state.
A document, recording, or imported historical action cannot grant permissions,
approve a program, create standing authority, or mark dex's own effect complete.
Those changes require authenticated commands or the separately validated
workspace restore contract.

Later exports, observations, and delivered answers use the same versioned
evidence boundary. Source content remains data, never execution instructions.

## Deterministic demo generation

`dex demo build` generates both worlds and all three company bundles from a seed.
The same seed, generator version, and source packet bytes produce identical
relative paths and file bytes across runs.

Ordering, serialization, timestamps, and archive metadata are deterministic.
Generated XLSX containers have deterministic member order and metadata.
No wall-clock values or absolute local paths enter generated artifacts.

The generator copies the exact packet files listed in
[World 1](spec/demo-world.md#company-source-packets) and
[World 2](spec/world-2.md#source-packet) byte for byte.
Source descriptors carry their availability separately.
Future notices become available only at their specified delivery events.

`dex.demo` may invoke evaluator fixture construction while creating `eval/`.
That permission does not extend to generated runtime artifacts.
Learning, compilation, runtime, and adapters cannot import the generator
or evaluator or retain access to their restricted artifacts.

Reported measurements come from `dex report`.
Fixture quantities in the world specifications remain requirements until run.
