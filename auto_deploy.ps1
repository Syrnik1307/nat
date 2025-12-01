# ========================================
# Teaching Panel - Автоматический деплой
# ========================================
# Универсальный скрипт для Windows/Linux
# Требует: Git, SSH клиент
# ========================================

param(
    [string]$Action = "menu",
    [switch]$SkipBuild = $false,
    [switch]$Force = $false
)

# Конфигурация
$SERVER = "root@72.56.81.163"
$SSH_KEY = "$env:USERPROFILE\.ssh\id_rsa_deploy"
$SSH_OPTS = "-i `"$SSH_KEY`" -o IdentitiesOnly=yes"
$LOCAL_DIR = $PSScriptRoot
$REMOTE_DIR = "/var/www/teaching_panel"
$GIT_REPO = "https://github.com/Syrnik1307/nat.git"

# Цвета для вывода
$ErrorColor = "Red"
$SuccessColor = "Green"
$WarningColor = "Yellow"
$InfoColor = "Cyan"

# ========================================
# Вспомогательные функции
# ========================================

function Write-Status {
    param([string]$Message, [string]$Type = "Info")
    
    $color = switch ($Type) {
        "Error" { $ErrorColor }
        "Success" { $SuccessColor }
        "Warning" { $WarningColor }
        default { $InfoColor }
    }
    
    $icon = switch ($Type) {
        "Error" { "❌" }
        "Success" { "✅" }
        "Warning" { "⚠️" }
        default { "ℹ️" }
    }
    
    Write-Host "$icon $Message" -ForegroundColor $color
}

function Test-SSHConnection {
    Write-Status "Проверка подключения к серверу..." "Info"
    
    try {
        $result = ssh -i $SSH_KEY -o IdentitiesOnly=yes -o ConnectTimeout=5 -o BatchMode=yes $SERVER "echo 'OK'" 2>&1
        if ($LASTEXITCODE -eq 0) {
            Write-Status "SSH соединение установлено" "Success"
            return $true
        }
    } catch {}
    
    Write-Status "Не удалось подключиться к серверу через SSH" "Error"
    Write-Host ""
    Write-Host "╔════════════════════════════════════════════════════════════════╗" -ForegroundColor Yellow
    Write-Host "║ SSH подключение не настроено                                   ║" -ForegroundColor Yellow
    Write-Host "╚════════════════════════════════════════════════════════════════╝" -ForegroundColor Yellow
    Write-Host ""
    Write-Host "Возможные причины:" -ForegroundColor Yellow
    Write-Host "  1. SSH клиент не установлен" -ForegroundColor Gray
    Write-Host "  2. SSH ключи не созданы" -ForegroundColor Gray
    Write-Host "  3. SSH ключ не скопирован на сервер" -ForegroundColor Gray
    Write-Host "  4. Сервер недоступен" -ForegroundColor Gray
    Write-Host ""
    Write-Host "╔════════════════════════════════════════════════════════════════╗" -ForegroundColor Cyan
    Write-Host "║ 🛠️  АВТОМАТИЧЕСКАЯ НАСТРОЙКА SSH                               ║" -ForegroundColor Cyan
    Write-Host "╚════════════════════════════════════════════════════════════════╝" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "У нас есть скрипт для автоматической настройки SSH!" -ForegroundColor Green
    Write-Host ""
    Write-Host "Запустить настройку SSH сейчас? (y/n)" -ForegroundColor Yellow
    $runSetup = Read-Host
    
    if ($runSetup -eq 'y') {
        Write-Host ""
        Write-Host "Запуск скрипта настройки SSH..." -ForegroundColor Cyan
        $setupScript = Join-Path $PSScriptRoot "setup_ssh.ps1"
        
        if (Test-Path $setupScript) {
            & $setupScript
            
            # После настройки проверить снова
            Write-Host ""
            Write-Host "Проверка подключения после настройки..." -ForegroundColor Yellow
            try {
                $result = ssh -i $SSH_KEY -o IdentitiesOnly=yes -o ConnectTimeout=5 -o BatchMode=yes $SERVER "echo 'OK'" 2>&1
                if ($LASTEXITCODE -eq 0) {
                    Write-Status "SSH соединение установлено!" "Success"
                    return $true
                }
            } catch {}
        } else {
            Write-Status "Скрипт setup_ssh.ps1 не найден в $PSScriptRoot" "Error"
            Write-Host ""
            Write-Host "Ручная настройка SSH:" -ForegroundColor Yellow
            Write-Host "  1. Установить SSH клиент: winget install Microsoft.OpenSSH.Preview" -ForegroundColor Gray
            Write-Host "  2. Создать ключ: ssh-keygen -t rsa -b 4096" -ForegroundColor Gray
            Write-Host "  3. Скопировать ключ на сервер:" -ForegroundColor Gray
            Write-Host '     type $env:USERPROFILE\.ssh\id_rsa.pub | ssh root@72.56.81.163 "cat >> ~/.ssh/authorized_keys"' -ForegroundColor Gray
        }
    } else {
        Write-Host ""
        Write-Host "Для ручной настройки SSH:" -ForegroundColor Yellow
        Write-Host "  1. Запустите: .\setup_ssh.ps1" -ForegroundColor Cyan
        Write-Host "  2. Или настройте вручную:" -ForegroundColor Gray
        Write-Host "     - winget install Microsoft.OpenSSH.Preview" -ForegroundColor Gray
        Write-Host "     - ssh-keygen -t rsa -b 4096" -ForegroundColor Gray
        Write-Host '     - type $env:USERPROFILE\.ssh\id_rsa.pub | ssh root@72.56.81.163 "cat >> ~/.ssh/authorized_keys"' -ForegroundColor Gray
    }
    
    Write-Host ""
    return $false
}

function Invoke-RemoteCommand {
    param(
        [string]$Command,
        [string]$Description = "Выполнение команды"
    )
    
    Write-Status "$Description..." "Info"
    
    try {
        $output = ssh -i $SSH_KEY -o IdentitiesOnly=yes $SERVER $Command 2>&1
        if ($LASTEXITCODE -eq 0) {
            Write-Status "$Description - Готово" "Success"
            return $true
        } else {
            Write-Status "$Description - Ошибка" "Error"
            Write-Host $output -ForegroundColor Red
            return $false
        }
    } catch {
        Write-Status "$Description - Исключение: $_" "Error"
        return $false
    }
}

function Show-Menu {
    Clear-Host
    Write-Host ""
    Write-Host "╔════════════════════════════════════════════╗" -ForegroundColor Cyan
    Write-Host "║   Teaching Panel - Автодеплой на сервер   ║" -ForegroundColor Cyan
    Write-Host "╚════════════════════════════════════════════╝" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "Сервер: $SERVER" -ForegroundColor Gray
    Write-Host "Путь: $REMOTE_DIR" -ForegroundColor Gray
    Write-Host ""
    Write-Host "╔════════════════════════════════════════════╗" -ForegroundColor White
    Write-Host "║ ОСНОВНЫЕ ДЕЙСТВИЯ                          ║" -ForegroundColor White
    Write-Host "╠════════════════════════════════════════════╣" -ForegroundColor White
    Write-Host "║ 1 - 🚀 Полный деплой (всё)                 ║" -ForegroundColor White
    Write-Host "║ 2 - 🐍 Обновить только бэкенд (Django)     ║" -ForegroundColor White
    Write-Host "║ 3 - ⚛️  Обновить только фронтенд (React)   ║" -ForegroundColor White
    Write-Host "║ 4 - 🗄️  Применить миграции БД              ║" -ForegroundColor White
    Write-Host "║ 5 - 🔄 Перезапустить сервисы               ║" -ForegroundColor White
    Write-Host "╠════════════════════════════════════════════╣" -ForegroundColor White
    Write-Host "║ МОНИТОРИНГ                                 ║" -ForegroundColor White
    Write-Host "╠════════════════════════════════════════════╣" -ForegroundColor White
    Write-Host "║ 6 - 📊 Статус сервисов                     ║" -ForegroundColor White
    Write-Host "║ 7 - 📋 Просмотр логов                      ║" -ForegroundColor White
    Write-Host "║ 8 - 🔍 Проверить здоровье системы          ║" -ForegroundColor White
    Write-Host "╠════════════════════════════════════════════╣" -ForegroundColor White
    Write-Host "║ ОБСЛУЖИВАНИЕ                               ║" -ForegroundColor White
    Write-Host "╠════════════════════════════════════════════╣" -ForegroundColor White
    Write-Host "║ 9 - 🧹 Очистить кеш и temp файлы           ║" -ForegroundColor White
    Write-Host "║ 10 - 📦 Обновить зависимости               ║" -ForegroundColor White
    Write-Host "║ 11 - 🔐 Проверить SSL сертификат           ║" -ForegroundColor White
    Write-Host "╠════════════════════════════════════════════╣" -ForegroundColor White
    Write-Host "║ 0 - 👋 Выход                               ║" -ForegroundColor White
    Write-Host "╚════════════════════════════════════════════╝" -ForegroundColor White
    Write-Host ""
}

function Deploy-Full {
    Write-Host ""
    Write-Host "════════════════════════════════════════" -ForegroundColor Cyan
    Write-Host "  🚀 ПОЛНЫЙ ДЕПЛОЙ" -ForegroundColor Cyan
    Write-Host "════════════════════════════════════════" -ForegroundColor Cyan
    Write-Host ""
    
    $steps = @(
        @{ Num=1; Total=8; Desc="Обновление кода из Git"; Cmd="cd $REMOTE_DIR && git pull origin main" },
        @{ Num=2; Total=8; Desc="Удаление Celery файлов"; Cmd="echo '# Celery removed - no longer needed' > $REMOTE_DIR/teaching_panel/teaching_panel/__init__.py && rm -f $REMOTE_DIR/teaching_panel/teaching_panel/celery.py" },
        @{ Num=3; Total=8; Desc="Обновление Python зависимостей"; Cmd="cd $REMOTE_DIR && source venv/bin/activate && pip install -r teaching_panel/requirements.txt --quiet" },
        @{ Num=4; Total=8; Desc="Применение миграций БД"; Cmd="cd $REMOTE_DIR && source venv/bin/activate && python teaching_panel/manage.py migrate --noinput" },
        @{ Num=5; Total=8; Desc="Сборка статики Django"; Cmd="cd $REMOTE_DIR && source venv/bin/activate && python teaching_panel/manage.py collectstatic --noinput --clear" },
        @{ Num=6; Total=8; Desc="Установка npm пакетов"; Cmd="cd $REMOTE_DIR/frontend && npm install --silent" },
        @{ Num=7; Total=8; Desc="Сборка React фронтенда"; Cmd="cd $REMOTE_DIR/frontend && umask 022 && npm run build" },
        @{ Num=8; Total=8; Desc="Перезапуск Django и Nginx"; Cmd="sudo systemctl restart teaching_panel nginx" }
    )
    
    foreach ($step in $steps) {
        Write-Host ""
        Write-Host "[$($step.Num)/$($step.Total)] $($step.Desc)..." -ForegroundColor Yellow
        
        if (-not (Invoke-RemoteCommand -Command $step.Cmd -Description $step.Desc)) {
            Write-Status "Деплой прерван на шаге $($step.Num)" "Error"
            return $false
        }
    }
    
    Write-Host ""
    Write-Host "════════════════════════════════════════" -ForegroundColor Green
    Write-Host "  ✅ ДЕПЛОЙ ЗАВЕРШЁН УСПЕШНО!" -ForegroundColor Green
    Write-Host "════════════════════════════════════════" -ForegroundColor Green
    Write-Host ""
    Write-Host "🌐 Сайт: http://72.56.81.163" -ForegroundColor Cyan
    Write-Host ""
    
    return $true
}

function Deploy-Backend {
    Write-Host ""
    Write-Host "════════════════════════════════════════" -ForegroundColor Cyan
    Write-Host "  🐍 ОБНОВЛЕНИЕ БЭКЕНДА" -ForegroundColor Cyan
    Write-Host "════════════════════════════════════════" -ForegroundColor Cyan
    Write-Host ""
    
    $commands = @"
cd $REMOTE_DIR && 
git pull origin main && 
source venv/bin/activate && 
pip install -r teaching_panel/requirements.txt --quiet && 
python teaching_panel/manage.py migrate --noinput && 
python teaching_panel/manage.py collectstatic --noinput --clear && 
sudo systemctl restart teaching_panel
"@
    
    if (Invoke-RemoteCommand -Command $commands -Description "Обновление бэкенда") {
        Write-Status "Бэкенд обновлён успешно!" "Success"
        return $true
    }
    return $false
}

function Deploy-Frontend {
    Write-Host ""
    Write-Host "════════════════════════════════════════" -ForegroundColor Cyan
    Write-Host "  ⚛️ ОБНОВЛЕНИЕ ФРОНТЕНДА" -ForegroundColor Cyan
    Write-Host "════════════════════════════════════════" -ForegroundColor Cyan
    Write-Host ""
    
    $commands = @"
cd $REMOTE_DIR && 
git pull origin main && 
cd frontend && 
npm install --silent && 
umask 022 && npm run build && 
sudo systemctl restart nginx
"@
    
    if (Invoke-RemoteCommand -Command $commands -Description "Обновление фронтенда") {
        Write-Status "Фронтенд обновлён успешно!" "Success"
        return $true
    }
    return $false
}

function Apply-Migrations {
    Write-Host ""
    Write-Host "════════════════════════════════════════" -ForegroundColor Cyan
    Write-Host "  🗄️ ПРИМЕНЕНИЕ МИГРАЦИЙ" -ForegroundColor Cyan
    Write-Host "════════════════════════════════════════" -ForegroundColor Cyan
    Write-Host ""
    
    $commands = @"
cd $REMOTE_DIR && 
source venv/bin/activate && 
python teaching_panel/manage.py migrate --noinput
"@
    
    if (Invoke-RemoteCommand -Command $commands -Description "Применение миграций") {
        Write-Status "Миграции применены!" "Success"
        return $true
    }
    return $false
}

function Restart-Services {
    Write-Host ""
    Write-Host "════════════════════════════════════════" -ForegroundColor Cyan
    Write-Host "  🔄 ПЕРЕЗАПУСК СЕРВИСОВ" -ForegroundColor Cyan
    Write-Host "════════════════════════════════════════" -ForegroundColor Cyan
    Write-Host ""
    
    Invoke-RemoteCommand -Command "sudo systemctl restart teaching_panel nginx redis-server" -Description "Перезапуск сервисов"
    Write-Status "Все сервисы перезапущены!" "Success"
}

function Show-Status {
    Write-Host ""
    Write-Host "════════════════════════════════════════" -ForegroundColor Cyan
    Write-Host "  📊 СТАТУС СЕРВИСОВ" -ForegroundColor Cyan
    Write-Host "════════════════════════════════════════" -ForegroundColor Cyan
    Write-Host ""
    
    ssh -i $SSH_KEY -o IdentitiesOnly=yes $SERVER "sudo systemctl status teaching_panel nginx redis-server --no-pager"
}

function Show-Logs {
    Write-Host ""
    Write-Host "════════════════════════════════════════" -ForegroundColor Cyan
    Write-Host "  📋 ПРОСМОТР ЛОГОВ" -ForegroundColor Cyan
    Write-Host "════════════════════════════════════════" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "Выберите тип логов:" -ForegroundColor Yellow
    Write-Host "  1 - Django (teaching_panel)" -ForegroundColor White
    Write-Host "  2 - Nginx Access" -ForegroundColor White
    Write-Host "  3 - Nginx Error" -ForegroundColor White
    Write-Host "  4 - Redis" -ForegroundColor White
    Write-Host ""
    
    $logChoice = Read-Host "Ваш выбор"
    Write-Host ""
    
    switch ($logChoice) {
        "1" { ssh -i $SSH_KEY -o IdentitiesOnly=yes $SERVER "sudo journalctl -u teaching_panel -n 100 --no-pager" }
        "2" { ssh -i $SSH_KEY -o IdentitiesOnly=yes $SERVER "sudo tail -n 100 /var/log/nginx/teaching_panel_access.log" }
        "3" { ssh -i $SSH_KEY -o IdentitiesOnly=yes $SERVER "sudo tail -n 100 /var/log/nginx/teaching_panel_error.log" }
        "4" { ssh -i $SSH_KEY -o IdentitiesOnly=yes $SERVER "sudo journalctl -u redis-server -n 100 --no-pager" }
        default { Write-Status "Неверный выбор" "Error" }
    }
}

function Check-Health {
    Write-Host ""
    Write-Host "════════════════════════════════════════" -ForegroundColor Cyan
    Write-Host "  🔍 ПРОВЕРКА ЗДОРОВЬЯ СИСТЕМЫ" -ForegroundColor Cyan
    Write-Host "════════════════════════════════════════" -ForegroundColor Cyan
    Write-Host ""
    
    $healthChecks = @"
echo '🔹 Использование диска:'
df -h | grep -E '^/dev|Filesystem'
echo ''
echo '🔹 Использование памяти:'
free -h
echo ''
echo '🔹 Процессы Python:'
echo '🔹 Процессы Python:'
ps aux | grep -E 'python|gunicorn' | grep -v grep | head -n 5
echo '🔹 Статус сервисов:'
echo '🔹 Статус сервисов:'
systemctl is-active teaching_panel nginx redis-server | paste -sd ' '
echo '🔹 Последние 5 ошибок Django:'
sudo journalctl -u teaching_panel -p err -n 5 --no-pager 2>/dev/null || echo 'Нет ошибок'
"@
    
    ssh -i $SSH_KEY -o IdentitiesOnly=yes $SERVER $healthChecks
}

function Clean-Cache {
    Write-Host ""
    Write-Host "════════════════════════════════════════" -ForegroundColor Cyan
    Write-Host "  🧹 ОЧИСТКА КЕША И TEMP ФАЙЛОВ" -ForegroundColor Cyan
    Write-Host "════════════════════════════════════════" -ForegroundColor Cyan
    Write-Host ""
    
    $commands = @"
cd $REMOTE_DIR && 
source venv/bin/activate && 
echo 'Очистка Python __pycache__...' && 
find . -type d -name '__pycache__' -exec rm -rf {} + 2>/dev/null || true && 
echo 'Очистка .pyc файлов...' && 
find . -type f -name '*.pyc' -delete && 
echo 'Очистка node_modules cache...' && 
cd frontend && npm cache clean --force && 
echo 'Очистка Django кеша...' && 
cd .. && python teaching_panel/manage.py clear_cache 2>/dev/null || echo 'Django cache cleared' && 
echo '✅ Очистка завершена!'
"@
    
    Invoke-RemoteCommand -Command $commands -Description "Очистка кеша"
}

function Update-Dependencies {
    Write-Host ""
    Write-Host "════════════════════════════════════════" -ForegroundColor Cyan
    Write-Host "  📦 ОБНОВЛЕНИЕ ЗАВИСИМОСТЕЙ" -ForegroundColor Cyan
    Write-Host "════════════════════════════════════════" -ForegroundColor Cyan
    Write-Host ""
    
    $commands = @"
cd $REMOTE_DIR && 
source venv/bin/activate && 
echo 'Обновление pip...' && 
pip install --upgrade pip --quiet && 
echo 'Обновление Python пакетов...' && 
pip install -r teaching_panel/requirements.txt --upgrade --quiet && 
echo 'Обновление npm пакетов...' && 
cd frontend && 
npm update --silent && 
echo '✅ Зависимости обновлены!'
"@
    
    Invoke-RemoteCommand -Command $commands -Description "Обновление зависимостей"
}

function Check-SSL {
    Write-Host ""
    Write-Host "════════════════════════════════════════" -ForegroundColor Cyan
    Write-Host "  🔐 ПРОВЕРКА SSL СЕРТИФИКАТА" -ForegroundColor Cyan
    Write-Host "════════════════════════════════════════" -ForegroundColor Cyan
    Write-Host ""
    
    ssh -i $SSH_KEY -o IdentitiesOnly=yes $SERVER "sudo certbot certificates"
}

# ========================================
# Главная логика
# ========================================

# Проверка SSH подключения
if (-not (Test-SSHConnection)) {
    Write-Host ""
    Write-Host "Нажмите любую клавишу для выхода..." -ForegroundColor Gray
    $null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")
    exit 1
}

# Главный цикл меню
while ($true) {
    Show-Menu
    
    $choice = Read-Host "Выберите действие"
    
    switch ($choice) {
        "1" { Deploy-Full }
        "2" { Deploy-Backend }
        "3" { Deploy-Frontend }
        "4" { Apply-Migrations }
        "5" { Restart-Services }
        "6" { Show-Status }
        "7" { Show-Logs }
        "8" { Check-Health }
        "9" { Clean-Cache }
        "10" { Update-Dependencies }
        "11" { Check-SSL }
        "0" { 
            Write-Host ""
            Write-Status "Выход из программы" "Info"
            exit 0
        }
        default { 
            Write-Status "Неверный выбор! Попробуйте снова." "Error"
        }
    }
    
    Write-Host ""
    Write-Host "Нажмите любую клавишу для возврата в меню..." -ForegroundColor Gray
    $null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")
}
