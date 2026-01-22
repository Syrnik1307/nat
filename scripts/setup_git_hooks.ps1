# Enables local git hooks for this repo (safe, opt-in).
# Usage:
#   pwsh -NoProfile -ExecutionPolicy Bypass -File scripts\setup_git_hooks.ps1

$ErrorActionPreference = 'Stop'

$root = Resolve-Path (Join-Path $PSScriptRoot '..')
Push-Location $root
try {
    git config core.hooksPath .githooks
    Write-Host "Configured git hooks: core.hooksPath=.githooks" -ForegroundColor Green
    Write-Host "Pre-push will run backend checks. Set SKIP_HOOKS=1 to bypass." -ForegroundColor Yellow
}
finally {
    Pop-Location
}
