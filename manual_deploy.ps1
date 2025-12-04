# Manual Deployment Script for Teaching Panel
# Использование: .\manual_deploy.ps1

$TARGET = "tp"  # SSH alias configured in ~/.ssh/config
$REMOTE_PATH = "/var/www/teaching_panel"

Write-Host "=== Teaching Panel Manual Deployment ===" -ForegroundColor Cyan
Write-Host ""

# Команды для выполнения на сервере
$commands = @"
cd $REMOTE_PATH &&
echo '=== Pulling latest changes ===' &&
sudo -u www-data git pull origin main &&
echo '' &&
echo '=== Activating virtual environment ===' &&
cd teaching_panel &&
source ../venv/bin/activate &&
echo '' &&
echo '=== Installing/updating Python dependencies ===' &&
pip install -r requirements.txt --quiet &&
echo '' &&
echo '=== Running database migrations ===' &&
python manage.py migrate &&
echo '' &&
echo '=== Collecting static files ===' &&
python manage.py collectstatic --noinput &&
echo '' &&
echo '=== Restarting services ===' &&
sudo systemctl restart teaching_panel &&
sudo systemctl restart nginx &&
echo '' &&
echo '=== Checking service status ===' &&
sudo systemctl status teaching_panel --no-pager | head -10 &&
echo '' &&
echo '✅ Deployment completed!'
"@

Write-Host "Connecting to server via alias: $TARGET" -ForegroundColor Yellow
Write-Host ""

# Попытка подключиться через SSH
# Примечание: требуется установленный SSH клиент или PuTTY
try {
    # Используем echo для автоматического ввода пароля (НЕ безопасно для production!)
    $deployScript = @"
#!/bin/bash
$commands
"@

    # Сохраняем скрипт локально
    $scriptPath = Join-Path $env:TEMP "deploy_script.sh"
    $deployScript | Out-File -FilePath $scriptPath -Encoding ASCII
    
    Write-Host "Deployment script created: $scriptPath" -ForegroundColor Green
    Write-Host ""
    Write-Host "Manual steps:" -ForegroundColor Yellow
    Write-Host "1. Copy script to server:" -ForegroundColor White
    Write-Host "   scp $scriptPath ${TARGET}:~/deploy.sh" -ForegroundColor Gray
    Write-Host "" 
    Write-Host "2. SSH to server:" -ForegroundColor White
    Write-Host "   ssh ${TARGET}" -ForegroundColor Gray
    Write-Host "" 
    Write-Host "3. Run deployment:" -ForegroundColor White
    Write-Host "   bash ~/deploy.sh" -ForegroundColor Gray
    Write-Host "" 
    
} catch {
    Write-Host "Error: $_" -ForegroundColor Red
    Write-Host ""
    Write-Host "Please deploy manually using the steps above." -ForegroundColor Yellow
}

Write-Host ""
Write-Host "=== Deployment script finished ===" -ForegroundColor Cyan
