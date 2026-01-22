# ============================================================
# SAFE DEPLOY SCRIPT FOR WINDOWS (PowerShell)
# ============================================================
# Безопасный деплой с проверками и автооткатом
# 
# Использование:
#   .\deploy_safe.ps1 -Type frontend
#   .\deploy_safe.ps1 -Type backend
#   .\deploy_safe.ps1 -Type full
# ============================================================

param(
    [Parameter(Mandatory=$true)]
    [ValidateSet("frontend", "backend", "full")]
    [string]$Type,
    
    [switch]$SkipBuild,
    [switch]$Force
)

$ErrorActionPreference = "Stop"

# ==================== КОНФИГУРАЦИЯ ====================
$SiteUrl = "https://lectio.tw1.ru"
$SshHost = "tp"
$RemotePath = "/var/www/teaching_panel"
$LocalFrontend = "frontend/build"

# ==================== ФУНКЦИИ ====================

function Write-Step {
    param([string]$Message)
    Write-Host "`n[$(Get-Date -Format 'HH:mm:ss')] $Message" -ForegroundColor Cyan
}

function Write-Success {
    param([string]$Message)
    Write-Host "[OK] $Message" -ForegroundColor Green
}

function Write-Error {
    param([string]$Message)
    Write-Host "[ERROR] $Message" -ForegroundColor Red
}

function Write-Warning {
    param([string]$Message)
    Write-Host "[WARN] $Message" -ForegroundColor Yellow
}

function Test-SiteHealth {
    param([int]$Retries = 5, [int]$Delay = 3)
    
    for ($i = 1; $i -le $Retries; $i++) {
        try {
            $response = Invoke-WebRequest -Uri $SiteUrl -TimeoutSec 10 -UseBasicParsing -ErrorAction Stop
            if ($response.StatusCode -eq 200) {
                Write-Success "Health check пройден (попытка $i/$Retries)"
                return $true
            }
        } catch {
            Write-Warning "Health check failed (попытка $i/$Retries): $($_.Exception.Message)"
        }
        
        if ($i -lt $Retries) {
            Start-Sleep -Seconds $Delay
        }
    }
    
    Write-Error "Health check провален после $Retries попыток"
    return $false
}

function Deploy-Frontend {
    Write-Step "Деплой Frontend..."
    
    # 1. Build (если не пропущен)
    if (-not $SkipBuild) {
        Write-Step "Сборка frontend..."
        Push-Location frontend
        try {
            npm run build 2>&1 | Out-Null
            if ($LASTEXITCODE -ne 0) {
                throw "npm build failed"
            }
            Write-Success "Build успешен"
        } finally {
            Pop-Location
        }
    }
    
    # 2. Проверка что build существует
    if (-not (Test-Path $LocalFrontend)) {
        throw "Build директория не найдена: $LocalFrontend"
    }
    
    # 3. Pre-deploy health check
    Write-Step "Pre-deploy проверка..."
    $preHealthy = Test-SiteHealth -Retries 1 -Delay 0
    
    # 4. Backup на сервере
    Write-Step "Создание backup на сервере..."
    ssh $SshHost "cd $RemotePath/frontend && if [ -d build ]; then cp -a build build_backup_`$(date +%Y%m%d_%H%M%S); fi"
    
    # 5. Копирование новой сборки
    Write-Step "Копирование файлов на сервер..."
    ssh $SshHost "rm -rf $RemotePath/frontend/build_new"
    scp -r $LocalFrontend "${SshHost}:${RemotePath}/frontend/build_new"
    
    if ($LASTEXITCODE -ne 0) {
        throw "SCP failed"
    }
    Write-Success "Файлы скопированы"
    
    # 6. Atomic swap + FIX PERMISSIONS (КРИТИЧЕСКИ ВАЖНО!)
    Write-Step "Атомарная замена + исправление прав..."
    ssh $SshHost @"
cd $RemotePath/frontend
rm -rf build_old
if [ -d build ]; then mv build build_old; fi
mv build_new build

# КРИТИЧЕСКИ ВАЖНО: Исправляем права доступа!
sudo chown -R www-data:www-data build
sudo chmod -R 755 build

# Перезапуск nginx для очистки кэша
sudo systemctl reload nginx

echo "DEPLOY_COMPLETE"
"@
    
    Write-Success "Деплой выполнен"
    
    # 7. Post-deploy health check
    Write-Step "Post-deploy проверка..."
    Start-Sleep -Seconds 2
    
    if (Test-SiteHealth) {
        Write-Success "Деплой frontend успешно завершён!"
        
        # Cleanup old backup
        ssh $SshHost "rm -rf $RemotePath/frontend/build_old"
        
        return $true
    } else {
        Write-Error "Health check провален, выполняю откат..."
        
        # Rollback
        ssh $SshHost @"
cd $RemotePath/frontend
rm -rf build
mv build_old build
sudo chown -R www-data:www-data build
sudo chmod -R 755 build
sudo systemctl reload nginx
echo "ROLLBACK_COMPLETE"
"@
        
        Start-Sleep -Seconds 2
        if (Test-SiteHealth) {
            Write-Warning "Откат успешен, сайт работает"
        } else {
            Write-Error "КРИТИЧЕСКАЯ ОШИБКА: откат не помог!"
        }
        
        return $false
    }
}

function Deploy-Backend {
    Write-Step "Деплой Backend..."
    
    # 1. Git pull
    Write-Step "Обновление кода на сервере..."
    ssh $SshHost "cd $RemotePath && git fetch origin && git reset --hard origin/main"
    
    # 2. Install dependencies
    Write-Step "Установка зависимостей..."
    ssh $SshHost "cd $RemotePath && source venv/bin/activate && pip install -r requirements.txt -q"
    
    # 3. Migrations
    Write-Step "Применение миграций..."
    ssh $SshHost "cd $RemotePath/teaching_panel && source ../venv/bin/activate && python manage.py migrate --noinput"
    
    # 4. Collect static
    Write-Step "Сбор статики..."
    ssh $SshHost "cd $RemotePath/teaching_panel && source ../venv/bin/activate && python manage.py collectstatic --noinput --clear -v 0"
    
    # 5. Restart service
    Write-Step "Перезапуск сервиса..."
    ssh $SshHost "sudo systemctl restart teaching_panel"
    
    # 6. Health check
    Start-Sleep -Seconds 3
    if (Test-SiteHealth) {
        Write-Success "Деплой backend успешно завершён!"
        return $true
    } else {
        Write-Error "Backend деплой провален"
        return $false
    }
}

# ==================== MAIN ====================

Write-Host "============================================" -ForegroundColor Magenta
Write-Host " LECTIO SAFE DEPLOY" -ForegroundColor Magenta
Write-Host " Type: $Type" -ForegroundColor Magenta
Write-Host "============================================" -ForegroundColor Magenta

$success = $false

switch ($Type) {
    "frontend" {
        $success = Deploy-Frontend
    }
    "backend" {
        $success = Deploy-Backend
    }
    "full" {
        $backendOk = Deploy-Backend
        if ($backendOk) {
            $success = Deploy-Frontend
        } else {
            Write-Error "Backend деплой провален, frontend пропущен"
            $success = $false
        }
    }
}

Write-Host "`n============================================" -ForegroundColor Magenta
if ($success) {
    Write-Host " DEPLOY SUCCESSFUL!" -ForegroundColor Green
} else {
    Write-Host " DEPLOY FAILED!" -ForegroundColor Red
    exit 1
}
Write-Host "============================================" -ForegroundColor Magenta
