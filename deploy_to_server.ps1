# ========================================
# Скрипт деплоя Teaching Panel на сервер
# ========================================

Write-Host ""
Write-Host "🚀 Teaching Panel - Deploy to Production Server" -ForegroundColor Cyan
Write-Host "=================================================" -ForegroundColor Cyan
Write-Host ""

$SERVER = "root@72.56.81.163"
$PROJECT_DIR = "c:\Users\User\Desktop\nat"
$REMOTE_PATH = "/var/www/teaching_panel"

# Функция для выполнения команд на сервере
function Invoke-RemoteCommand {
    param([string]$Command)
    Write-Host "📡 Executing on server..." -ForegroundColor Yellow
    ssh $SERVER $Command
}

# Меню
Write-Host "Выберите действие:" -ForegroundColor Green
Write-Host "1 - Полный деплой (код + сборка фронтенда + перезапуск)" -ForegroundColor White
Write-Host "2 - Только обновить бэкенд (Django)" -ForegroundColor White
Write-Host "3 - Только обновить фронтенд" -ForegroundColor White
Write-Host "4 - Только перезапустить сервисы" -ForegroundColor White
Write-Host "5 - Применить миграции БД" -ForegroundColor White
Write-Host "6 - Посмотреть логи" -ForegroundColor White
Write-Host "7 - Статус сервисов" -ForegroundColor White
Write-Host "0 - Выход" -ForegroundColor White
Write-Host ""

$choice = Read-Host "Ваш выбор"

switch ($choice) {
    "1" {
        Write-Host ""
        Write-Host "🔄 ПОЛНЫЙ ДЕПЛОЙ" -ForegroundColor Cyan
        Write-Host "==================" -ForegroundColor Cyan
        
        # 1. Обновить код из Git
        Write-Host ""
        Write-Host "📥 Шаг 1/5: Обновление кода из Git..." -ForegroundColor Yellow
        Invoke-RemoteCommand "cd $REMOTE_PATH && git pull origin main"
        
        # 2. Обновить Python зависимости
        Write-Host ""
        Write-Host "📦 Шаг 2/5: Обновление Python зависимостей..." -ForegroundColor Yellow
        Invoke-RemoteCommand "cd $REMOTE_PATH && source venv/bin/activate && pip install -r teaching_panel/requirements-production.txt"
        
        # 3. Применить миграции
        Write-Host ""
        Write-Host "🗄️ Шаг 3/5: Применение миграций БД..." -ForegroundColor Yellow
        Invoke-RemoteCommand "cd $REMOTE_PATH && source venv/bin/activate && python teaching_panel/manage.py migrate"
        
        # 4. Собрать статику Django
        Write-Host ""
        Write-Host "📁 Шаг 4/5: Сборка статики Django..." -ForegroundColor Yellow
        Invoke-RemoteCommand "cd $REMOTE_PATH && source venv/bin/activate && python teaching_panel/manage.py collectstatic --noinput"
        
        # 5. Собрать React фронтенд
        Write-Host ""
        Write-Host "⚛️ Шаг 5/5: Сборка React фронтенда..." -ForegroundColor Yellow
        Invoke-RemoteCommand "cd $REMOTE_PATH/frontend && npm install && npm run build"
        
        # 6. Перезапустить сервисы
        Write-Host ""
        Write-Host "🔄 Перезапуск сервисов..." -ForegroundColor Yellow
        Invoke-RemoteCommand "sudo systemctl restart teaching_panel celery celery-beat nginx"
        
        Write-Host ""
        Write-Host "✅ ДЕПЛОЙ ЗАВЕРШЁН!" -ForegroundColor Green
        Write-Host "Проверьте сайт: http://72.56.81.163" -ForegroundColor Cyan
    }
    
    "2" {
        Write-Host ""
        Write-Host "🐍 ОБНОВЛЕНИЕ БЭКЕНДА" -ForegroundColor Cyan
        
        Invoke-RemoteCommand "cd $REMOTE_PATH && git pull origin main && source venv/bin/activate && pip install -r teaching_panel/requirements-production.txt && python teaching_panel/manage.py migrate && python teaching_panel/manage.py collectstatic --noinput && sudo systemctl restart teaching_panel celery celery-beat"
        
        Write-Host ""
        Write-Host "✅ Бэкенд обновлён!" -ForegroundColor Green
    }
    
    "3" {
        Write-Host ""
        Write-Host "⚛️ ОБНОВЛЕНИЕ ФРОНТЕНДА" -ForegroundColor Cyan
        
        Invoke-RemoteCommand "cd $REMOTE_PATH && git pull origin main && cd frontend && npm install && npm run build && sudo systemctl restart nginx"
        
        Write-Host ""
        Write-Host "✅ Фронтенд обновлён!" -ForegroundColor Green
    }
    
    "4" {
        Write-Host ""
        Write-Host "🔄 ПЕРЕЗАПУСК СЕРВИСОВ" -ForegroundColor Cyan
        
        Invoke-RemoteCommand "sudo systemctl restart teaching_panel celery celery-beat nginx"
        
        Write-Host ""
        Write-Host "✅ Сервисы перезапущены!" -ForegroundColor Green
    }
    
    "5" {
        Write-Host ""
        Write-Host "🗄️ ПРИМЕНЕНИЕ МИГРАЦИЙ" -ForegroundColor Cyan
        
        Invoke-RemoteCommand "cd $REMOTE_PATH && source venv/bin/activate && python teaching_panel/manage.py migrate"
        
        Write-Host ""
        Write-Host "✅ Миграции применены!" -ForegroundColor Green
    }
    
    "6" {
        Write-Host ""
        Write-Host "📋 ЛОГИ СЕРВИСОВ" -ForegroundColor Cyan
        Write-Host "================" -ForegroundColor Cyan
        Write-Host ""
        Write-Host "Выберите логи:" -ForegroundColor Yellow
        Write-Host "1 - Django (teaching_panel)" -ForegroundColor White
        Write-Host "2 - Celery" -ForegroundColor White
        Write-Host "3 - Nginx Access" -ForegroundColor White
        Write-Host "4 - Nginx Error" -ForegroundColor White
        Write-Host ""
        
        $logChoice = Read-Host "Ваш выбор"
        
        switch ($logChoice) {
            "1" { Invoke-RemoteCommand "sudo journalctl -u teaching_panel -n 50 --no-pager" }
            "2" { Invoke-RemoteCommand "sudo journalctl -u celery -n 50 --no-pager" }
            "3" { Invoke-RemoteCommand "sudo tail -n 50 /var/log/nginx/teaching_panel_access.log" }
            "4" { Invoke-RemoteCommand "sudo tail -n 50 /var/log/nginx/teaching_panel_error.log" }
        }
    }
    
    "7" {
        Write-Host ""
        Write-Host "📊 СТАТУС СЕРВИСОВ" -ForegroundColor Cyan
        Write-Host "==================" -ForegroundColor Cyan
        
        Invoke-RemoteCommand "sudo systemctl status teaching_panel celery celery-beat nginx redis-server --no-pager"
    }
    
    "0" {
        Write-Host ""
        Write-Host "👋 Выход..." -ForegroundColor Gray
        exit
    }
    
    default {
        Write-Host ""
        Write-Host "❌ Неверный выбор!" -ForegroundColor Red
    }
}

Write-Host ""
Write-Host "Нажмите любую клавишу для продолжения..." -ForegroundColor Gray
$null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")

# Рекурсивно запустить скрипт снова
& $PSCommandPath
