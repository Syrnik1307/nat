# Safe local checks before deploy/push.
# Usage:
#   pwsh -NoProfile -ExecutionPolicy Bypass -File scripts\run_checks.ps1
# Optional:
#   $env:RUN_FRONTEND_CHECKS='1'  # also run `npm run build`
#   $env:SKIP_DEPLOY_CHECK='1'    # skip `manage.py check --deploy`

$ErrorActionPreference = 'Stop'

function Invoke-External {
    param(
        [Parameter(Mandatory = $true)][string]$FilePath,
        [Parameter(Mandatory = $true)][string[]]$Arguments
    )

    & $FilePath @Arguments
    if ($LASTEXITCODE -ne 0) {
        throw "Command failed ($LASTEXITCODE): $FilePath $($Arguments -join ' ')"
    }
}

function Resolve-BackendPython([string]$RepoRoot) {
    $candidates = @(
        (Join-Path $RepoRoot 'venv\Scripts\python.exe'),
        (Join-Path $RepoRoot '.venv\Scripts\python.exe')
    )

    foreach ($candidate in $candidates) {
        if (Test-Path $candidate) {
            return $candidate
        }
    }

    return 'python'
}

function Write-Step([string]$Message) {
    Write-Host $Message -ForegroundColor Cyan
}

function Ensure-Env([string]$Name, [string]$Value) {
    $existing = (Get-Item -Path ("env:{0}" -f $Name) -ErrorAction SilentlyContinue).Value
    if ([string]::IsNullOrEmpty($existing)) {
        Set-Item -Path ("env:{0}" -f $Name) -Value $Value
    }
}

$root = Resolve-Path (Join-Path $PSScriptRoot '..')
$backendPython = Resolve-BackendPython $root

Write-Step "Backend: Django checks"
Push-Location (Join-Path $root 'teaching_panel')
try {
    # Provide safe defaults so `check --deploy` is meaningful locally.
    Ensure-Env 'SECRET_KEY' 'ci-local-secret-key-please-change-1234567890-abcdefghijklmnopqrstuvwxyz'
    Ensure-Env 'DEBUG' 'False'
    Ensure-Env 'ALLOWED_HOSTS' 'localhost,127.0.0.1'
    Ensure-Env 'SECURE_SSL_REDIRECT' 'True'
    Ensure-Env 'SESSION_COOKIE_SECURE' 'True'
    Ensure-Env 'CSRF_COOKIE_SECURE' 'True'
    Ensure-Env 'SECURE_HSTS_SECONDS' '60'
    Ensure-Env 'SECURE_HSTS_INCLUDE_SUBDOMAINS' 'True'
    Ensure-Env 'SECURE_HSTS_PRELOAD' 'True'
    Ensure-Env 'RECAPTCHA_ENABLED' 'False'
    Ensure-Env 'RECAPTCHA_PUBLIC_KEY' 'disabled'
    Ensure-Env 'RECAPTCHA_PRIVATE_KEY' 'disabled'
    Ensure-Env 'USE_IN_MEMORY_CELERY' '1'
    Ensure-Env 'ZOOM_ACCOUNT_ID' 'disabled'
    Ensure-Env 'ZOOM_CLIENT_ID' 'disabled'
    Ensure-Env 'ZOOM_CLIENT_SECRET' 'disabled'

    Invoke-External $backendPython @('manage.py', 'check')
    if ($env:SKIP_DEPLOY_CHECK -ne '1') {
        Invoke-External $backendPython @('manage.py', 'check', '--deploy', '--fail-level', 'WARNING')
    }
}
finally {
    Pop-Location
}

if ($env:RUN_FRONTEND_CHECKS -eq '1') {
    Write-Step "Frontend: build"
    Push-Location (Join-Path $root 'frontend')
    try {
        if (-not (Test-Path (Join-Path (Get-Location) 'node_modules'))) {
            throw "node_modules not found. Run 'npm ci' (or 'npm install') in frontend/ before enabling RUN_FRONTEND_CHECKS=1."
        }
        else {
            Invoke-External 'npm' @('run', 'build')
        }
    }
    finally {
        Pop-Location
    }
}

Write-Host "OK" -ForegroundColor Green
