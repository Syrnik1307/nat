# Quick Deploy Script for Teaching Panel
# Usage: .\deploy_quick.ps1 [options]
# Options:
#   -Frontend    Only rebuild frontend (fastest)
#   -Backend     Only restart backend services
#   -Full        Full deploy with migrations (default)
#   -NoBuild     Skip frontend build
#   -Status      Just check service status

param(
    [switch]$Frontend,
    [switch]$Backend, 
    [switch]$Full,
    [switch]$NoBuild,
    [switch]$Status
)

$Server = "tp"
$ProjectDir = "/var/www/teaching_panel"

function Write-Step($msg) {
    Write-Host "`n>> $msg" -ForegroundColor Cyan
}

function Write-Ok($msg) {
    Write-Host "[OK] $msg" -ForegroundColor Green
}

function Write-Err($msg) {
    Write-Host "[ERROR] $msg" -ForegroundColor Red
}

# Check SSH connection first
Write-Step "Checking SSH connection..."
$sshCheck = ssh -o ConnectTimeout=5 -o BatchMode=yes $Server "echo 'OK'" 2>&1
if ($sshCheck -ne "OK") {
    Write-Err "Cannot connect to server. Check your SSH config."
    exit 1
}
Write-Ok "SSH connected"

if ($Status) {
    Write-Step "Checking service status..."
    ssh $Server "systemctl is-active teaching_panel nginx; curl -sI https://lectiospace.ru | head -3"
    exit 0
}

# Git push local changes first
Write-Step "Pushing local changes to GitHub..."
git add -A
$hasChanges = git status --porcelain
if ($hasChanges) {
    $commitMsg = Read-Host "Commit message (or Enter for 'quick update')"
    if (-not $commitMsg) { $commitMsg = "quick update" }
    git commit -m $commitMsg
    git push origin main
    Write-Ok "Changes pushed"
} else {
    Write-Ok "No local changes"
}

# Build deploy command based on options
$commands = @()

# Always pull latest
$commands += "cd $ProjectDir && git pull origin main"

if (-not $Backend) {
    if (-not $NoBuild) {
        $commands += "cd $ProjectDir/frontend && npm run build"
        $commands += "chown -R www-data:www-data $ProjectDir/frontend/build && chmod -R 755 $ProjectDir/frontend/build"
    }
}

if (-not $Frontend) {
    $commands += "cd $ProjectDir/teaching_panel && source ../venv/bin/activate && pip install -r requirements.txt -q"
    
    if ($Full -or (-not $Frontend -and -not $Backend -and -not $NoBuild)) {
        $commands += "cd $ProjectDir/teaching_panel && source ../venv/bin/activate && python manage.py migrate --noinput"
        $commands += "cd $ProjectDir/teaching_panel && source ../venv/bin/activate && python manage.py collectstatic --noinput -v0"
    }
    
    $commands += "sudo systemctl restart teaching_panel"
}

$commands += "sudo systemctl reload nginx"
$commands += "echo '=== DEPLOY COMPLETE ==='"
$commands += "curl -sI https://lectiospace.ru | head -3"

$fullCmd = $commands -join " && "

Write-Step "Deploying to production..."
Write-Host "Commands: " -NoNewline
Write-Host ($commands.Count) -ForegroundColor Yellow -NoNewline
Write-Host " steps"

ssh $Server $fullCmd

if ($LASTEXITCODE -eq 0) {
    Write-Host "`n" 
    Write-Ok "Deploy successful! Site: https://lectiospace.ru"
} else {
    Write-Err "Deploy failed with exit code $LASTEXITCODE"
    exit 1
}
