param(
    [string]$SSHAlias = 'tp',
    [string]$Email = $null,
    [string]$Password = 'TestPass123!',
    [string]$FirstName = 'Smoke',
    [string]$LastName = 'Student',
    [switch]$ResetPassword
)

$ErrorActionPreference = 'Stop'

if (-not $Email) {
    $stamp = (Get-Date).ToString('yyyyMMdd')
    $Email = "smoke_student_$stamp@test.com"
}

function Invoke-RemotePy {
    param([Parameter(Mandatory=$true)][string]$Py)

    $b64 = [Convert]::ToBase64String([Text.Encoding]::UTF8.GetBytes($Py))

    $remoteScript = @'
set -e

cd /var/www/teaching_panel/teaching_panel

if [ -x ../venv/bin/python ]; then
  PY=../venv/bin/python
else
  echo VENV_PY_NOT_FOUND
  exit 3
fi

"$PY" manage.py shell -c "import base64; exec(base64.b64decode('__B64__').decode('utf-8'))"
'@

    $remoteScript = $remoteScript.Replace('__B64__', $b64) -replace "`r", ""
    $out = $remoteScript | & ssh $SSHAlias bash -s
    if ($LASTEXITCODE -ne 0) {
        throw "Remote python failed (ssh exit=$LASTEXITCODE)"
    }
    return ($out | Out-String)
}

$py = @'
from django.contrib.auth import get_user_model

email = "__EMAIL__"
password = "__PASSWORD__"
first_name = "__FIRST__"
last_name = "__LAST__"
reset = __RESET__

User = get_user_model()

u = User.objects.filter(email=email).first()
if u is None:
    u = User.objects.create_user(email=email, password=password, role='student', first_name=first_name, last_name=last_name)
    print(f"CREATED id={u.id} email={u.email} role={u.role}")
else:
    if reset:
        u.set_password(password)
        u.first_name = first_name
        u.last_name = last_name
        if getattr(u, 'role', None) != 'student':
            u.role = 'student'
        u.save(update_fields=['password', 'first_name', 'last_name', 'role'])
        print(f"UPDATED id={u.id} email={u.email} role={u.role} (password reset)")
    else:
        print(f"EXISTS id={u.id} email={u.email} role={getattr(u,'role',None)}")
'@

$py = $py.Replace('__EMAIL__', $Email)
$py = $py.Replace('__PASSWORD__', $Password)
$py = $py.Replace('__FIRST__', $FirstName)
$py = $py.Replace('__LAST__', $LastName)
$py = $py.Replace('__RESET__', ($(if ($ResetPassword) { 'True' } else { 'False' })))

Write-Host "Creating student on prod..." -ForegroundColor Cyan
$out = Invoke-RemotePy -Py $py
Write-Output $out

Write-Host "Credentials:" -ForegroundColor Green
Write-Host "email: $Email"
Write-Host "password: $Password"
