#!/usr/bin/env python3
"""
Main module for running ChatOps CLI as a package.

This allows running the CLI with: python -m chatops_cli
"""

from .main import main

if __name__ == "__main__":
    exit(main()) 