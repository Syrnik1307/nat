#!/usr/bin/env pwsh
# Deploy CSP config to nginx

Write-Host "=== STEP 1: Copy file ===" -ForegroundColor Cyan
scp c:\Users\User\Desktop\nat\nginx_lectiospace_new.conf root@lectiospace.ru:/etc/nginx/sites-enabled/lectiospace.ru
if ($LASTEXITCODE -eq 0) { Write-Host "OK" -ForegroundColor Green } else { Write-Host "FAILED" -ForegroundColor Red }

Write-Host "`n=== STEP 2: Test nginx config ===" -ForegroundColor Cyan
ssh root@lectiospace.ru "nginx -t 2>&1"
if ($LASTEXITCODE -eq 0) { Write-Host "OK" -ForegroundColor Green } else { Write-Host "FAILED" -ForegroundColor Red }

Write-Host "`n=== STEP 3: Reload nginx ===" -ForegroundColor Cyan
ssh root@lectiospace.ru "systemctl reload nginx 2>&1"
if ($LASTEXITCODE -eq 0) { Write-Host "OK" -ForegroundColor Green } else { Write-Host "FAILED" -ForegroundColor Red }

Write-Host "`n=== STEP 4: Check CSP header ===" -ForegroundColor Cyan
$headers = ssh root@lectiospace.ru "curl -sI https://lectiospace.ru/"
$headers | ForEach-Object { Write-Host $_ }
if ($headers -match "Content-Security-Policy") {
    Write-Host "`nCSP HEADER FOUND!" -ForegroundColor Green
} else {
    Write-Host "`nCSP HEADER NOT FOUND!" -ForegroundColor Red
}
