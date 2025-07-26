# ChatOps CLI - Main Entry Point PowerShell Script
# This allows you to run 'chatops' directly to access all commands

param(
    [Parameter(ValueFromRemainingArguments=$true)]
    [string[]]$Arguments
)

# Run the main CLI with any arguments
python -m poetry run python -m chatops_cli @Arguments 