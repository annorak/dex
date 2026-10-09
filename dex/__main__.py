import argparse
import sys
from collections.abc import Sequence
from pathlib import Path


def main(argv: Sequence[str]) -> int:
    parser = argparse.ArgumentParser(prog="dex")
    subparsers = parser.add_subparsers(dest="command", required=True)

    for name, help_text in (
        ("run", "Run dex"),
        ("measure", "Measure dex"),
    ):
        subparsers.add_parser(name, help=help_text)

    verify_parser = subparsers.add_parser("verify-package", help="Verify a package")
    verify_parser.add_argument("package", type=Path)
    args = parser.parse_args(argv)

    print(f"dex: {args.command} is not implemented yet", file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
