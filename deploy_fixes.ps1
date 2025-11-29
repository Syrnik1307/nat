# ========================================
# Быстрый деплой исправлений на сервер
# ========================================
# ⚠️ DEPRECATED: Используйте auto_deploy.ps1
# ========================================

Write-Host ""
Write-Host "⚠️ РЕКОМЕНДАЦИЯ: Используйте auto_deploy.ps1 для деплоя" -ForegroundColor Yellow
Write-Host "Нажмите Enter для продолжения или Ctrl+C для выхода" -ForegroundColor Gray
Read-Host

Write-Host ""
Write-Host "🚀 Деплой исправлений на сервер" -ForegroundColor Cyan
Write-Host "=================================" -ForegroundColor Cyan
Write-Host ""

$SERVER = "root@72.56.81.163"
$LOCAL_DIR = "c:\Users\User\Desktop\nat"
$REMOTE_DIR = "/var/www/teaching_panel"

# Файлы для копирования
$files = @(
    "frontend/src/components/NavBarNew.js",
    "frontend/src/components/TeacherHomePage.js",
    "frontend/package.json"
)

Write-Host "📦 Копируем исправленные файлы на сервер..." -ForegroundColor Yellow
Write-Host ""

foreach ($file in $files) {
    $localPath = Join-Path $LOCAL_DIR $file
    $remotePath = "${REMOTE_DIR}/${file}" -replace '\\', '/'
    $remoteDir = Split-Path $remotePath -Parent
    
    Write-Host "  → $file" -ForegroundColor Gray
    
    # Создаём директорию на сервере если нужно
    ssh $SERVER "mkdir -p $remoteDir"
    
    # Копируем файл
    scp $localPath "${SERVER}:${remotePath}"
}

Write-Host ""
Write-Host "✅ Файлы скопированы!" -ForegroundColor Green
Write-Host ""

# Пересобираем фронтенд на сервере
Write-Host "⚛️ Пересборка React фронтенда на сервере..." -ForegroundColor Yellow

ssh $SERVER @"
cd $REMOTE_DIR/frontend && 
npm install && 
npm run build && 
echo '✅ Фронтенд собран!'
"@

Write-Host ""
Write-Host "🔄 Перезапуск Nginx..." -ForegroundColor Yellow

ssh $SERVER "sudo systemctl restart nginx && echo '✅ Nginx перезапущен!'"

Write-Host ""
Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor Green
Write-Host "✅ ДЕПЛОЙ ЗАВЕРШЁН!" -ForegroundColor Green
Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor Green
Write-Host ""
Write-Host "🌐 Проверьте сайт: http://72.56.81.163" -ForegroundColor Cyan
Write-Host ""
Write-Host "📋 Полезные команды:" -ForegroundColor Yellow
Write-Host "  • Логи Nginx: ssh $SERVER 'sudo tail -f /var/log/nginx/teaching_panel_error.log'" -ForegroundColor Gray
Write-Host "  • Статус Django: ssh $SERVER 'sudo systemctl status teaching_panel'" -ForegroundColor Gray
Write-Host ""
