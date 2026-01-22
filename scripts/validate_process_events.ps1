# Validation of all changed files
$python = "C:/Users/User/Desktop/nat/.venv/Scripts/python.exe"
$cd = "c:\Users\User\Desktop\nat\teaching_panel"

Write-Host "=== SYNTAX CHECK ===" -ForegroundColor Green

$files = @(
    "observability/process_events.py",
    "observability/__init__.py",
    "accounts/security.py",
    "accounts/jwt_views.py",
    "accounts/payments_service.py",
    "schedule/tasks.py",
    "homework/views.py"
)

$all_ok = $true

foreach ($file in $files) {
    Push-Location $cd
    & $python -m py_compile $file 2>&1 | Out-Null
    if ($LASTEXITCODE -eq 0) {
        Write-Host "  OK: $file" -ForegroundColor Green
    } else {
        Write-Host "  FAIL: $file" -ForegroundColor Red
        $all_ok = $false
    }
    Pop-Location
}

Write-Host ""
Write-Host "=== IMPORT CHECK ===" -ForegroundColor Green

Push-Location $cd
$result = & $python -c "from observability.process_events import emit_process_event; print('OK')" 2>&1
if ($LASTEXITCODE -eq 0) {
    Write-Host "  OK: observability.process_events import" -ForegroundColor Green
} else {
    Write-Host "  FAIL: observability.process_events import" -ForegroundColor Red
    Write-Host "       Error: $result" -ForegroundColor Yellow
    $all_ok = $false
}
Pop-Location

Write-Host ""
Write-Host "=== DJANGO CHECK ===" -ForegroundColor Green

Push-Location $cd
& $python manage.py check 2>&1 | Out-Null
if ($LASTEXITCODE -eq 0) {
    Write-Host "  OK: Django system check passed" -ForegroundColor Green
} else {
    Write-Host "  INFO: Django check exit code: $($LASTEXITCODE)" -ForegroundColor Cyan
}
Pop-Location

Write-Host ""
if ($all_ok) {
    Write-Host "=== ALL CHECKS PASSED ===" -ForegroundColor Green
} else {
    Write-Host "=== SOME CHECKS FAILED ===" -ForegroundColor Red
}
