# Isolation probe packaging applicability

PASS. The packaged probe preserves the isolation review evidence.

Product head remains 499198ca10a2a7c3bb69aa5c34b3ceaab71427e6.
Base remains 5a6faaa69b4644a12593a719c42a9752bdfbb4f9.
Stable product patch ID remains 274aa5d21338095dc47b05f6f9b7eb65b04e7a1e.

Compared the original isolation/round1/probe.py with
packaging/isolation/round1/probe.py and inspected
proposals/023-portable-probes.diff.

The only changes add argparse, require --root/--base/--head, resolve supplied
revision arguments through git rev-parse --verify, and bind ROOT to --root.
The existing equality check against the checkout HEAD remains.

Receipt 007-packaging-applicability.txt proves all 33 assertion ASTs match,
all statements from ROOT.mkdir() onward match, and imports match except for
argparse. The packaged --help exits 0 and exposes all required arguments.
No fixture generation, test suite, performance run or product re-review ran.

Original probe, reports and receipts remain unchanged. The earlier isolation
PASS applies to the unchanged product. The packaged script is a portable
copy of the proven probe, not a new execution result.
