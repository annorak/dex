import argparse
import sys
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
    if sys.argv[1:2] == ["workspace"]:
        workspace_commands = workspace.add_subparsers(
            dest="workspace_command", required=True
        )
        apply = workspace_commands.add_parser("command")
        apply.add_argument("workspace", type=Path)
        apply.add_argument("--command", required=True, type=Path, dest="command_file")
    bundle = commands.add_parser(
        "bundle", help="Validate company evidence or project permitted learning inputs."
    )
    bundle_commands = bundle.add_subparsers(dest="bundle_command", required=True)
    check = bundle_commands.add_parser(
        "check", help="Check a public bundle without opening eval/."
    )
    check.add_argument("bundle", type=Path)
    project = bundle_commands.add_parser(
        "project", help="Materialize available learning evidence without exam access."
    )
    project.add_argument("bundle", type=Path)
    project.add_argument("--consumer", choices=("learning",), required=True)
    project.add_argument("--as-of", required=True)
    project.add_argument("--out", required=True, type=Path)
    demo = commands.add_parser(
        "demo", help="Build deterministic synthetic company bundles."
    )
    demo_commands = demo.add_subparsers(dest="demo_command", required=True)
    build = demo_commands.add_parser(
        "build", help="Build both complete World 1 companies."
    )
    build.add_argument("--world", default="all")
    build.add_argument("--seed", required=True, type=int)
    build.add_argument("--out", required=True, type=Path)
    run = commands.add_parser(
        "run", help="Run company cases with a verified, approved program."
    )
    run.add_argument("bundle", type=Path)
    run.add_argument("--program", required=True, type=Path)
    run.add_argument("--workspace", required=True, type=Path)
    run.add_argument("--out", required=True, type=Path)
    arguments = parser.parse_args()
    if arguments.command == "demo":
        from dex.demo.build import run_build

        raise SystemExit(run_build(arguments.world, arguments.seed, arguments.out))
    if arguments.command == "bundle":
        if arguments.bundle_command == "project":
            from dex.bundle.commands import project_bundle

            raise SystemExit(
                project_bundle(arguments.bundle, arguments.as_of, arguments.out)
            )
        from dex.bundle.commands import check_bundle

        raise SystemExit(check_bundle(arguments.bundle))
    if arguments.command == "run":
        from dex.bundle.commands import run_bundle

        raise SystemExit(
            run_bundle(
                arguments.bundle, arguments.program, arguments.workspace, arguments.out
            )
        )
    if arguments.command == "eval":
        from dex.eval.scenarios import run_scenario

        raise SystemExit(run_scenario(arguments.scenario, arguments.out))
    if arguments.command == "workspace":
        from dex.workspace_command import run_command

        raise SystemExit(run_command(arguments.workspace, arguments.command_file))
    parser.print_help()
