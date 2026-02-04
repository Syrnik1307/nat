# Быстрый деплой фронтенда с правильными правами
# Использование: .\deploy_frontend.ps1

$ErrorActionPreference = "Stop"

Write-Host ""
Write-Host "=== ДЕПЛОЙ ФРОНТЕНДА ===" -ForegroundColor Cyan
Write-Host ""

# 1. Проверяем что билд существует
$buildPath = "c:\Users\User\Desktop\nat\frontend\build"
if (-not (Test-Path $buildPath)) {
    Write-Host "Билд не найден! Сначала запусти: cd frontend && npm run build" -ForegroundColor Red
    exit 1
}

# 2. Проверяем index.html
$indexHtml = Get-Content "$buildPath\index.html" -Raw
if ($indexHtml -match 'main\.([a-f0-9]+)\.js') {
    $jsHash = $Matches[1]
    Write-Host "Билд найден: main.$jsHash.js" -ForegroundColor Green
} else {
    Write-Host "Не могу найти main.*.js в index.html!" -ForegroundColor Red
    exit 1
}

# 3. Копируем на сервер
Write-Host "Копирую файлы на сервер..." -ForegroundColor Yellow
scp -r "$buildPath\*" "tp:/var/www/teaching-panel/frontend/build/"

if ($LASTEXITCODE -ne 0) {
    Write-Host "SCP завершился с ошибкой!" -ForegroundColor Red
    exit 1
}

# 4. КРИТИЧНО: Исправляем права (иначе nginx не сможет читать)
Write-Host "Исправляю права доступа..." -ForegroundColor Yellow
ssh tp "sudo chown -R www-data:www-data /var/www/teaching-panel/frontend/build && sudo chmod -R 755 /var/www/teaching-panel/frontend/build"

if ($LASTEXITCODE -ne 0) {
    Write-Host "Не удалось исправить права!" -ForegroundColor Red
    exit 1
}

# 5. Проверяем что сайт работает
Write-Host "Проверяю сайт..." -ForegroundColor Yellow
Start-Sleep -Seconds 2

$status = curl -s -o /dev/null -w "%{http_code}" https://lectiospace.ru/
if ($status -eq "200") {
    Write-Host ""
    Write-Host "=== ДЕПЛОЙ УСПЕШЕН ===" -ForegroundColor Green
    Write-Host "Сайт работает (HTTP $status)" -ForegroundColor Green
} else {
    Write-Host ""
    Write-Host "ВНИМАНИЕ: Сайт вернул код $status" -ForegroundColor Yellow
    Write-Host "Проверь: https://lectiospace.ru/" -ForegroundColor Yellow
}

Write-Host ""
