"""
Main entry point for ChatOps CLI application.
"""

import sys


def main() -> int:
    """
    Main entry point for the ChatOps CLI.

    Returns:
        int: Exit code (0 for success, non-zero for error)
    """
    print("ChatOps CLI v0.1.0")
    print("Offline ChatOps CLI with LangChain + Local LLM")
    print("Foundation setup complete!")
    return 0


if __name__ == "__main__":
    sys.exit(main())
