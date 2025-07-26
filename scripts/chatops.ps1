# ChatOps CLI - Global Entry Point
# This script allows you to run 'chatops' from anywhere

param(
    [Parameter(ValueFromRemainingArguments=$true)]
    [string[]]$Arguments
)

# Get the ChatOps project root (this script's location)
$ChatOpsRoot = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)

# Change to the ChatOps directory and run the command
Push-Location $ChatOpsRoot
try {
    python -m poetry run python -m chatops_cli @Arguments
}
finally {
    Pop-Location
}
