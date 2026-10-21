import argparse
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="dex",
        description="dex engine command-line interface.",
    )
    commands = parser.add_subparsers(dest="command")
    evaluator = commands.add_parser(
        "eval", help="Verify a versioned evaluator scenario without activating it."
    )
    evaluator.add_argument("--scenario", required=True, type=Path)
    evaluator.add_argument("--out", required=True, type=Path)
    arguments = parser.parse_args()
    if arguments.command == "eval":
        from dex.eval.scenarios import run_scenario

        raise SystemExit(run_scenario(arguments.scenario, arguments.out))
    parser.print_help()
