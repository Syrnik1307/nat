# Teaching Panel Production Deployment Script (PowerShell)
# Deploy without password using SSH configured without password
# Usage: .\deploy_final.ps1

param(
    [string]$SSHAlias = "tp",
    [switch]$NoRestart = $false
)

# Color codes
$Green = [System.ConsoleColor]::Green
$Blue = [System.ConsoleColor]::Blue
$Yellow = [System.ConsoleColor]::Yellow
$Red = [System.ConsoleColor]::Red

function Write-ColorOutput {
    param(
        [string]$Message,
        [System.ConsoleColor]$Color = $Green
    )
    Write-Host $Message -ForegroundColor $Color
}

# Header
Write-Host "========================================" -ForegroundColor $Blue
Write-Host "Teaching Panel Production Deployment" -ForegroundColor $Blue
Write-Host "========================================" -ForegroundColor $Blue
Write-Host ""

Write-ColorOutput "🚀 Начинаем деплой Teaching Panel..." $Yellow
Write-Host ""

# Build deployment commands
$deploymentCommands = @"
cd /var/www/teaching_panel && \
echo '📥 Шаг 1: Обновление кода из Git...' && \
sudo -u www-data git pull origin main && \
cd teaching_panel && \
source ../venv/bin/activate && \
echo '📦 Шаг 2: Установка зависимостей...' && \
pip install -r requirements.txt --quiet && \
echo '🔄 Шаг 3: Запуск миграций БД...' && \
python manage.py migrate --noinput && \
echo '📄 Шаг 4: Сбор статических файлов...' && \
python manage.py collectstatic --noinput --clear && \
echo '🔄 Шаг 5: Перезапуск сервисов...' && \
sudo systemctl restart teaching_panel && \
sudo systemctl restart nginx && \
echo '✔️ Шаг 6: Проверка статуса...' && \
sudo systemctl status teaching_panel --no-pager && \
echo '✅ ДЕПЛОЙ ЗАВЕРШЕН УСПЕШНО!'
"@

try {
    Write-ColorOutput "🔌 Подключаюсь к серверу: $SSHAlias" $Yellow
    
    # Execute deployment via SSH
    $result = ssh $SSHAlias $deploymentCommands
    
    Write-Host ""
    Write-Host "========================================" -ForegroundColor $Blue
    Write-ColorOutput "✅ ДЕПЛОЙ УСПЕШНО ЗАВЕРШЕН!" $Green
    Write-Host "========================================" -ForegroundColor $Blue
    Write-Host ""
    
    Write-ColorOutput "Проверка доступности:" $Blue
    Write-Host "  - API: https://teaching-panel.ru/api/"
    Write-Host "  - Frontend: https://teaching-panel.ru/"
    Write-Host ""
    
    Write-ColorOutput "Полезные команды:" $Blue
    Write-Host "  - Логи: ssh $SSHAlias 'sudo journalctl -u teaching_panel -f'"
    Write-Host "  - Статус: ssh $SSHAlias 'sudo systemctl status teaching_panel'"
    Write-Host "  - Перезапуск: ssh $SSHAlias 'sudo systemctl restart teaching_panel'"
    Write-Host ""
    
    Write-Host "Вывод команд:" -ForegroundColor $Blue
    Write-Host $result
    
    exit 0
}
catch {
    Write-Host ""
    Write-Host "========================================" -ForegroundColor $Red
    Write-ColorOutput "❌ ОШИБКА ПРИ ДЕПЛОЕ" $Red
    Write-Host "========================================" -ForegroundColor $Red
    Write-Host ""
    Write-ColorOutput "Ошибка: $_" $Red
    exit 1
}
