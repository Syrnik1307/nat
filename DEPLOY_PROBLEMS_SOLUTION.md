# 🛠 План решения проблем деплоя Teaching Panel

**Дата:** 7 февраля 2026  
**Цель:** Устранить все критические проблемы деплоя и создать надежный процесс

---

## 📋 Стратегия решения

### Фаза 1: СРОЧНЫЕ ИСПРАВЛЕНИЯ (сегодня)
✅ Исправить критические ошибки в существующих скриптах  
✅ Обеспечить работоспособность деплоя  

### Фаза 2: ОПТИМИЗАЦИЯ (завтра)
⚡ Создать единый надежный скрипт деплоя  
⚡ Добавить мониторинг и уведомления  

### Фаза 3: ДОЛГОСРОЧНОЕ (на неделю)
📝 Документация и обучение  
📝 Автоматизация тестирования  

---

## 🔥 Фаза 1: Срочные исправления

### Task 1.1: Исправить имена сервисов во всех скриптах

**Файлы для исправления:**
- ✅ `deploy_to_production.ps1` - 5 мест
- ✅ `deploy.ps1` - 3 места
- ✅ `deploy_simple.ps1` - 2 места
- ✅ `deploy_multi.ps1` - 3 места
- ✅ `auto_deploy.ps1` - проверить
- ✅ `quick_deploy.ps1` - 1 место
- ✅ `scripts/monitoring/deploy_safe.sh` - проверить

**Замены:**
```powershell
# НЕВЕРНО
systemctl restart teaching-panel
systemctl status teaching-panel
journalctl -u teaching-panel

# ВЕРНО
systemctl restart teaching_panel
systemctl status teaching_panel
journalctl -u teaching_panel
```

**Время:** 30 минут  
**Риск:** Низкий (простой поиск-замена)

---

### Task 1.2: Добавить health checks в auto_deploy.ps1

**Что добавить:**

1. **Функция Health Check:**
```powershell
function Test-SiteHealth {
    param(
        [string]$Url = "https://lectiospace.ru/api/health/",
        [int]$Retries = 5,
        [int]$Delay = 3
    )
    
    for ($i = 1; $i -le $Retries; $i++) {
        try {
            $response = Invoke-WebRequest -Uri $Url -UseBasicParsing -TimeoutSec 10
            if ($response.StatusCode -eq 200) {
                Write-Status "Health check пройден (попытка $i/$Retries)" "Success"
                return $true
            }
        } catch {
            Write-Status "Health check failed (попытка $i/$Retries): $_" "Warning"
        }
        
        if ($i -lt $Retries) {
            Start-Sleep -Seconds $Delay
        }
    }
    
    Write-Status "Health check провален после $Retries попыток" "Error"
    return $false
}
```

2. **Использовать в функциях деплоя:**
```powershell
function Deploy-Full {
    # ... existing code ...
    
    # После перезапуска сервисов
    Write-Host "Проверка работоспособности..." -ForegroundColor Yellow
    
    if (-not (Test-SiteHealth)) {
        Write-Status "КРИТИЧЕСКАЯ ОШИБКА: Сайт не отвечает после деплоя!" "Error"
        Write-Status "Выполняется откат..." "Warning"
        
        # Rollback logic
        Invoke-RemoteCommand -Command "cd $REMOTE_DIR && git reset --hard HEAD@{1}"
        Invoke-RemoteCommand -Command "sudo systemctl restart teaching_panel"
        
        if (Test-SiteHealth) {
            Write-Status "Откат выполнен успешно" "Success"
        } else {
            Write-Status "КРИТИЧНО: Откат не помог! Требуется ручное вмешательство!" "Error"
        }
        
        return $false
    }
    
    Write-Status "Деплой завершен успешно!" "Success"
    return $true
}
```

**Время:** 1 час  
**Риск:** Низкий (добавление функциональности)

---

### Task 1.3: Добавить fix_permissions в auto_deploy.ps1

**Функция для добавления:**
```powershell
function Fix-Permissions {
    Write-Status "Исправление прав доступа..." "Info"
    
    $commands = @(
        "sudo chown -R www-data:www-data /var/www/teaching_panel/frontend/build",
        "sudo chmod -R 755 /var/www/teaching_panel/frontend/build",
        "sudo chown -R www-data:www-data /var/www/teaching_panel/teaching_panel/staticfiles",
        "sudo chmod -R 755 /var/www/teaching_panel/teaching_panel/staticfiles",
        "sudo chown -R www-data:www-data /var/www/teaching_panel/teaching_panel/media",
        "sudo chmod -R 755 /var/www/teaching_panel/teaching_panel/media"
    )
    
    foreach ($cmd in $commands) {
        Invoke-RemoteCommand -Command $cmd -Description "Исправление прав"
    }
    
    Write-Status "Права исправлены" "Success"
}
```

**Использовать после:**
- Сборки фронтенда
- collectstatic
- Любых операций с файлами

**Время:** 30 минут  
**Риск:** Низкий

---

### Task 1.4: Реализовать atomic frontend deploy

**Добавить функцию:**
```powershell
function Deploy-Frontend-Atomic {
    Write-Host ""
    Write-Host "════════════════════════════════════════" -ForegroundColor Cyan
    Write-Host "  АТОМАРНЫЙ ДЕПЛОЙ ФРОНТЕНДА" -ForegroundColor Cyan
    Write-Host "════════════════════════════════════════" -ForegroundColor Cyan
    
    # 1. Проверить что билд существует локально
    $localBuild = "$PSScriptRoot\frontend\build"
    if (-not (Test-Path "$localBuild\index.html")) {
        Write-Status "Билд не найден! Запустите: cd frontend && npm run build" "Error"
        return $false
    }
    
    # 2. Создать временную директорию на сервере
    $timestamp = Get-Date -Format "yyyyMMdd_HHmmss"
    $tempBuild = "/var/www/teaching_panel/frontend/build_new_$timestamp"
    
    Write-Status "Копирование билда во временную директорию..." "Info"
    ssh $SERVER "mkdir -p $tempBuild"
    
    # 3. Загрузить файлы
    scp -r "$localBuild\*" "${SERVER}:${tempBuild}/"
    
    if ($LASTEXITCODE -ne 0) {
        Write-Status "SCP завершился с ошибкой!" "Error"
        ssh $SERVER "rm -rf $tempBuild"
        return $false
    }
    
    # 4. Проверить что билд валидный
    $indexCheck = ssh $SERVER "test -f $tempBuild/index.html && echo 'ok' || echo 'fail'"
    $jsCheck = ssh $SERVER "grep -oP 'main\.\w+\.js' $tempBuild/index.html | head -1"
    $jsExists = ssh $SERVER "test -f $tempBuild/static/js/$jsCheck && echo 'ok' || echo 'fail'"
    
    if ($indexCheck -ne "ok" -or $jsExists -ne "ok") {
        Write-Status "Новый билд невалиден! index=$indexCheck js=$jsExists" "Error"
        ssh $SERVER "rm -rf $tempBuild"
        return $false
    }
    
    # 5. Исправить права ПЕРЕД заменой
    ssh $SERVER "sudo chown -R www-data:www-data $tempBuild && sudo chmod -R 755 $tempBuild"
    
    # 6. АТОМАРНАЯ ЗАМЕНА (мгновенно!)
    Write-Status "Атомарная замена билда..." "Info"
    $swapResult = ssh $SERVER @"
cd /var/www/teaching_panel/frontend && \
sudo mv build build_old_$timestamp 2>/dev/null; \
sudo mv $tempBuild build && \
sudo nginx -s reload && \
echo 'SWAP_OK'
"@
    
    if ($swapResult -notmatch "SWAP_OK") {
        Write-Status "Замена провалилась! Откат..." "Error"
        ssh $SERVER "cd /var/www/teaching_panel/frontend && sudo mv build_old_$timestamp build"
        return $false
    }
    
    # 7. Проверить что сайт работает
    if (-not (Test-SiteHealth)) {
        Write-Status "Сайт не работает! Откат..." "Error"
        ssh $SERVER @"
cd /var/www/teaching_panel/frontend && \
sudo rm -rf build && \
sudo mv build_old_$timestamp build && \
sudo nginx -s reload
"@
        return $false
    }
    
    # 8. Очистка старых билдов (оставляем 2 последних)
    ssh $SERVER "cd /var/www/teaching_panel/frontend && ls -dt build_old_* 2>/dev/null | tail -n +3 | xargs -r sudo rm -rf"
    
    Write-Status "Frontend успешно задеплоен!" "Success"
    return $true
}
```

**Время:** 2 часа  
**Риск:** Средний (тестировать осторожно)

---

## ⚡ Фаза 2: Создание единого скрипта

### Task 2.1: Создать deploy_unified.ps1

**Структура:**
```powershell
# ============================================================
# Teaching Panel - Единый надежный скрипт деплоя
# ============================================================
# Требования:
# - PowerShell 7+
# - SSH доступ к серверу (алиас 'tp')
# - Права sudo на сервере
# ============================================================

param(
    [ValidateSet('full', 'backend', 'frontend', 'quick', 'rollback')]
    [string]$Action = 'menu',
    
    [switch]$SkipHealthCheck,
    [switch]$SkipBackup,
    [switch]$DryRun
)

# КОНФИГУРАЦИЯ
$SERVER = "tp"
$REMOTE_DIR = "/var/www/teaching_panel"
$SERVICE_NAME = "teaching_panel"  # ✅ ПРАВИЛЬНОЕ ИМЯ
$SITE_URL = "https://lectiospace.ru"

# БЭКАП НАСТРОЙКИ
$BACKUP_ENABLED = -not $SkipBackup
$BACKUP_DIR = "$REMOTE_DIR/backups"

# HEALTH CHECK НАСТРОЙКИ
$HEALTH_CHECK_ENABLED = -not $SkipHealthCheck
$HEALTH_CHECK_RETRIES = 5
$HEALTH_CHECK_DELAY = 3

# ... остальной код ...
```

**Основные функции:**
1. `Test-Prerequisites` - проверка окружения
2. `Test-SSHConnection` - проверка подключения
3. `Test-SiteHealth` - health check
4. `Backup-Database` - бэкап БД
5. `Backup-Code` - бэкап кода
6. `Deploy-Backend` - деплой бэкенда
7. `Deploy-Frontend-Atomic` - атомарный деплой фронтенда
8. `Deploy-Full` - полный деплой
9. `Rollback-ToBackup` - откат к бэкапу
10. `Send-TelegramNotification` - уведомления

**Время:** 4-6 часов  
**Риск:** Средний (требует тщательного тестирования)

---

### Task 2.2: Пометить устаревшие скрипты как deprecated

**Создать файл DEPRECATED_SCRIPTS.md:**
```markdown
# ⚠️ Устаревшие скрипты деплоя

Следующие скрипты больше НЕ используются и будут удалены в будущих версиях:

## ❌ НЕ используй:
- `deploy.ps1` (неверные имена сервисов)
- `deploy_simple.ps1` (неверные имена сервисов)
- `deploy_quick.ps1` (нет health checks)
- `deploy_multi.ps1` (неверные имена сервисов)
- `deploy_final.ps1` (устарел)
- `deploy_fast.ps1` (устарел)

## ✅ Используй вместо этого:
- **`deploy_unified.ps1`** - единый надежный скрипт деплоя
- **`deploy_to_production.ps1`** - безопасный деплой с откатом (альтернатива)

## 📝 Миграция:
```powershell
# Старый способ
.\deploy.ps1 production-russia

# Новый способ
.\deploy_unified.ps1 -Action full
```
```

**Добавить в начало устаревших скриптов:**
```powershell
Write-Host "⚠️ ВНИМАНИЕ: Этот скрипт устарел!" -ForegroundColor Red
Write-Host "Используй вместо него: .\deploy_unified.ps1" -ForegroundColor Yellow
Write-Host "Нажми Ctrl+C чтобы остановить, или Enter чтобы продолжить (не рекомендуется)" -ForegroundColor Yellow
Read-Host
```

**Время:** 1 час  
**Риск:** Низкий

---

## 📝 Фаза 3: Долгосрочные улучшения

### Task 3.1: Написать документацию

**Файлы для создания:**
1. `DEPLOY_GUIDE.md` - полное руководство по деплою
2. `DEPLOY_TROUBLESHOOTING.md` - решение проблем
3. `DEPLOY_CHECKLIST.md` - чек-лист перед деплоем

**Время:** 2-3 часа

---

### Task 3.2: Добавить pre-deployment checks

**Проверки перед деплоем:**
- ✅ Git status (нет uncommitted changes)
- ✅ Tests passed (pytest, jest)
- ✅ Linting passed (flake8, eslint)
- ✅ Миграции созданы (makemigrations --check)
- ✅ Dependencies updated (pip freeze, npm audit)
- ✅ Место на диске (>10GB свободно)
- ✅ Production работает (health check before deploy)

**Время:** 2 часа

---

### Task 3.3: Добавить Telegram уведомления

**Интеграция с мониторингом:**
```powershell
function Send-DeployNotification {
    param(
        [ValidateSet('start', 'success', 'failure', 'rollback')]
        [string]$Status,
        [string]$Message = ""
    )
    
    $emoji = switch ($Status) {
        'start' { '🚀' }
        'success' { '✅' }
        'failure' { '❌' }
        'rollback' { '🔄' }
    }
    
    $text = "$emoji LECTIO DEPLOY $($Status.ToUpper())`n`n$Message`n`n🕐 $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')"
    
    # ... отправка в Telegram через API ...
}
```

**Время:** 1 час

---

## 🔄 План тестирования

### Этап 1: Unit тесты (локально)
- Проверить все функции скриптов
- Проверить обработку ошибок
- Проверить dry-run режим

### Этап 2: Staging тест
- Задеплоить на staging
- Проверить frontend
- Проверить backend
- Проверить health checks
- Проверить rollback

### Этап 3: Production тест (в low-traffic время)
- Выбрать время с минимальной нагрузкой (ночь)
- Задеплоить небольшое изменение
- Мониторить логи
- Быть готовым к откату

---

## 📊 Метрики успеха

### До исправлений:
- ❌ Деплой падает ~30% случаев
- ❌ Downtime при деплое frontend: 15-30 сек
- ❌ Нет автоматического отката
- ❌ 16 разных скриптов деплоя

### После исправлений (цель):
- ✅ Деплой успешен в >95% случаев
- ✅ Downtime при деплое frontend: <1 сек
- ✅ Автоматический откат при ошибках
- ✅ 1-2 основных скрипта деплоя
- ✅ Health checks перед и после
- ✅ Telegram уведомления

---

## 🚀 План действий на сегодня

1. ✅ Исправить имена сервисов (30 мин)
2. ✅ Добавить health checks в auto_deploy.ps1 (1 час)
3. ✅ Добавить fix_permissions (30 мин)
4. ✅ Протестировать на staging (30 мин)

**Итого:** ~2.5 часа на критические исправления

**Завтра:**
5. Создать deploy_unified.ps1 (4-6 часов)
6. Протестировать (2 часа)
7. Документация (2 часа)

---

## ⚠️ Риски и митигация

### Риск 1: Сломать production при тестировании
**Митигация:** 
- Всегда тестировать на staging первым
- Использовать DryRun режим
- Делать бэкап перед любыми изменениями

### Риск 2: Новые скрипты будут содержать баги
**Митигация:**
- Тщательное code review
- Поэтапное внедрение
- Сохранить старые скрипты как fallback

### Риск 3: Пользователи продолжат использовать старые скрипты
**Митигация:**
- Добавить предупреждения в старые скрипты
- Обновить документацию
- Обучение команды

---

**Документ подготовлен:** GitHub Copilot AI  
**Статус:** Ready for implementation  
**Приоритет:** CRITICAL
