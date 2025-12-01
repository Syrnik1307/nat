# ========================================
# Настройка SSH для автодеплоя
# ========================================

$SERVER = "root@72.56.81.163"
$SSH_DIR = "$env:USERPROFILE\.ssh"
# Единый deploy-ключ без пароля, согласованный с auto_deploy.ps1
$PRIVATE_KEY = "$SSH_DIR\id_rsa_deploy"
$PUBLIC_KEY = "$SSH_DIR\id_rsa_deploy.pub"

Write-Host ""
Write-Host "╔════════════════════════════════════════════╗" -ForegroundColor Cyan
Write-Host "║   Настройка SSH для автодеплоя            ║" -ForegroundColor Cyan
Write-Host "╚════════════════════════════════════════════╝" -ForegroundColor Cyan
Write-Host ""

# Шаг 1: Проверить SSH клиент
Write-Host "Шаг 1: Проверка SSH клиента..." -ForegroundColor Yellow
try {
    $sshVersion = ssh -V 2>&1
    Write-Host "✅ SSH клиент установлен: $sshVersion" -ForegroundColor Green
} catch {
    Write-Host "❌ SSH клиент не установлен" -ForegroundColor Red
    Write-Host ""
    Write-Host "Установка SSH клиента..." -ForegroundColor Yellow
    winget install Microsoft.OpenSSH.Preview
    
    # Обновить PATH
    $env:Path = [System.Environment]::GetEnvironmentVariable("Path","Machine") + ";" + [System.Environment]::GetEnvironmentVariable("Path","User")
    
    Write-Host "✅ SSH клиент установлен" -ForegroundColor Green
}

Write-Host ""

# Шаг 2: Проверить SSH ключи
Write-Host "Шаг 2: Проверка SSH ключей..." -ForegroundColor Yellow

if (Test-Path $PRIVATE_KEY) {
    Write-Host "✅ SSH ключи уже существуют" -ForegroundColor Green
    Write-Host "   Путь: $PRIVATE_KEY" -ForegroundColor Gray
} else {
    Write-Host "⚠️  SSH ключи не найдены" -ForegroundColor Yellow
    Write-Host ""
    Write-Host "Создание SSH ключей..." -ForegroundColor Yellow
    
    # Создать директорию .ssh если нужно
    if (-not (Test-Path $SSH_DIR)) {
        New-Item -ItemType Directory -Path $SSH_DIR | Out-Null
    }
    
    # Создать deploy-ключ без пароля (ed25519 быстрее и короче)
    ssh-keygen -t ed25519 -f $PRIVATE_KEY -N "" -C "teaching-panel-deploy"
    
    Write-Host "✅ SSH ключи созданы" -ForegroundColor Green
}

Write-Host ""

# Шаг 3: Скопировать ключ на сервер
Write-Host "Шаг 3: Копирование ключа на сервер..." -ForegroundColor Yellow
Write-Host ""

# Проверить, может ли мы уже подключиться без пароля
Write-Host "Проверка подключения к серверу..." -ForegroundColor Gray
$canConnect = $false
try {
    $testResult = ssh -o ConnectTimeout=5 -o BatchMode=yes $SERVER "echo 'OK'" 2>&1
    if ($LASTEXITCODE -eq 0) {
        $canConnect = $true
    }
} catch {}

if ($canConnect) {
    Write-Host "✅ SSH подключение уже настроено!" -ForegroundColor Green
    Write-Host "   Можно использовать автодеплой без пароля" -ForegroundColor Gray
} else {
    Write-Host "⚠️  SSH ключ ещё не скопирован на сервер" -ForegroundColor Yellow
    Write-Host ""
    Write-Host "╔════════════════════════════════════════════════════════════════╗" -ForegroundColor Yellow
    Write-Host "║ Для копирования ключа на сервер нужен пароль root             ║" -ForegroundColor Yellow
    Write-Host "╚════════════════════════════════════════════════════════════════╝" -ForegroundColor Yellow
    Write-Host ""
    Write-Host "Выберите способ:" -ForegroundColor Cyan
    Write-Host "  1 - Автоматически (потребует пароль root)" -ForegroundColor White
    Write-Host "  2 - Вручную (показать инструкции)" -ForegroundColor White
    Write-Host "  0 - Пропустить (настроить позже)" -ForegroundColor White
    Write-Host ""
    
    $choice = Read-Host "Ваш выбор"
    
    switch ($choice) {
        "1" {
            Write-Host ""
            Write-Host "Копирование ключа на сервер..." -ForegroundColor Yellow
            Write-Host "Введите пароль root когда запросит:" -ForegroundColor Gray
            Write-Host ""
            
            # Копируем ключ
            $publicKeyContent = Get-Content $PUBLIC_KEY
            $command = "mkdir -p ~/.ssh && echo '$publicKeyContent' >> ~/.ssh/authorized_keys && chmod 700 ~/.ssh && chmod 600 ~/.ssh/authorized_keys"
            
            ssh $SERVER $command
            
            if ($LASTEXITCODE -eq 0) {
                Write-Host ""
                Write-Host "✅ Ключ успешно скопирован на сервер!" -ForegroundColor Green
                
                # Проверить подключение
                Write-Host "Проверка подключения..." -ForegroundColor Gray
                $testResult = ssh -o ConnectTimeout=5 $SERVER "echo 'OK'" 2>&1
                
                if ($LASTEXITCODE -eq 0) {
                    Write-Host "✅ SSH подключение работает без пароля!" -ForegroundColor Green
                } else {
                    Write-Host "⚠️  Подключение не удалось, попробуйте вручную" -ForegroundColor Yellow
                }
            } else {
                Write-Host "❌ Не удалось скопировать ключ" -ForegroundColor Red
                Write-Host "Попробуйте вручную (опция 2)" -ForegroundColor Yellow
            }
        }
        
        "2" {
            Write-Host ""
            Write-Host "╔════════════════════════════════════════════════════════════════╗" -ForegroundColor Cyan
            Write-Host "║ Инструкция по ручному копированию ключа                       ║" -ForegroundColor Cyan
            Write-Host "╚════════════════════════════════════════════════════════════════╝" -ForegroundColor Cyan
            Write-Host ""
            Write-Host "Вариант 1: Через командную строку" -ForegroundColor Yellow
            Write-Host ""
            Write-Host "Выполните эту команду (потребует пароль root):" -ForegroundColor Gray
            Write-Host ""
            Write-Host 'type $env:USERPROFILE\.ssh\id_rsa.pub | ssh root@72.56.81.163 "mkdir -p ~/.ssh && cat >> ~/.ssh/authorized_keys && chmod 700 ~/.ssh && chmod 600 ~/.ssh/authorized_keys"' -ForegroundColor Cyan
            Write-Host ""
            Write-Host "Вариант 2: Вручную через PuTTY/другой SSH клиент" -ForegroundColor Yellow
            Write-Host ""
            Write-Host "1. Скопируйте содержимое публичного ключа:" -ForegroundColor Gray
            Write-Host ""
            Get-Content $PUBLIC_KEY | Write-Host -ForegroundColor Green
            Write-Host ""
            Write-Host "2. Подключитесь к серверу через SSH" -ForegroundColor Gray
            Write-Host "3. Выполните на сервере:" -ForegroundColor Gray
            Write-Host "   mkdir -p ~/.ssh" -ForegroundColor White
            Write-Host "   nano ~/.ssh/authorized_keys" -ForegroundColor White
            Write-Host "4. Вставьте скопированный ключ в файл" -ForegroundColor Gray
            Write-Host "5. Сохраните (Ctrl+O, Enter, Ctrl+X)" -ForegroundColor Gray
            Write-Host "6. Установите права:" -ForegroundColor Gray
            Write-Host "   chmod 700 ~/.ssh" -ForegroundColor White
            Write-Host "   chmod 600 ~/.ssh/authorized_keys" -ForegroundColor White
            Write-Host ""
        }
        
        "0" {
            Write-Host ""
            Write-Host "⚠️  Настройка пропущена" -ForegroundColor Yellow
            Write-Host "Вы можете настроить SSH позже, запустив этот скрипт снова" -ForegroundColor Gray
        }
    }
}

Write-Host ""
Write-Host "════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host "  Итоговая проверка" -ForegroundColor Cyan
Write-Host "════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host ""

# Создаём/обновляем SSH config для принудительного использования deploy-ключа
try {
    $sshConfigPath = Join-Path $SSH_DIR "config"
    $configBlock = @()
    if (Test-Path $sshConfigPath) {
        $configBlock = Get-Content $sshConfigPath
    }

    $hostLine = "Host teaching-panel"
    $desired = @(
        $hostLine,
        "  HostName 72.56.81.163",
        "  User root",
        "  IdentityFile $PRIVATE_KEY",
        "  IdentitiesOnly yes",
        "  ServerAliveInterval 30",
        "  ServerAliveCountMax 3"
    )

    $needsWrite = $true
    if ($configBlock -and ($configBlock -join "`n") -match [regex]::Escape($hostLine)) {
        # Если блок уже есть, не дублируем
        $needsWrite = $false
    }

    if ($needsWrite) {
        Add-Content -Path $sshConfigPath -Value "`n$($desired -join "`n")`n"
        Write-Host "✅ Обновлён ~/.ssh/config для teaching-panel" -ForegroundColor Green
    } else {
        Write-Host "ℹ️  ~/.ssh/config уже содержит блок teaching-panel" -ForegroundColor Yellow
    }
} catch {
    Write-Host "⚠️  Не удалось обновить ~/.ssh/config: $_" -ForegroundColor Yellow
}

# Финальная проверка
Write-Host "Проверка SSH подключения..." -ForegroundColor Yellow
try {
    $testResult = ssh -o ConnectTimeout=5 -o BatchMode=yes -i $PRIVATE_KEY -o IdentitiesOnly=yes $SERVER "echo 'OK'" 2>&1
    if ($LASTEXITCODE -eq 0) {
        Write-Host "✅ SSH настроен правильно!" -ForegroundColor Green
        Write-Host ""
        Write-Host "╔════════════════════════════════════════════════════════════════╗" -ForegroundColor Green
        Write-Host "║ ✅ ВСЁ ГОТОВО К ИСПОЛЬЗОВАНИЮ!                                 ║" -ForegroundColor Green
        Write-Host "╚════════════════════════════════════════════════════════════════╝" -ForegroundColor Green
        Write-Host ""
        Write-Host "Теперь вы можете использовать автодеплой:" -ForegroundColor Cyan
        Write-Host "  .\auto_deploy.ps1" -ForegroundColor White
        Write-Host ""
    } else {
        Write-Host "⚠️  SSH подключение не работает" -ForegroundColor Yellow
        Write-Host ""
        Write-Host "Возможные причины:" -ForegroundColor Yellow
        Write-Host "  1. Ключ ещё не скопирован на сервер" -ForegroundColor Gray
        Write-Host "  2. Неправильные права на файлы на сервере" -ForegroundColor Gray
        Write-Host "  3. Сервер недоступен" -ForegroundColor Gray
        Write-Host ""
        Write-Host "Запустите скрипт снова для повторной попытки:" -ForegroundColor Cyan
        Write-Host "  .\setup_ssh.ps1" -ForegroundColor White
        Write-Host ""
    }
} catch {
    Write-Host "❌ Ошибка подключения: $_" -ForegroundColor Red
}

Write-Host ""
Write-Host "Нажмите любую клавишу для выхода..." -ForegroundColor Gray
$null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")
