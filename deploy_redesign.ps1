# ========================================
# Deploy UI Redesign to Production Server
# ========================================
# ⚠️ DEPRECATED: Используйте auto_deploy.ps1
# ========================================

Write-Host ""
Write-Host "⚠️ ВНИМАНИЕ: Этот скрипт устарел!" -ForegroundColor Yellow
Write-Host ""
Write-Host "Используйте новый улучшенный скрипт для деплоя:" -ForegroundColor Green
Write-Host "  .\auto_deploy.ps1" -ForegroundColor Cyan
Write-Host ""
Write-Host "Он предоставляет:" -ForegroundColor Yellow
Write-Host "  ✅ Интерактивное меню" -ForegroundColor White
Write-Host "  ✅ Полный деплой" -ForegroundColor White
Write-Host "  ✅ Частичные обновления (только фронтенд/бэкенд)" -ForegroundColor White
Write-Host "  ✅ Мониторинг и логи" -ForegroundColor White
Write-Host "  ✅ Обслуживание системы" -ForegroundColor White
Write-Host ""
Write-Host "Запустить новый скрипт? (y/n)" -ForegroundColor Yellow
$launch = Read-Host

if ($launch -eq 'y') {
    $scriptPath = Join-Path $PSScriptRoot "auto_deploy.ps1"
    if (Test-Path $scriptPath) {
        & $scriptPath
    } else {
        Write-Host "❌ Файл auto_deploy.ps1 не найден в $PSScriptRoot" -ForegroundColor Red
    }
} else {
    Write-Host "👋 Выход" -ForegroundColor Gray
}
