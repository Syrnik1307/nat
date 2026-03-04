# ============================================================
# PRE-DEPLOY VALIDATION
# ============================================================
# Запускает ВСЕ проверки ПЕРЕД деплоем, чтобы не сломать прод.
# Использование: .\scripts\pre_deploy_check.ps1
# Или через VS Code task: "pre-deploy: local validate"
# ============================================================

$ErrorActionPreference = "Continue"
$failures = @()
$warnings = @()

function Test-Pass { param($msg) Write-Host "  PASS  $msg" -ForegroundColor Green }
function Test-Fail { param($msg) Write-Host "  FAIL  $msg" -ForegroundColor Red; $script:failures += $msg }
function Test-Warn { param($msg) Write-Host "  WARN  $msg" -ForegroundColor Yellow; $script:warnings += $msg }
function Test-Step { param($num, $msg) Write-Host "" ; Write-Host "[$num] $msg" -ForegroundColor Cyan }

Write-Host ""
Write-Host "============================================" -ForegroundColor Cyan
Write-Host "  PRE-DEPLOY VALIDATION                    " -ForegroundColor Cyan
Write-Host "============================================" -ForegroundColor Cyan

# ===== 1. GIT STATE =====
Test-Step 1 "Git state..."

$uncommitted = git status --porcelain 2>&1
if ($uncommitted) {
    $count = ($uncommitted | Measure-Object -Line).Lines
    Test-Warn "Есть $count незакоммиченных изменений"
} else {
    Test-Pass "Чистый git"
}

# Проверка tenant-кода
$tenantFiles = git diff HEAD --name-only 2>$null | Select-String "tenant"
if ($tenantFiles) {
    Test-Fail "Обнаружен tenant-код: $($tenantFiles -join ', ')"
}

# Проверка что мы на main/master
$branch = git branch --show-current 2>&1
if ($branch -notmatch "^(main|master)$") {
    Test-Warn "Текущая ветка: $branch (не main/master)"
} else {
    Test-Pass "Ветка: $branch"
}

# ===== 2. BACKEND CHECKS =====
Test-Step 2 "Backend checks..."

Push-Location "teaching_panel"

# Активируем venv
$venvActivate = "..\venv\Scripts\Activate.ps1"
if (Test-Path $venvActivate) {
    & $venvActivate
    Test-Pass "venv активирован"
} else {
    Test-Fail "venv не найден"
}

# Django check
$checkResult = python manage.py check 2>&1
if ($LASTEXITCODE -eq 0) {
    Test-Pass "Django check OK"
} else {
    Test-Fail "Django check failed: $($checkResult | Select-Object -First 3)"
}

# Миграции
$migrations = python manage.py showmigrations --plan 2>&1 | Select-String "\[ \]"
if ($migrations) {
    $migCount = ($migrations | Measure-Object).Count
    Test-Warn "$migCount непримененных миграций (проверь что безопасны!)"
    $migrations | Select-Object -First 5 | ForEach-Object { Write-Host "    $_" -ForegroundColor Yellow }
} else {
    Test-Pass "Все миграции применены"
}

# Проверяем что нет опасных миграций (DROP, DELETE, RemoveField)
$pendingMigrations = python manage.py showmigrations --plan 2>&1 | Select-String "\[ \]" | ForEach-Object {
    $_ -replace '.*\]\s+', '' -replace '\s+', ''
}
foreach ($mig in $pendingMigrations) {
    $parts = $mig -split '\.'
    if ($parts.Count -ge 2) {
        $app = $parts[0]
        $migName = $parts[1]
        $migFile = Get-ChildItem -Path "$app\migrations\${migName}.py" -ErrorAction SilentlyContinue
        if ($migFile) {
            $content = Get-Content $migFile.FullName -Raw
            if ($content -match "RemoveField|DeleteModel|DROP|TRUNCATE|RunSQL.*DELETE") {
                Test-Fail "ОПАСНАЯ миграция: $mig (удаление данных!)"
            }
        }
    }
}

# Django tests (быстрые)
$testResult = python manage.py test --failfast --parallel auto 2>&1
if ($LASTEXITCODE -eq 0) {
    Test-Pass "Django tests OK"
} else {
    $lastLines = $testResult | Select-Object -Last 5
    Test-Fail "Django tests failed: $($lastLines -join '; ')"
}

Pop-Location

# ===== 3. FRONTEND BUILD =====
Test-Step 3 "Frontend build..."

Push-Location "frontend"

if (Test-Path "node_modules") {
    Test-Pass "node_modules exists"
} else {
    Test-Fail "node_modules отсутствует (npm install?)"
}

# Build в CI-mode (warnings = errors)
$env:CI = "true"
$buildOutput = npm run build 2>&1
if ($LASTEXITCODE -eq 0) {
    Test-Pass "Frontend build OK"
    
    # Проверяем что build содержит нужные файлы
    if (Test-Path "build/index.html") {
        $jsFile = Select-String -Path "build/index.html" -Pattern 'main\.[a-f0-9]+\.js' -AllMatches | 
            ForEach-Object { $_.Matches.Value } | Select-Object -First 1
        if ($jsFile -and (Test-Path "build/static/js/$jsFile")) {
            Test-Pass "JS bundle: $jsFile"
        } else {
            Test-Fail "JS bundle отсутствует в build/"
        }
    } else {
        Test-Fail "index.html отсутствует в build/"
    }
} else {
    # Пробуем без CI (warnings допустимы)
    $env:CI = "false"
    $buildOutput2 = npm run build 2>&1
    if ($LASTEXITCODE -eq 0) {
        Test-Warn "Frontend build OK, но есть warnings (CI=true fails)"
    } else {
        Test-Fail "Frontend build FAILED"
        $buildOutput2 | Select-Object -Last 10 | ForEach-Object { Write-Host "    $_" -ForegroundColor Red }
    }
}
$env:CI = $null

Pop-Location

# ===== 4. PROD CONNECTIVITY =====
Test-Step 4 "Production connectivity..."

$sshCheck = ssh tp "echo SSH_OK" 2>&1
if ($sshCheck -match "SSH_OK") {
    Test-Pass "SSH подключение OK"
    
    # Проверяем что прод сейчас работает
    $prodHealth = ssh tp "curl -s -o /dev/null -w '%{http_code}' http://127.0.0.1:8000/api/health/ -H 'Host: lectiospace.ru' -H 'X-Forwarded-Proto: https' 2>/dev/null" 2>&1
    if ($prodHealth -eq "200") {
        Test-Pass "Production сейчас здоров (health=200)"
    } else {
        Test-Warn "Production сейчас НЕ здоров (health=$prodHealth) — деплой может починить или ухудшить"
    }
    
    # Диск
    $diskUsage = ssh tp "df / | awk 'NR==2{gsub(/%/,\"\"); print \$5}'" 2>&1
    if ([int]$diskUsage -gt 85) {
        Test-Warn "Диск на проде: ${diskUsage}% (почисти перед деплоем)"
    } else {
        Test-Pass "Диск: ${diskUsage}%"
    }
    
    # Guardian установлен?
    $guardianExists = ssh tp "test -f /opt/lectio-monitor/guardian.sh && echo YES || echo NO" 2>&1
    if ($guardianExists -match "YES") {
        Test-Pass "Guardian установлен"
        $knownGood = ssh tp "cat /var/run/lectio-monitor/last_known_good 2>/dev/null" 2>&1
        if ($knownGood) {
            Write-Host "    Last known good: $knownGood" -ForegroundColor Gray
        }
    } else {
        Test-Warn "Guardian НЕ установлен (запусти task: guardian: install on prod)"
    }
} else {
    Test-Warn "SSH недоступен (не можем проверить прод)"
}

# ===== ИТОГО =====
Write-Host ""
Write-Host "============================================" -ForegroundColor Cyan

if ($failures.Count -eq 0 -and $warnings.Count -eq 0) {
    Write-Host "  ALL CLEAR — безопасно деплоить!" -ForegroundColor Green
} elseif ($failures.Count -eq 0) {
    Write-Host "  $($warnings.Count) warnings — деплой возможен, но осторожно" -ForegroundColor Yellow
} else {
    Write-Host "  $($failures.Count) FAILURES — НЕ ДЕПЛОЙ!" -ForegroundColor Red
    Write-Host "" 
    Write-Host "  Проблемы:" -ForegroundColor Red
    $failures | ForEach-Object { Write-Host "    - $_" -ForegroundColor Red }
}

if ($warnings.Count -gt 0 -and $failures.Count -gt 0) {
    Write-Host ""
    Write-Host "  Предупреждения:" -ForegroundColor Yellow
    $warnings | ForEach-Object { Write-Host "    - $_" -ForegroundColor Yellow }
}

Write-Host ""
Write-Host "============================================" -ForegroundColor Cyan
Write-Host ""

exit $failures.Count
