# ChatOps CLI - Global Chat Entry Point
# This script allows you to run 'chat' from anywhere

param(
    [Parameter(ValueFromRemainingArguments=$true)]
    [string[]]$Arguments
)

# Get the ChatOps project root (this script's location)
$ChatOpsRoot = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)

# Change to the ChatOps directory and run the chat command
Push-Location $ChatOpsRoot
try {
    python -m poetry run python -m chatops_cli chat @Arguments
}
finally {
    Pop-Location
}
