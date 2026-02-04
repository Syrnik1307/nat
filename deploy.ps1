# Deploy скрипт с выбором окружения
param(
    [Parameter(Mandatory=$true)]
    [ValidateSet('production-russia', 'staging', 'production-africa')]
    [string]$Environment
)

Write-Host "🚀 Deploying to: $Environment" -ForegroundColor Cyan

# Проверки перед деплоем
Write-Host "`n✅ Pre-deploy checks..." -ForegroundColor Yellow

# 1. Проверить тесты
Write-Host "Running tests..."
cd teaching_panel
python manage.py test --settings=teaching_panel.settings_$Environment
if ($LASTEXITCODE -ne 0) {
    Write-Host "❌ Tests failed! Aborting deploy." -ForegroundColor Red
    exit 1
}

# 2. Проверить миграции
Write-Host "Checking migrations..."
python manage.py makemigrations --check --dry-run --settings=teaching_panel.settings_$Environment
if ($LASTEXITCODE -ne 0) {
    Write-Host "⚠️ Uncommitted migrations found!" -ForegroundColor Yellow
}

# 3. Проверить feature flags
Write-Host "Feature flags for $Environment:"
python -c "
import os
os.environ['DJANGO_SETTINGS_MODULE'] = 'teaching_panel.settings_$Environment'
import django
django.setup()
from core.feature_flags import FeatureFlags
import inspect

for name, value in inspect.getmembers(FeatureFlags):
    if name.startswith('FEATURE_'):
        print(f'  {name}: {value}')
"

# Подтверждение
$confirm = Read-Host "`nDeploy to $Environment? (yes/no)"
if ($confirm -ne 'yes') {
    Write-Host "❌ Deploy cancelled" -ForegroundColor Red
    exit 0
}

# Deploy
Write-Host "`n🚀 Starting deploy..." -ForegroundColor Green

switch ($Environment) {
    'production-russia' {
        # Деплой на lectiospace.ru
        Write-Host "Deploying to lectiospace.ru (PRODUCTION RUSSIA)"
        
        # Backend
        ssh root@lectiospace.ru "cd /var/www/teaching-panel && \
            git pull origin main && \
            source venv/bin/activate && \
            pip install -r requirements.txt && \
            export DJANGO_SETTINGS_MODULE=teaching_panel.settings_production_russia && \
            python manage.py migrate && \
            python manage.py collectstatic --noinput && \
            sudo systemctl restart teaching-panel"
        
        # Frontend
        cd ../frontend
        $env:REACT_APP_ENV = 'production_russia'
        npm run build
        scp -r build/* root@lectiospace.ru:/var/www/teaching-panel-frontend/
        
        Write-Host "✅ Deployed to lectiospace.ru" -ForegroundColor Green
    }
    
    'staging' {
        # Деплой на stage.lectiospace.ru
        Write-Host "Deploying to stage.lectiospace.ru (STAGING)"
        
        ssh root@lectiospace.ru "cd /var/www/teaching-panel-staging && \
            git pull origin staging && \
            source venv/bin/activate && \
            pip install -r requirements.txt && \
            export DJANGO_SETTINGS_MODULE=teaching_panel.settings_staging && \
            python manage.py migrate && \
            python manage.py collectstatic --noinput && \
            sudo systemctl restart teaching-panel-staging"
        
        cd ../frontend
        $env:REACT_APP_ENV = 'staging'
        npm run build
        scp -r build/* root@lectiospace.ru:/var/www/teaching-panel-staging-frontend/
        
        Write-Host "✅ Deployed to stage.lectiospace.ru" -ForegroundColor Green
    }
    
    'production-africa' {
        # Деплой на teachpanel.com (будущее)
        Write-Host "Deploying to teachpanel.com (PRODUCTION AFRICA)"
        Write-Host "⚠️ Not implemented yet" -ForegroundColor Yellow
    }
}

Write-Host "`n✅ Deploy completed!" -ForegroundColor Green
Write-Host "Check logs: ssh root@lectiospace.ru 'tail -f /var/www/teaching-panel/logs/app.log'"
