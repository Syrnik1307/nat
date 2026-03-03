#!/usr/bin/env pwsh
<#
.SYNOPSIS
    Promote staging branch to new-prod (production-ready)
.DESCRIPTION
    Merges staging into new-prod with safety checks.
    Does NOT deploy to production - run deploy_to_production.ps1 after this.
#>

$ErrorActionPreference = "Stop"
Set-Location "$PSScriptRoot\.."

Write-Host "============================================" -ForegroundColor Cyan
Write-Host "  Promote STAGING -> NEW-PROD" -ForegroundColor Cyan
Write-Host "============================================" -ForegroundColor Cyan
Write-Host ""

# ── 1. Check staging health ──
Write-Host "[1/5] Checking staging health..." -ForegroundColor Green
$health = ssh tp "curl -s -o /dev/null -w '%{http_code}' https://stage.lectiospace.ru/api/health/ 2>/dev/null"
if ($health -ne "200") {
    Write-Host "BLOCKED: Staging is unhealthy (HTTP $health)" -ForegroundColor Red
    Write-Host "Fix staging first, then re-run this script." -ForegroundColor Red
    exit 1
}
Write-Host "  Staging healthy (HTTP $health)" -ForegroundColor Green

# ── 2. Show diff ──
Write-Host ""
Write-Host "[2/5] Changes that will go to prod:" -ForegroundColor Green
Write-Host "--- Commits ---" -ForegroundColor Yellow
git log new-prod..staging --oneline | Select-Object -First 20

Write-Host ""
Write-Host "--- Files changed ---" -ForegroundColor Yellow
$changedFiles = git diff --name-only new-prod..staging
$changedFiles | ForEach-Object { Write-Host "  $_" }
$fileCount = ($changedFiles | Measure-Object).Count
Write-Host "  ($fileCount files)" -ForegroundColor Gray

# ── 3. Scan migrations for dangerous ops ──
Write-Host ""
Write-Host "[3/5] Scanning new migrations for dangerous operations..." -ForegroundColor Green
$newMigrations = git diff --name-only new-prod..staging | Select-String "migrations/\d"
$dangerous = @()
foreach ($mig in $newMigrations) {
    $content = git show "staging:$mig" 2>$null
    if ($content -match "RemoveField|DeleteModel|DROP|TRUNCATE|RunSQL.*DELETE") {
        $dangerous += $mig
    }
}
if ($dangerous.Count -gt 0) {
    Write-Host "WARNING: Dangerous migrations found!" -ForegroundColor Red
    $dangerous | ForEach-Object { Write-Host "  $_" -ForegroundColor Red }
    Write-Host "Review these migrations carefully before proceeding." -ForegroundColor Yellow
    $confirm = Read-Host "Continue despite dangerous migrations? (yes/N)"
    if ($confirm -ne "yes") { exit 1 }
} else {
    Write-Host "  No dangerous migrations detected." -ForegroundColor Green
}

# ── 4. Tenant code check ──
Write-Host ""
Write-Host "[4/5] Tenant code safety check..." -ForegroundColor Green
$tenantInDiff = git diff new-prod..staging -- "*.py" | Select-String "tenant|TenantMiddleware|TenantModelMixin"
if ($tenantInDiff) {
    Write-Host "BLOCKED: Tenant code detected in diff!" -ForegroundColor Red
    exit 1
}
Write-Host "  No tenant code found." -ForegroundColor Green

# ── 5. Merge ──
Write-Host ""
Write-Host "[5/5] Ready to merge staging -> new-prod" -ForegroundColor Green
$date = Get-Date -Format "yyyy-MM-dd HH:mm"
Write-Host "  Merge message: promote: staging -> prod $date" -ForegroundColor Gray
Write-Host ""
$confirm = Read-Host "Proceed with merge? (y/N)"
if ($confirm -ne "y") {
    Write-Host "Aborted." -ForegroundColor Yellow
    exit 0
}

git checkout new-prod
if ($LASTEXITCODE -ne 0) { Write-Host "FAILED: checkout new-prod" -ForegroundColor Red; exit 1 }

git merge staging --no-ff -m "promote: staging -> prod $date"
if ($LASTEXITCODE -ne 0) {
    Write-Host "FAILED: merge had conflicts. Resolve manually." -ForegroundColor Red
    exit 1
}

git push origin new-prod
if ($LASTEXITCODE -ne 0) { Write-Host "FAILED: push" -ForegroundColor Red; exit 1 }

Write-Host ""
Write-Host "PROMOTE SUCCESS!" -ForegroundColor Green
Write-Host "staging merged into new-prod and pushed." -ForegroundColor Green
Write-Host ""
Write-Host "Next step: .\deploy_to_production.ps1" -ForegroundColor Cyan
