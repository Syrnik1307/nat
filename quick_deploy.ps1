# Quick Deployment Script for Teaching Panel
# Автоматически выполняет deployment через SSH

$SERVER = "89.169.42.70"
$USER = "nat"  
$PASSWORD = "Syrnik13"

Write-Host "=== Teaching Panel Quick Deploy ===" -ForegroundColor Cyan
Write-Host ""

# Команда для deployment
$deployCmd = @"
cd /home/nat/teaching_panel && \
git pull origin main && \
source venv/bin/activate && \
pip install -r requirements.txt --quiet && \
python manage.py migrate && \
python manage.py collectstatic --noinput && \
sudo systemctl restart teaching_panel && \
sudo systemctl restart celery && \
sudo systemctl restart nginx && \
echo '✅ Deployment completed!' && \
sudo systemctl status teaching_panel --no-pager | head -10
"@

Write-Host "📡 Connecting to $SERVER..." -ForegroundColor Yellow

# Пробуем разные методы SSH
$methods = @(
    @{
        Name = "OpenSSH (встроенный)"
        Command = "ssh -o StrictHostKeyChecking=no ${USER}@${SERVER} `"$deployCmd`""
        UsePassword = $true
    },
    @{
        Name = "PuTTY plink"
        Command = "plink -batch -pw `"$PASSWORD`" ${USER}@${SERVER} `"$deployCmd`""
        UsePassword = $false
    }
)

$success = $false

foreach ($method in $methods) {
    Write-Host ""
    Write-Host "Trying: $($method.Name)..." -ForegroundColor Gray
    
    try {
        if ($method.UsePassword) {
            # Для OpenSSH используем expect-like поведение
            Write-Host "NOTE: You may need to enter password: $PASSWORD" -ForegroundColor Yellow
            $result = Invoke-Expression $method.Command
            $success = $LASTEXITCODE -eq 0
        } else {
            # Для plink пароль уже в команде
            $result = Invoke-Expression $method.Command
            $success = $LASTEXITCODE -eq 0
        }
        
        if ($success) {
            Write-Host ""
            Write-Host "✅ Deployment successful with $($method.Name)!" -ForegroundColor Green
            Write-Host $result
            break
        }
    } catch {
        Write-Host "❌ Failed: $_" -ForegroundColor Red
    }
}

if (-not $success) {
    Write-Host ""
    Write-Host "❌ All methods failed. Manual deployment required." -ForegroundColor Red
    Write-Host ""
    Write-Host "Please follow these steps:" -ForegroundColor Yellow
    Write-Host "1. Open terminal/PowerShell" -ForegroundColor White
    Write-Host "2. Run: ssh ${USER}@${SERVER}" -ForegroundColor Cyan
    Write-Host "3. Enter password: $PASSWORD" -ForegroundColor Cyan
    Write-Host "4. Copy and paste:" -ForegroundColor White
    Write-Host ""
    Write-Host $deployCmd -ForegroundColor Gray
    Write-Host ""
}
