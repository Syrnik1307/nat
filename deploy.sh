#!/bin/bash
# Deploy UI Redesign Script
# Run this with: bash deploy.sh

echo "🚀 Deploying UI Redesign to Production Server..."
echo "📦 Server: root@72.56.81.163"
echo ""

ssh root@72.56.81.163 << 'ENDSSH'
echo "📥 Pulling latest changes from GitHub..."
cd ~/nat
git pull

echo "📋 Copying updated CSS file..."
sudo cp -r ~/nat/frontend/src/components/NavBar.css /var/www/teaching_panel/frontend/src/components/

echo "🔨 Building frontend..."
cd /var/www/teaching_panel/frontend
npm run build

echo "✅ Deployment complete!"
echo "🌐 Check: http://72.56.81.163"
ENDSSH

echo ""
echo "✅ Done! Hard refresh browser (Ctrl+Shift+R) to see changes."
