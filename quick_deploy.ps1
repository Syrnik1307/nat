# Quick Deployment Script for Teaching Panel
# Автоматически выполняет deployment через SSH (alias "tp")

$TARGET = "tp"

Write-Host "=== Teaching Panel Quick Deploy ===" -ForegroundColor Cyan
Write-Host ""

# Команда для deployment (в одну строку)
$deployCmd = "cd /var/www/teaching_panel && sudo -u www-data git pull origin main && cd teaching_panel && source ../venv/bin/activate && pip install -r requirements.txt --quiet && python manage.py migrate && python manage.py collectstatic --noinput && sudo systemctl restart teaching_panel && sudo systemctl restart nginx && echo \"✅ Deployment completed!\" && sudo systemctl status teaching_panel --no-pager | head -10"

Write-Host "📡 Connecting to $TARGET..." -ForegroundColor Yellow

try {
    $result = ssh $TARGET "$deployCmd"
    if ($LASTEXITCODE -eq 0) {
        Write-Host ""
        Write-Host "✅ Deployment successful via OpenSSH!" -ForegroundColor Green
    } else {
        throw "Deployment command exited with code $LASTEXITCODE"
    }
} catch {
    Write-Host ""
    Write-Host "❌ Deployment failed. Please run the command manually:" -ForegroundColor Red
    Write-Host "   ssh $TARGET" -ForegroundColor Yellow
    Write-Host "   $deployCmd" -ForegroundColor Yellow
}
