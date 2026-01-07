$ErrorActionPreference = 'Stop'

$sshAlias = 'tp'
# Base URL for API calls. Override with env var `TP_BASE_URL`.
# Default points to the current temporary host.
$baseUrl = if ($env:TP_BASE_URL -and $env:TP_BASE_URL.Trim()) { $env:TP_BASE_URL.Trim().TrimEnd('/') } else { 'https://lectio.tw1.ru' }

function Get-AccessTokenForEmail {
    param([Parameter(Mandatory=$true)][string]$Email)

        # Генерируем access token на сервере через Django (без паролей).
        # Важно: не выводим токен в консоль, только возвращаем значение.
        $remoteScript = @'
set -e

if [ -d /var/www/teaching_panel/teaching_panel ]; then
    cd /var/www/teaching_panel/teaching_panel
elif [ -d /var/www/teaching_panel ]; then
    cd /var/www/teaching_panel
else
    echo PROJECT_DIR_NOT_FOUND
    exit 2
fi

if [ -x ../venv/bin/python ]; then
    PY=../venv/bin/python
elif [ -x venv/bin/python ]; then
    PY=venv/bin/python
elif [ -x /var/www/teaching_panel/venv/bin/python ]; then
    PY=/var/www/teaching_panel/venv/bin/python
else
    echo VENV_PY_NOT_FOUND
    exit 3
fi

$PY - <<'PYEOF'
import os
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'teaching_panel.settings')

import django
django.setup()

from django.contrib.auth import get_user_model
from rest_framework_simplejwt.tokens import RefreshToken

email = "__EMAIL__"
User = get_user_model()
u = User.objects.get(email=email)
print(str(RefreshToken.for_user(u).access_token))
PYEOF

echo AFTER_HEREDOC_OK
'@

    $remoteScript = $remoteScript.Replace('__EMAIL__', $Email)
    $remoteScriptNoCr = $remoteScript -replace "`r", ""

    # Debug: сохраняем фактически отправляемый bash-скрипт локально
    $remoteScriptNoCr | Out-File -FilePath "prod_join_remote_script_preview.sh" -Encoding utf8

    $rawOutput = $remoteScriptNoCr | & ssh $sshAlias bash -s
    if ($LASTEXITCODE -ne 0) {
        throw "Не удалось получить JWT access token на сервере (ssh exit=$LASTEXITCODE)"
    }

    $text = ($rawOutput | Out-String)
    $m = [regex]::Match($text, '[A-Za-z0-9_\-]+\.[A-Za-z0-9_\-]+\.[A-Za-z0-9_\-]+')
    if (-not $m.Success) {
        throw "Не удалось распарсить JWT из вывода сервера"
    }

    return $m.Value.Trim()
}

function New-TempLessonForStudent {
    param(
        [Parameter(Mandatory=$true)][string]$StudentEmail,
        [Parameter(Mandatory=$true)][string]$Title,
        [Parameter(Mandatory=$true)][string]$JoinUrl
    )

    $py = @'
import os
from datetime import timedelta

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'teaching_panel.settings')
import django
django.setup()

from django.contrib.auth import get_user_model
from django.utils import timezone
from schedule.models import Group, Lesson

student_email = "__STUDENT_EMAIL__"
title = "__TITLE__"
join_url = "__JOIN_URL__"

User = get_user_model()
student = User.objects.get(email=student_email)
group = Group.objects.filter(students=student).order_by('id').first()
if not group:
    print('NO_GROUP_FOR_STUDENT')
    raise SystemExit(4)

start = timezone.now() + timedelta(minutes=5)
end = start + timedelta(minutes=60)

lesson = Lesson.objects.create(
    title=title,
    group=group,
    teacher=group.teacher,
    start_time=start,
    end_time=end,
    zoom_join_url=join_url,
)

print(f'SMOKE_GROUP_ID={group.id}')
print(f'SMOKE_LESSON_ID={lesson.id}')
'@

    $py = $py.Replace('__STUDENT_EMAIL__', $StudentEmail)
    $py = $py.Replace('__TITLE__', $Title)
    $py = $py.Replace('__JOIN_URL__', $JoinUrl)
    $pyB64 = [Convert]::ToBase64String([Text.Encoding]::UTF8.GetBytes($py))

    $remoteScript = @'
set -e

if [ -d /var/www/teaching_panel/teaching_panel ]; then
  cd /var/www/teaching_panel/teaching_panel
elif [ -d /var/www/teaching_panel ]; then
  cd /var/www/teaching_panel
else
  echo PROJECT_DIR_NOT_FOUND
  exit 2
fi

if [ -x ../venv/bin/python ]; then
  PY=../venv/bin/python
elif [ -x venv/bin/python ]; then
  PY=venv/bin/python
elif [ -x /var/www/teaching_panel/venv/bin/python ]; then
  PY=/var/www/teaching_panel/venv/bin/python
else
  echo VENV_PY_NOT_FOUND
  exit 3
fi

"$PY" -c "import base64; exec(base64.b64decode('__PY_B64__').decode('utf-8'))"
'@

    $remoteScript = $remoteScript.Replace('__PY_B64__', $pyB64)
    $remoteScriptNoCr = $remoteScript -replace "`r", ""
    $remoteScriptNoCr | Out-File -FilePath "prod_join_temp_lesson_script_preview.sh" -Encoding utf8

    $out = $remoteScriptNoCr | & ssh $sshAlias bash -s
    if ($LASTEXITCODE -ne 0) {
        throw "Не удалось создать временный урок на сервере (ssh exit=$LASTEXITCODE)"
    }

    $text = ($out | Out-String)
    $m = [regex]::Match($text, 'SMOKE_LESSON_ID=(\d+)')
    if (-not $m.Success) {
        throw "Не удалось получить SMOKE_LESSON_ID из вывода сервера"
    }

    return [long]$m.Groups[1].Value
}

function Remove-TempLesson {
    param([Parameter(Mandatory=$true)][long]$LessonId)

    $py = @'
import os
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'teaching_panel.settings')
import django
django.setup()

from schedule.models import Lesson

lid = int('__LESSON_ID__')
Lesson.objects.filter(id=lid).delete()
print('SMOKE_LESSON_DELETED=1')
'@

    $py = $py.Replace('__LESSON_ID__', $LessonId.ToString())
    $pyB64 = [Convert]::ToBase64String([Text.Encoding]::UTF8.GetBytes($py))

    $remoteScript = @'
set -e
if [ -d /var/www/teaching_panel/teaching_panel ]; then
  cd /var/www/teaching_panel/teaching_panel
elif [ -d /var/www/teaching_panel ]; then
  cd /var/www/teaching_panel
else
  exit 2
fi

if [ -x ../venv/bin/python ]; then
  PY=../venv/bin/python
elif [ -x venv/bin/python ]; then
  PY=venv/bin/python
elif [ -x /var/www/teaching_panel/venv/bin/python ]; then
  PY=/var/www/teaching_panel/venv/bin/python
else
  exit 3
fi

"$PY" -c "import base64; exec(base64.b64decode('__PY_B64__').decode('utf-8'))"
'@

    $remoteScript = $remoteScript.Replace('__PY_B64__', $pyB64)
    $remoteScriptNoCr = $remoteScript -replace "`r", ""
    $null = $remoteScriptNoCr | & ssh $sshAlias bash -s
}

$studentEmail = 'syrnik1307@gmail.com'
$studentToken = Get-AccessTokenForEmail -Email $studentEmail
$headers = @{ Authorization = "Bearer $studentToken" }

Write-Host "TOKEN_OK len=$($studentToken.Length)" -ForegroundColor DarkGray

Write-Host "ME запрос..." -ForegroundColor Cyan
$me = Invoke-RestMethod -Method Get -Uri "$baseUrl/api/me/" -Headers $headers
Write-Host "ME_OK email=$($me.email) role=$($me.role)" -ForegroundColor Green

$startDate = Get-Date
$endDate = $startDate.AddDays(7)
$startIso = $startDate.ToString('yyyy-MM-dd') + 'T00:00:00'
$endIso = $endDate.ToString('yyyy-MM-dd') + 'T23:59:59'
$query = "start=$([uri]::EscapeDataString($startIso))&end=$([uri]::EscapeDataString($endIso))&include_recurring=true"

Write-Host "Загрузка уроков (сегодня + 7 дней)..." -ForegroundColor Cyan
$lessonsResp = Invoke-RestMethod -Method Get -Uri "$baseUrl/api/schedule/lessons/?$query" -Headers $headers

$items = @()
if ($null -ne $lessonsResp.results) {
    $items = @($lessonsResp.results)
} elseif ($lessonsResp -is [System.Collections.IEnumerable]) {
    $items = @($lessonsResp)
}

function TryParseDateTime($value) {
    try {
        return [DateTimeOffset]::Parse($value)
    } catch {
        return $null
    }
}

$real = $items |
    Where-Object { $_ -ne $null -and $_.PSObject.Properties['id'] -and (($_.id -is [int]) -or ($_.id -is [long])) } |
    ForEach-Object {
        $dt = TryParseDateTime $_.start_time
        if ($null -ne $dt) {
            [PSCustomObject]@{
                id = [long]$_.id
                start = $dt
                title = $_.title
            }
        }
    } |
    Sort-Object start

Write-Output "LESSONS_TOTAL=$($items.Count) REAL_NUMERIC=$($real.Count)"
$items | Select-Object -First 6 | ForEach-Object {
    $idVal = $null
    try { $idVal = $_.id } catch { }
    $typeName = $null
    if ($null -ne $idVal) {
        try { $typeName = $idVal.GetType().FullName } catch { }
    }
    Write-Output "ITEM id=$idVal type=$typeName"
}
$real | Select-Object -First 6 | ForEach-Object { Write-Host "LESSON $($_.id) $($_.start.ToString('o')) $($_.title)" }

if ($real.Count -eq 0) {
    Write-Host "REAL_NUMERIC=0, создаю временный реальный урок для smoke..." -ForegroundColor Yellow
    $tempTitle = "SMOKE Join Test $(Get-Date -Format 'yyyyMMdd_HHmmss')"
    $tempJoinUrl = "https://example.com/zoom-join-smoke"
    $tempLessonId = New-TempLessonForStudent -StudentEmail $studentEmail -Title $tempTitle -JoinUrl $tempJoinUrl
    Write-Host "TEMP_LESSON_CREATED id=$tempLessonId" -ForegroundColor Yellow

    try {
        $joinUrl = "$baseUrl/api/schedule/lessons/$tempLessonId/join/"
        $join = Invoke-RestMethod -Method Post -Uri $joinUrl -Headers $headers -ContentType 'application/json' -Body '{}'
        $hasUrl = [bool]$join.zoom_join_url
        Write-Host "JOIN_TEMP_OK lesson=$tempLessonId has_zoom_join_url=$hasUrl" -ForegroundColor Green
    } finally {
        Remove-TempLesson -LessonId $tempLessonId
        Write-Host "TEMP_LESSON_DELETED id=$tempLessonId" -ForegroundColor DarkGray
    }

    return
}

$found = $false
foreach ($l in ($real | Select-Object -First 8)) {
    $joinUrl = "$baseUrl/api/schedule/lessons/$($l.id)/join/"
    try {
        $join = Invoke-RestMethod -Method Post -Uri $joinUrl -Headers $headers -ContentType 'application/json' -Body '{}' 
        $hasUrl = [bool]$join.zoom_join_url
        Write-Host "JOIN_OK lesson=$($l.id) has_zoom_join_url=$hasUrl" -ForegroundColor Green
        $found = $true
        break
    } catch {
        $status = $null
        try { $status = [int]$_.Exception.Response.StatusCode.value__ } catch { }
        $detail = $null
        try {
            $reader = New-Object System.IO.StreamReader($_.Exception.Response.GetResponseStream())
            $body = $reader.ReadToEnd()
            if ($body) {
                $parsed = $body | ConvertFrom-Json -ErrorAction SilentlyContinue
                if ($parsed -and $parsed.detail) { $detail = $parsed.detail }
            }
        } catch { }

        if ($detail) {
            Write-Host "JOIN_TRY lesson=$($l.id) code=$status detail=$detail" -ForegroundColor DarkYellow
        } else {
            Write-Host "JOIN_TRY lesson=$($l.id) code=$status" -ForegroundColor DarkYellow
        }
    }
}

if (-not $found) {
    Write-Host "JOIN_RESULT=NO_200_FOUND (скорее всего учитель еще не стартовал урок)" -ForegroundColor Yellow
}
