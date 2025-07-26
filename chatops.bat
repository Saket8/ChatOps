@echo off
REM ChatOps CLI - Main Entry Point
REM This allows you to run 'chatops' directly to access all commands

python -m poetry run python -m chatops_cli %* 