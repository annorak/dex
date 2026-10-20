import argparse


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="dex",
        description="dex engine command-line interface.",
        epilog="Only help is available in this scaffold.",
    )
    parser.parse_args()
    parser.print_help()
