# ChatOps CLI - Global Setup Script
# This script adds ChatOps CLI to your system PATH for global access

param(
    [switch]$Uninstall,
    [switch]$Force
)

# Get the current script directory (ChatOps project root)
$ChatOpsRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$ChatOpsScripts = Join-Path $ChatOpsRoot "scripts"

# Create scripts directory if it doesn't exist
if (!(Test-Path $ChatOpsScripts)) {
    New-Item -ItemType Directory -Path $ChatOpsScripts -Force | Out-Null
    Write-Host "Created scripts directory: $ChatOpsScripts" -ForegroundColor Green
}

# Create the global chatops script
$GlobalChatOpsScript = Join-Path $ChatOpsScripts "chatops.ps1"
$GlobalChatScript = Join-Path $ChatOpsScripts "chat.ps1"

# Create the main chatops script
$ChatOpsScriptContent = @"
# ChatOps CLI - Global Entry Point
# This script allows you to run 'chatops' from anywhere

param(
    [Parameter(ValueFromRemainingArguments=`$true)]
    [string[]]`$Arguments
)

# Get the ChatOps project root (this script's location)
`$ChatOpsRoot = Split-Path -Parent (Split-Path -Parent `$MyInvocation.MyCommand.Path)

# Change to the ChatOps directory and run the command
Push-Location `$ChatOpsRoot
try {
    python -m poetry run python -m chatops_cli @Arguments
}
finally {
    Pop-Location
}
"@

# Create the chat script
$ChatScriptContent = @"
# ChatOps CLI - Global Chat Entry Point
# This script allows you to run 'chat' from anywhere

param(
    [Parameter(ValueFromRemainingArguments=`$true)]
    [string[]]`$Arguments
)

# Get the ChatOps project root (this script's location)
`$ChatOpsRoot = Split-Path -Parent (Split-Path -Parent `$MyInvocation.MyCommand.Path)

# Change to the ChatOps directory and run the chat command
Push-Location `$ChatOpsRoot
try {
    python -m poetry run python -m chatops_cli chat @Arguments
}
finally {
    Pop-Location
}
"@

if ($Uninstall) {
    Write-Host "Uninstalling ChatOps CLI from global PATH..." -ForegroundColor Yellow
    
    # Remove from PATH
    $CurrentPath = [Environment]::GetEnvironmentVariable("PATH", "User")
    $NewPath = ($CurrentPath -split ';' | Where-Object { $_ -notlike "*$ChatOpsScripts*" }) -join ';'
    [Environment]::SetEnvironmentVariable("PATH", $NewPath, "User")
    
    Write-Host "ChatOps CLI removed from global PATH" -ForegroundColor Green
    Write-Host "You may need to restart your terminal for changes to take effect" -ForegroundColor Yellow
    exit 0
}

# Check if already installed
$CurrentPath = [Environment]::GetEnvironmentVariable("PATH", "User")
if ($CurrentPath -like "*$ChatOpsScripts*" -and -not $Force) {
    Write-Host "ChatOps CLI is already installed globally!" -ForegroundColor Green
    Write-Host "You can now use 'chatops' and 'chat' commands from anywhere" -ForegroundColor Green
    Write-Host ""
    Write-Host "Usage examples:" -ForegroundColor Cyan
    Write-Host "  chatops --help" -ForegroundColor White
    Write-Host "  chatops plugins --list" -ForegroundColor White
    Write-Host "  chat" -ForegroundColor White
    Write-Host "  chat --context 'Windows server'" -ForegroundColor White
    exit 0
}

Write-Host "Setting up ChatOps CLI for global access..." -ForegroundColor Yellow

# Create the scripts
Set-Content -Path $GlobalChatOpsScript -Value $ChatOpsScriptContent -Encoding UTF8
Set-Content -Path $GlobalChatScript -Value $ChatScriptContent -Encoding UTF8

# Make scripts executable
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser -Force | Out-Null

# Add to PATH
$CurrentPath = [Environment]::GetEnvironmentVariable("PATH", "User")
if ($CurrentPath -notlike "*$ChatOpsScripts*") {
    $NewPath = "$CurrentPath;$ChatOpsScripts"
    [Environment]::SetEnvironmentVariable("PATH", $NewPath, "User")
}

Write-Host "✅ ChatOps CLI installed globally!" -ForegroundColor Green
Write-Host ""
Write-Host "You can now use these commands from anywhere:" -ForegroundColor Cyan
Write-Host "  chatops --help" -ForegroundColor White
Write-Host "  chatops plugins --list" -ForegroundColor White
Write-Host "  chat" -ForegroundColor White
Write-Host "  chat --context 'Windows server'" -ForegroundColor White
Write-Host ""
Write-Host "Note: You may need to restart your terminal or run 'refreshenv' for changes to take effect" -ForegroundColor Yellow
Write-Host ""
Write-Host "To uninstall, run: .\setup-global.ps1 -Uninstall" -ForegroundColor Gray 