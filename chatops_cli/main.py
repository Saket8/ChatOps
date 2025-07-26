"""
Main entry point for ChatOps CLI application.
"""

import sys
from .cli.main import cli


def main() -> int:
    """
    Main entry point for the ChatOps CLI.

    Returns:
        int: Exit code (0 for success, non-zero for error)
    """
    try:
        cli()
        return 0
    except Exception:
        return 1


if __name__ == "__main__":
    sys.exit(main())
