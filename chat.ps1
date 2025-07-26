# ChatOps CLI - Quick Start PowerShell Script
# This allows you to run 'chat' directly to start interactive mode

param(
    [Parameter(ValueFromRemainingArguments=$true)]
    [string[]]$Arguments
)

# Run the chat command with any additional arguments
python -m poetry run python -m chatops_cli chat @Arguments 