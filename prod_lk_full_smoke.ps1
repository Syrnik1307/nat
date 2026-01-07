$ErrorActionPreference = 'Stop'

$sshAlias = 'tp'
$baseUrl = if ($env:TP_BASE_URL -and $env:TP_BASE_URL.Trim()) { $env:TP_BASE_URL.Trim().TrimEnd('/') } else { 'https://lectio.tw1.ru' }

function Invoke-RemotePy {
    param([Parameter(Mandatory=$true)][string]$Py)

    $b64 = [Convert]::ToBase64String([Text.Encoding]::UTF8.GetBytes($Py))

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

"$PY" manage.py shell -c "import base64; exec(base64.b64decode('__B64__').decode('utf-8'))"
'@

    $remoteScript = $remoteScript.Replace('__B64__', $b64) -replace "`r", ""
    $out = $remoteScript | & ssh $sshAlias bash -s
    if ($LASTEXITCODE -ne 0) {
        throw "Remote python failed (ssh exit=$LASTEXITCODE)"
    }
    return ($out | Out-String)
}

function Get-AccessTokenForEmail {
    param([Parameter(Mandatory=$true)][string]$Email)

    $py = @'
import json
from django.contrib.auth import get_user_model
from rest_framework_simplejwt.tokens import RefreshToken

email = "__EMAIL__"
User = get_user_model()
u = User.objects.get(email=email)
print(str(RefreshToken.for_user(u).access_token))
'@
    $py = $py.Replace('__EMAIL__', $Email)

    $raw = Invoke-RemotePy -Py $py
    $m = [regex]::Match($raw, '[A-Za-z0-9_\-]+\.[A-Za-z0-9_\-]+\.[A-Za-z0-9_\-]+')
    if (-not $m.Success) { throw "JWT parse failed for $Email" }
    return $m.Value.Trim()
}

function HttpGet {
    param(
        [Parameter(Mandatory=$true)][string]$Url,
        [Parameter(Mandatory=$true)][hashtable]$Headers
    )
    try {
        $resp = Invoke-WebRequest -Method Get -Uri $Url -Headers $Headers -TimeoutSec 25
        return [PSCustomObject]@{ ok=$true; status=$resp.StatusCode; body=$resp.Content }
    } catch {
        $status = $null
        $body = $null
        try { $status = [int]$_.Exception.Response.StatusCode.value__ } catch { }
        try {
            $reader = New-Object System.IO.StreamReader($_.Exception.Response.GetResponseStream())
            $body = $reader.ReadToEnd()
        } catch { }
        return [PSCustomObject]@{ ok=$false; status=$status; body=$body }
    }
}

function HttpGetJson {
    param(
        [Parameter(Mandatory=$true)][string]$Url,
        [Parameter(Mandatory=$true)][hashtable]$Headers
    )
    $r = HttpGet -Url $Url -Headers $Headers
    if (-not $r.ok) { return [PSCustomObject]@{ ok=$false; status=$r.status; json=$null; raw=$r.body } }
    try {
        return [PSCustomObject]@{ ok=$true; status=$r.status; json=($r.body | ConvertFrom-Json); raw=$r.body }
    } catch {
        return [PSCustomObject]@{ ok=$false; status=$r.status; json=$null; raw=$r.body }
    }
}

Write-Host "=== Discover users (admin/teacher/student) ===" -ForegroundColor Cyan
$pyDiscover = @'
import json
from django.contrib.auth import get_user_model

User = get_user_model()
admin = User.objects.filter(role='admin').order_by('id').first()
teacher = User.objects.filter(role='teacher').order_by('id').first()
student = User.objects.filter(role='student').order_by('id').first()

print(json.dumps({
  'admin': {'id': getattr(admin,'id',None), 'email': getattr(admin,'email',None)},
  'teacher': {'id': getattr(teacher,'id',None), 'email': getattr(teacher,'email',None)},
  'student': {'id': getattr(student,'id',None), 'email': getattr(student,'email',None)},
}))
'@
$discoverRaw = Invoke-RemotePy -Py $pyDiscover
$discoverJsonLine = ($discoverRaw -split "`n" | Where-Object { $_.Trim().StartsWith('{') } | Select-Object -First 1)
if (-not $discoverJsonLine) { throw "Failed to parse discovery output" }
$users = $discoverJsonLine | ConvertFrom-Json

$adminEmail = [string]$users.admin.email
$teacherEmail = [string]$users.teacher.email
$studentEmail = [string]$users.student.email

Write-Host "ADMIN email=$adminEmail" -ForegroundColor DarkGray
Write-Host "TEACHER email=$teacherEmail" -ForegroundColor DarkGray
Write-Host "STUDENT email=$studentEmail" -ForegroundColor DarkGray

if (-not $adminEmail -or -not $teacherEmail -or -not $studentEmail) {
    throw "Missing at least one user role in DB (admin/teacher/student)"
}

Write-Host "=== Mint JWT tokens ===" -ForegroundColor Cyan
$adminTok = Get-AccessTokenForEmail -Email $adminEmail
$teacherTok = Get-AccessTokenForEmail -Email $teacherEmail
$studentTok = Get-AccessTokenForEmail -Email $studentEmail

$adminHeaders = @{ Authorization = "Bearer $adminTok" }
$teacherHeaders = @{ Authorization = "Bearer $teacherTok" }
$studentHeaders = @{ Authorization = "Bearer $studentTok" }

function Assert-Ok {
    param([string]$Name, $Resp)
    if (-not $Resp.ok -or $Resp.status -lt 200 -or $Resp.status -ge 300) {
        $snippet = if ($Resp.raw) { ($Resp.raw | Out-String).Substring(0, [Math]::Min(300, ($Resp.raw | Out-String).Length)) } else { '' }
        throw "$Name FAILED status=$($Resp.status) body_snippet=$snippet"
    }
}

Write-Host "\n=== STUDENT LK (API) ===" -ForegroundColor Green
$me = HttpGetJson -Url "$baseUrl/api/me/" -Headers $studentHeaders; Assert-Ok -Name "student /api/me" -Resp $me
Write-Host "student.me.role=$($me.json.role)" -ForegroundColor DarkGray

$hw = HttpGetJson -Url "$baseUrl/api/homework/" -Headers $studentHeaders; Assert-Ok -Name "student /api/homework" -Resp $hw
$hwList = @()
if ($hw.json.results) { $hwList = @($hw.json.results) } elseif ($hw.json -is [System.Collections.IEnumerable]) { $hwList = @($hw.json) }
Write-Host "student.homework.count=$($hwList.Count)" -ForegroundColor DarkGray
if ($hwList.Count -gt 0) {
    $hid = $hwList[0].id
    $hwd = HttpGetJson -Url "$baseUrl/api/homework/$hid/" -Headers $studentHeaders; Assert-Ok -Name "student /api/homework/{id}" -Resp $hwd
    $q0 = $hwd.json.questions | Select-Object -First 1
    if ($q0) {
        $hasPoints = $q0.PSObject.Properties.Name -contains 'points'
        Write-Host "student.homework.firstQuestion.has_points=$hasPoints" -ForegroundColor DarkGray
    }
}

$subm = HttpGetJson -Url "$baseUrl/api/submissions/" -Headers $studentHeaders; Assert-Ok -Name "student /api/submissions" -Resp $subm
Write-Host "student.submissions.status=$($subm.status)" -ForegroundColor DarkGray

Write-Host "\n=== TEACHER LK (API) ===" -ForegroundColor Green
$meT = HttpGetJson -Url "$baseUrl/api/me/" -Headers $teacherHeaders; Assert-Ok -Name "teacher /api/me" -Resp $meT
Write-Host "teacher.me.role=$($meT.json.role)" -ForegroundColor DarkGray

$sub = HttpGetJson -Url "$baseUrl/api/subscription/" -Headers $teacherHeaders
if ($sub.ok) {
    Write-Host "teacher.subscription.status=$($sub.json.status) expires_at=$($sub.json.expires_at)" -ForegroundColor DarkGray
} else {
    Write-Host "teacher.subscription: status=$($sub.status)" -ForegroundColor Yellow
}

$groups = HttpGetJson -Url "$baseUrl/api/groups/" -Headers $teacherHeaders; Assert-Ok -Name "teacher /api/groups" -Resp $groups
$glist = @($groups.json.results ?? @())
Write-Host "teacher.groups.results=$($glist.Count)" -ForegroundColor DarkGray

$less = HttpGetJson -Url "$baseUrl/api/schedule/lessons/?start=2025-01-01T00:00:00&end=2026-12-31T23:59:59&include_recurring=true" -Headers $teacherHeaders
if ($less.ok) {
    $ll = @($less.json.results ?? @())
    Write-Host "teacher.lessons.results=$($ll.Count)" -ForegroundColor DarkGray
} else {
    Write-Host "teacher.lessons: status=$($less.status)" -ForegroundColor Yellow
}

$hwT = HttpGetJson -Url "$baseUrl/api/homework/" -Headers $teacherHeaders
if ($hwT.ok) {
    $hwtList = @($hwT.json.results ?? @())
    Write-Host "teacher.homework.results=$($hwtList.Count)" -ForegroundColor DarkGray
    if ($hwtList.Count -gt 0) {
        $hidT = $hwtList[0].id
        $hwdT = HttpGetJson -Url "$baseUrl/api/homework/$hidT/" -Headers $teacherHeaders
        if ($hwdT.ok) {
            $tq0 = $hwdT.json.questions | Select-Object -First 1
            if ($tq0) {
                $hasPointsT = $tq0.PSObject.Properties.Name -contains 'points'
                $hasTypeT = $tq0.PSObject.Properties.Name -contains 'question_type'
                Write-Host "teacher.homework.firstQuestion.has_points=$hasPointsT has_question_type=$hasTypeT" -ForegroundColor DarkGray
            }
        } else {
            Write-Host "teacher.homework.detail: status=$($hwdT.status)" -ForegroundColor Yellow
        }
    }
} else {
    Write-Host "teacher.homework: status=$($hwT.status)" -ForegroundColor Yellow
}

$submT = HttpGetJson -Url "$baseUrl/api/submissions/" -Headers $teacherHeaders
if ($submT.ok) {
    $submListT = @($submT.json.results ?? @())
    Write-Host "teacher.submissions.results=$($submListT.Count)" -ForegroundColor DarkGray
} else {
    Write-Host "teacher.submissions: status=$($submT.status)" -ForegroundColor Yellow
}

Write-Host "\n=== ADMIN LK (API) ===" -ForegroundColor Green
$meA = HttpGetJson -Url "$baseUrl/api/me/" -Headers $adminHeaders; Assert-Ok -Name "admin /api/me" -Resp $meA
Write-Host "admin.me.role=$($meA.json.role)" -ForegroundColor DarkGray

$admTeach = HttpGetJson -Url "$baseUrl/accounts/api/admin/teachers/?page=1&page_size=5" -Headers $adminHeaders; Assert-Ok -Name "admin teachers list" -Resp $admTeach
Write-Host "admin.teachers.results=$(@($admTeach.json.results).Count)" -ForegroundColor DarkGray

$admStud = HttpGetJson -Url "$baseUrl/accounts/api/admin/students/?page=1&page_size=5&status=active" -Headers $adminHeaders; Assert-Ok -Name "admin students list" -Resp $admStud
Write-Host "admin.students.results=$(@($admStud.json.results).Count)" -ForegroundColor DarkGray

$admSubs = HttpGetJson -Url "$baseUrl/api/admin/subscriptions/" -Headers $adminHeaders
if ($admSubs.ok) {
    $subsList = @($admSubs.json.results ?? @())
    Write-Host "admin.subscriptions.results=$($subsList.Count)" -ForegroundColor DarkGray
} else {
    Write-Host "admin.subscriptions: status=$($admSubs.status)" -ForegroundColor Yellow
}

$storageStats = HttpGetJson -Url "$baseUrl/schedule/api/storage/statistics/" -Headers $adminHeaders
if ($storageStats.ok) {
    Write-Host "admin.storage.statistics.ok=1" -ForegroundColor DarkGray
} else {
    Write-Host "admin.storage.statistics: status=$($storageStats.status)" -ForegroundColor Yellow
}

Write-Host "\nOK: LK full smoke finished" -ForegroundColor Green
