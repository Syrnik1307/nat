#!/bin/bash
# Teaching Panel Production Deployment Script
# Запуск: chmod +x deploy.sh && ./deploy.sh

set -e  # Exit on error

echo "🚀 Teaching Panel Production Deployment Started..."
echo "=================================================="

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Configuration
DEPLOY_DIR="/var/www/teaching_panel"
VENV_PATH="${DEPLOY_DIR}/venv"
DJANGO_DIR="${DEPLOY_DIR}/teaching_panel"
FRONTEND_DIR="${DEPLOY_DIR}/frontend"

# Step 1: Pull latest code
echo -e "${YELLOW}📥 Step 1: Pulling latest code from main...${NC}"
cd "${DEPLOY_DIR}"
sudo -u www-data git pull origin main
echo -e "${GREEN}✅ Code updated${NC}"

# Step 2: Install Python dependencies
echo -e "${YELLOW}📦 Step 2: Installing Python dependencies...${NC}"
cd "${DJANGO_DIR}"
source "${VENV_PATH}/bin/activate"
pip install -r requirements.txt --quiet
echo -e "${GREEN}✅ Dependencies installed${NC}"

# Step 3: Run migrations
echo -e "${YELLOW}🗄️  Step 3: Running database migrations...${NC}"
python manage.py migrate --noinput
echo -e "${GREEN}✅ Migrations completed${NC}"

# Step 4: Collect static files
echo -e "${YELLOW}📂 Step 4: Collecting static files...${NC}"
python manage.py collectstatic --noinput --clear
echo -e "${GREEN}✅ Static files collected${NC}"

# Step 5: Build frontend
echo -e "${YELLOW}Step 5: Building frontend...${NC}"
cd "${FRONTEND_DIR}"
npm install --quiet
npm run build

# Fix permissions - CRITICAL: npm creates files as root, but nginx runs as www-data
echo -e "${YELLOW}Step 5.1: Fixing permissions...${NC}"
chown -R www-data:www-data "${FRONTEND_DIR}/build"
chmod -R 755 "${FRONTEND_DIR}/build"
echo -e "${GREEN}Frontend built and permissions fixed${NC}"

# Step 6: Restart services
echo -e "${YELLOW}🔄 Step 6: Restarting services...${NC}"
sudo systemctl restart teaching_panel
sudo systemctl restart nginx
echo -e "${GREEN}✅ Services restarted${NC}"

# Step 7: Verify deployment
echo -e "${YELLOW}✔️  Step 7: Verifying deployment...${NC}"
sleep 2

if sudo systemctl is-active --quiet teaching_panel; then
    echo -e "${GREEN}✅ Teaching Panel service is running${NC}"
else
    echo -e "${RED}❌ Teaching Panel service is NOT running${NC}"
    exit 1
fi

if sudo systemctl is-active --quiet nginx; then
    echo -e "${GREEN}✅ Nginx service is running${NC}"
else
    echo -e "${RED}❌ Nginx service is NOT running${NC}"
    exit 1
fi

echo ""
echo -e "${GREEN}=================================================="
echo "✅ DEPLOYMENT SUCCESSFUL!"
echo "=================================================${NC}"
echo ""
echo "📊 Service Status:"
echo "---"
sudo systemctl status teaching_panel --no-pager | head -5
echo "---"
echo ""
echo "📝 Recent Logs:"
echo "---"
sudo journalctl -u teaching_panel -n 10 --no-pager
echo "---"
echo ""
echo "✨ Teaching Panel is live! 🎉"
