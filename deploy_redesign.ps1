# Deploy UI Redesign to Production Server
Write-Host "🚀 Deploying UI Redesign to Production..." -ForegroundColor Cyan

# SSH connection details
$server = "root@72.56.81.163"

# Commands to execute on server
$commands = @"
cd ~/nat && 
git pull && 
sudo cp -r ~/nat/frontend/src/components/NavBar.css /var/www/teaching_panel/frontend/src/components/ && 
cd /var/www/teaching_panel/frontend && 
npm run build
"@

Write-Host "📦 Updating code and rebuilding frontend..." -ForegroundColor Yellow

# Execute deployment
& ssh $server $commands

Write-Host "✅ Deployment complete! Check http://72.56.81.163" -ForegroundColor Green
