# M1-09 isolation review

Verdict: FAIL.

Head: b509d09f63b2e4bc92ea2e02430b313600941882
Base: 9d66353dd4136abccda85ee4d1b49fb88d7fae3c
Stable patch ID: 8efe2fc3e33ff5cf20b5be342bb67cd6e729e61a

This review applies only to that exact head against that base. It does not
carry forward across product changes without delta review and focused probes.
The independent checkout is /private/tmp/dex-m1-09-isolation and was clean
when identity was recorded. Python 3.13.11 and uv 0.11.31 were used.

## Blocking findings

1. P2: malformed mapping enum values crash public admission.
   In src/dex/bundle/formats.py, _value uses unvalidated kind and encoding
   values in set membership at lines 260, 285 and 292. A valid mapped CSV
   descriptor with kind=[] or money encoding={} raises TypeError through
   check_bundle. The CLI exits 1 with a traceback instead of a source/field
   error. Receipts 06-bad-kind-cli.txt and 07-bad-encoding-cli.txt reproduce
   both paths. Validate enum shapes at the mapping boundary; do not hide
   malformed source configuration as successful extraction.

2. P2: malformed XLSX container exceptions escape admission.
   An otherwise valid XLSX whose ZIP member compression method is 99 raises
   NotImplementedError at archive.read in formats.py:151. _xlsx's exception
   boundary at lines 236-246 does not handle this. Receipt
   08-bad-xlsx-cli.txt records a traceback and exit 1. Unsupported/unreadable
   spreadsheet content must remain unresolved or receive a named rejection,
   with source context. The outer bundle ZIP boundary already handles this
   class of failure; the XLSX extraction boundary does not.

Both failures occur while loading the bundle, before run_bundle opens a
workspace. No authority escalation or evaluator disclosure was demonstrated.
They block the explicit malformed-input requirement, which excludes crashes
as acceptable rejections.

## Passing isolation evidence

Receipt 09-runtime-isolation.txt records the final targeted probe:

- Public directory and collection admission completed with os.open and
  os.scandir tripwires against evaluator paths.
- ZIP admission completed with an archive.open tripwire against eval members.
- An unsupported outer ZIP compression method received a named archive error.
- A fresh ordinary-runtime subprocess succeeded while imports of dex.eval
  and dex.demo were forbidden.
- The approved workspace rebuilt to the same state while execute_function
  was replaced by a failing tripwire. No effects or grants were introduced.

Static review found ordinary run loads a StructuralArtifact, compares the
exact artifact with the persisted catalog, validates source evidence and
company identity, and delegates StartCase admission to Workspace.start_cases.
The core requires complete checks and persisted program approval. One shared
reducer owns execution and rebuild. The changed admission maps are replayed
state; replay has no new I/O or dispatch path.

relative_path rejects absolute, traversal, backslash, null, colon, and eval
components before declared-file access. Directory reads use descriptor-relative
O_NOFOLLOW access. Public inventory skips top-level eval before inspecting
its type. ZIP inventory skips evaluator entries before opening them.
Collection bundle paths pass the same validator before opening.

Source text, observations, model recordings, and approval-looking flags do
not become workspace authority. The public manifest has a closed field set;
ordinary run creates only StartCase commands from admitted cases and does not
restore imported actions, approvals, grants, or effect confirmations.
Company scope is checked against the local session and persisted registration.
The change does not edit trust accounting, grant/revocation checks, sampling,
effect dispatch, or reconciliation semantics. The M1-08 handoff and final
isolation report were consulted for the prior review boundary, not rerun.

## Receipts and limitations

01-install.txt records isolated setup. 10-identity.txt records revisions,
patch ID, clean status and tool versions. Raw receipts remain unchanged.
The reproducible probe is /private/tmp/dex-m1-09-isolation-probe.py.
Generated adversarial inputs are named in each probe receipt.

02-adversarial.txt is a failed probe setup caused by an invalid macOS /dev/fd
assumption. 03-adversarial.txt had invalid mapping fixture setup and does not
prove those malformed enum paths. Both are preserved. 04, 05 and 09 use the
corrected setup; 06-08 capture actual CLI crashes.

No product or repository test files were edited. No full gate, scenario suite,
performance measurement, production authentication, UI, OCR, or later milestone
verification is claimed. No PR, commit, push, merge or auto-merge was performed.
