# Start Telegram Bot Locally
# Usage: .\start_bot.ps1

Write-Host "🤖 Starting Teaching Panel Telegram Bot..." -ForegroundColor Cyan
Write-Host ""

# Check if .env exists
$envFile = "teaching_panel\.env"
if (-Not (Test-Path $envFile)) {
    Write-Host "❌ Error: .env file not found at $envFile" -ForegroundColor Red
    Write-Host "Please create .env file and add TELEGRAM_BOT_TOKEN" -ForegroundColor Yellow
    exit 1
}

# Check if token exists in .env
$envContent = Get-Content $envFile
$tokenLine = $envContent | Select-String "TELEGRAM_BOT_TOKEN"
if (-Not $tokenLine) {
    Write-Host "❌ Error: TELEGRAM_BOT_TOKEN not found in .env" -ForegroundColor Red
    Write-Host "Please add: TELEGRAM_BOT_TOKEN=your_token_here" -ForegroundColor Yellow
    exit 1
}

Write-Host "✅ Found TELEGRAM_BOT_TOKEN in .env" -ForegroundColor Green

# Activate virtual environment
Write-Host "🔧 Activating virtual environment..." -ForegroundColor Cyan
& "venv\Scripts\Activate.ps1"

# Check if python-telegram-bot is installed
Write-Host "🔧 Checking python-telegram-bot..." -ForegroundColor Cyan
$botLib = pip show python-telegram-bot 2>&1
if ($botLib -match "WARNING: Package\(s\) not found") {
    Write-Host "❌ python-telegram-bot not installed" -ForegroundColor Red
    Write-Host "Installing python-telegram-bot==20.7..." -ForegroundColor Yellow
    pip install python-telegram-bot==20.7
}
else {
    Write-Host "✅ python-telegram-bot is installed" -ForegroundColor Green
}

# Check if Django is running
Write-Host "🔧 Checking Django server..." -ForegroundColor Cyan
try {
    $response = Invoke-WebRequest -Uri "http://127.0.0.1:8000/api/me/" -Method GET -TimeoutSec 2 -ErrorAction Stop
    Write-Host "✅ Django server is running on http://127.0.0.1:8000" -ForegroundColor Green
}
catch {
    Write-Host "⚠️  Django server is NOT running!" -ForegroundColor Yellow
    Write-Host "Please start Django in another terminal:" -ForegroundColor Yellow
    Write-Host "  cd teaching_panel" -ForegroundColor Cyan
    Write-Host "  ..\venv\Scripts\Activate.ps1" -ForegroundColor Cyan
    Write-Host "  python manage.py runserver" -ForegroundColor Cyan
    Write-Host ""
    $continue = Read-Host "Continue anyway? (y/N)"
    if ($continue -ne "y") {
        exit 1
    }
}

# Start the bot
Write-Host ""
Write-Host "🚀 Starting Telegram bot..." -ForegroundColor Green
Write-Host "Press Ctrl+C to stop" -ForegroundColor Yellow
Write-Host ""

Set-Location teaching_panel
python telegram_bot.py
