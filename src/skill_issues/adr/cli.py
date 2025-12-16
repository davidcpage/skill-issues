"""CLI entry point for adr command."""

import argparse
import sys


def main() -> int:
    """Entry point for the adr command."""
    parser = argparse.ArgumentParser(
        description="Architecture Decision Records skill",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  adr init              # Initialize adr skill in current directory
  adr init /path/to/project  # Initialize in specified directory
"""
    )

    # Subcommands
    subparsers = parser.add_subparsers(dest="subcommand")
    init_parser = subparsers.add_parser("init", help="Initialize adr skill in a project")
    init_parser.add_argument("path", nargs="?", help="Project path (default: current directory)")

    args = parser.parse_args()

    if args.subcommand == "init":
        from .. import init as init_module
        return init_module.run_init(["adr"], getattr(args, "path", None))

    # No subcommand - show help
    parser.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())
