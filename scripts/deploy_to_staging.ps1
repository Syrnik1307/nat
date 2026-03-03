#!/usr/bin/env pwsh
<#
.SYNOPSIS
    Deploy current staging branch to stage.lectiospace.ru
.DESCRIPTION
    Full deploy: backend code + pip install + migrate + frontend build + upload + restart + smoke test
    Production (lectiospace.ru) is NOT affected.
#>

$ErrorActionPreference = "Stop"
Set-Location "$PSScriptRoot\.."

Write-Host "============================================" -ForegroundColor Cyan
Write-Host "  Deploy to STAGING (stage.lectiospace.ru)" -ForegroundColor Cyan
Write-Host "============================================" -ForegroundColor Cyan
Write-Host ""

# ── 0. Pre-checks ──
$branch = git rev-parse --abbrev-ref HEAD
if ($branch -ne "staging") {
    Write-Host "WARNING: Current branch is '$branch', expected 'staging'" -ForegroundColor Yellow
    $confirm = Read-Host "Continue anyway? (y/N)"
    if ($confirm -ne "y") { exit 1 }
}

# Tenant safety check
$tenantFiles = git diff --name-only HEAD~5..HEAD | Select-String "tenant"
if ($tenantFiles) {
    Write-Host "BLOCKED: Tenant code detected in recent commits!" -ForegroundColor Red
    $tenantFiles | ForEach-Object { Write-Host "  $_" -ForegroundColor Red }
    exit 1
}

Write-Host "[OK] Pre-checks passed (branch: $branch)" -ForegroundColor Green
Write-Host ""

# ── 1. Deploy backend code ──
Write-Host "[1/7] Deploying backend code..." -ForegroundColor Green
ssh tp @"
cd /var/www/teaching-panel-stage/teaching_panel && \
git fetch origin staging && \
git reset --hard origin/staging && \
echo 'GIT_RESET_OK'
"@
if ($LASTEXITCODE -ne 0) { Write-Host "FAILED: git reset" -ForegroundColor Red; exit 1 }

# ── 2. Install dependencies ──
Write-Host "[2/7] Installing Python dependencies..." -ForegroundColor Green
ssh tp @"
cd /var/www/teaching-panel-stage/teaching_panel && \
source ../venv/bin/activate && \
pip install -r requirements.txt --quiet 2>&1 | tail -3 && \
echo 'PIP_OK'
"@

# ── 3. Run migrations ──
Write-Host "[3/7] Running migrations..." -ForegroundColor Green
ssh tp @"
cd /var/www/teaching-panel-stage/teaching_panel && \
source ../venv/bin/activate && \
DJANGO_SETTINGS_MODULE=teaching_panel.settings_staging python manage.py migrate --noinput 2>&1 | tail -5 && \
echo 'MIGRATE_OK'
"@

# ── 4. Collect static ──
Write-Host "[4/7] Collecting static files..." -ForegroundColor Green
ssh tp @"
cd /var/www/teaching-panel-stage/teaching_panel && \
source ../venv/bin/activate && \
DJANGO_SETTINGS_MODULE=teaching_panel.settings_staging python manage.py collectstatic --noinput 2>&1 | tail -3 && \
echo 'STATIC_OK'
"@

# ── 5. Build frontend ──
Write-Host "[5/7] Building frontend (CRA)..." -ForegroundColor Green
Push-Location frontend
npm run build 2>&1 | Select-Object -Last 5
if ($LASTEXITCODE -ne 0) {
    Pop-Location
    Write-Host "FAILED: frontend build" -ForegroundColor Red
    exit 1
}
Pop-Location

if (-not (Test-Path "frontend/build/index.html")) {
    Write-Host "FAILED: frontend/build/index.html not found" -ForegroundColor Red
    exit 1
}
$fileCount = (Get-ChildItem "frontend/build" -Recurse -File).Count
Write-Host "  -> Build OK: $fileCount files" -ForegroundColor Green

# ── 6. Upload frontend ──
Write-Host "[6/7] Uploading frontend to staging..." -ForegroundColor Green
ssh tp "sudo mkdir -p /var/www/teaching-panel-stage/frontend/build"
ssh tp "sudo cp -r /var/www/teaching-panel-stage/frontend/build /var/www/teaching-panel-stage/frontend/build.bak.$(Get-Date -Format 'yyyyMMdd_HHmmss') 2>/dev/null; true"

scp -r frontend/build/* tp:/tmp/stage-frontend-build/
ssh tp @"
sudo rm -rf /var/www/teaching-panel-stage/frontend/build/* && \
sudo cp -r /tmp/stage-frontend-build/* /var/www/teaching-panel-stage/frontend/build/ && \
sudo chown -R www-data:www-data /var/www/teaching-panel-stage/frontend/build/ && \
rm -rf /tmp/stage-frontend-build/ && \
echo 'UPLOAD_OK'
"@

# ── 7. Restart & smoke test ──
Write-Host "[7/7] Restarting staging service..." -ForegroundColor Green
ssh tp "sudo systemctl restart teaching_panel_stage 2>&1; sleep 2; sudo systemctl is-active teaching_panel_stage"

Write-Host ""
Write-Host "Smoke test..." -ForegroundColor Green
$health = ssh tp "curl -s -o /dev/null -w '%{http_code}' https://stage.lectiospace.ru/api/health/"
$page = ssh tp "curl -s -o /dev/null -w '%{http_code}' https://stage.lectiospace.ru/"

Write-Host "  API health: $health" -ForegroundColor $(if ($health -eq "200") { "Green" } else { "Red" })
Write-Host "  Frontend:   $page" -ForegroundColor $(if ($page -eq "200") { "Green" } else { "Red" })

if ($health -eq "200" -and $page -eq "200") {
    Write-Host ""
    Write-Host "STAGING DEPLOY SUCCESS!" -ForegroundColor Green
    Write-Host "Check: https://stage.lectiospace.ru/" -ForegroundColor Cyan
} else {
    Write-Host ""
    Write-Host "WARNING: Smoke test issues. Check logs:" -ForegroundColor Yellow
    Write-Host "  ssh tp 'sudo journalctl -u teaching_panel_stage -n 30 --no-pager'" -ForegroundColor Yellow
}
