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
    workspace = commands.add_parser(
        "workspace", help="Persist typed local workspace commands."
    )
    workspace_commands = workspace.add_subparsers(
        dest="workspace_command", required=True
    )
    apply = workspace_commands.add_parser("command")
    apply.add_argument("workspace", type=Path)
    apply.add_argument("--command", required=True, type=Path, dest="command_file")
    arguments = parser.parse_args()
    if arguments.command == "eval":
        from dex.eval.scenarios import run_scenario

        raise SystemExit(run_scenario(arguments.scenario, arguments.out))
    if arguments.command == "workspace":
        from dex.workspace_command import run_command

        raise SystemExit(run_command(arguments.workspace, arguments.command_file))
    parser.print_help()
