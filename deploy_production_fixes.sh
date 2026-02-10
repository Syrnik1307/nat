#!/bin/bash
#
# Production Deployment Script for Teaching Panel
# Handles migrations, service restarts, and Celery worker deduplication
#
# Usage: sudo bash deploy_production_fixes.sh
#

set -e  # Exit on error

# Configuration
PROJECT_ROOT="/var/www/teaching_panel"
VENV_PATH="${PROJECT_ROOT}/../venv"
PYTHON="${VENV_PATH}/bin/python"
MANAGE_PY="${PROJECT_ROOT}/manage.py"
BACKUP_DIR="/tmp"
SERVICES=(
    "teaching_panel"           # Gunicorn service
    "celery-worker"            # Celery worker
    "celery-beat"              # Celery beat scheduler (if exists)
)

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo "========================================="
echo "Teaching Panel - Production Deployment"
echo "========================================="
echo ""

# Check if running as root or with sudo
if [ "$EUID" -ne 0 ]; then 
    echo -e "${RED}⚠️  This script requires sudo privileges.${NC}"
    echo "Please run with: sudo bash deploy_production_fixes.sh"
    exit 1
fi

# Step 1: Backup Database
echo -e "${GREEN}📦 Step 1: Creating database backup...${NC}"
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
BACKUP_FILE="${BACKUP_DIR}/deploy_${TIMESTAMP}.sqlite3"

if [ -f "${PROJECT_ROOT}/db.sqlite3" ]; then
    cp "${PROJECT_ROOT}/db.sqlite3" "${BACKUP_FILE}"
    echo -e "${GREEN}✅ Backup created: ${BACKUP_FILE}${NC}"
    
    # Verify backup integrity
    sqlite3 "${BACKUP_FILE}" "PRAGMA integrity_check;" > /dev/null 2>&1
    if [ $? -eq 0 ]; then
        echo -e "${GREEN}✅ Backup integrity verified${NC}"
    else
        echo -e "${RED}❌ Backup integrity check failed!${NC}"
        echo "Aborting deployment."
        exit 1
    fi
else
    echo -e "${YELLOW}⚠️  Database file not found. Skipping backup.${NC}"
fi

echo ""

# Step 2: Git Pull (optional - commented out)
# echo -e "${GREEN}🔄 Step 2: Pulling latest code from git...${NC}"
# cd "${PROJECT_ROOT}"
# sudo -u www-data git pull origin main
# echo ""

# Step 3: Install/Update Dependencies
echo -e "${GREEN}📦 Step 3: Installing Python dependencies...${NC}"
cd "${PROJECT_ROOT}"
"${VENV_PATH}/bin/pip" install -r requirements.txt --quiet
echo -e "${GREEN}✅ Dependencies updated${NC}"
echo ""

# Step 4: Run Migrations (with confirmation)
echo -e "${GREEN}🗄️  Step 4: Running database migrations...${NC}"
echo ""
echo -e "${YELLOW}⚠️  WARNING: Migrations are IRREVERSIBLE!${NC}"
echo "The following migration will be applied:"
echo "  - 0032_fix_gdrive_file_id_default (adds default='' to gdrive fields)"
echo ""
echo "Backup location: ${BACKUP_FILE}"
echo ""
read -p "Type MIGRATE to continue, or anything else to skip: " -r
echo ""

if [ "$REPLY" == "MIGRATE" ]; then
    sudo -u www-data "${PYTHON}" "${MANAGE_PY}" migrate --noinput
    echo -e "${GREEN}✅ Migrations completed${NC}"
else
    echo -e "${YELLOW}⏭️  Migrations skipped${NC}"
fi

echo ""

# Step 5: Collect Static Files
echo -e "${GREEN}📁 Step 5: Collecting static files...${NC}"
sudo -u www-data "${PYTHON}" "${MANAGE_PY}" collectstatic --noinput --clear
echo -e "${GREEN}✅ Static files collected${NC}"
echo ""

# Step 6: Restart Services
echo -e "${GREEN}🔄 Step 6: Restarting services...${NC}"
for service in "${SERVICES[@]}"; do
    if systemctl list-unit-files | grep -q "^${service}.service"; then
        echo "  Restarting ${service}..."
        systemctl restart "${service}"
        sleep 2
        
        if systemctl is-active --quiet "${service}"; then
            echo -e "${GREEN}  ✅ ${service} is running${NC}"
        else
            echo -e "${RED}  ❌ ${service} failed to start!${NC}"
            echo "  Check logs with: journalctl -u ${service} -n 50"
        fi
    else
        echo -e "${YELLOW}  ⏭️  ${service} not found, skipping${NC}"
    fi
done

echo ""

# Step 7: Deduplicate Celery Workers
echo -e "${GREEN}🔧 Step 7: Checking for duplicate Celery workers...${NC}"
echo ""

# Count active celery workers
CELERY_SERVICES=$(systemctl list-units --type=service --state=active --no-pager | grep -i celery | grep -i worker | wc -l)

if [ ${CELERY_SERVICES} -gt 1 ]; then
    echo -e "${YELLOW}⚠️  Multiple Celery workers detected (${CELERY_SERVICES} active)${NC}"
    echo ""
    echo "Active Celery services:"
    systemctl list-units --type=service --state=active --no-pager | grep -i celery | grep -i worker
    echo ""
    
    read -p "Run Celery deduplication script? (y/n) " -n 1 -r
    echo ""
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        # Find and run deduplication script
        DEDUP_SCRIPT="${PROJECT_ROOT}/../fix_duplicate_celery_workers.sh"
        if [ -f "${DEDUP_SCRIPT}" ]; then
            bash "${DEDUP_SCRIPT}"
        else
            echo -e "${YELLOW}⚠️  Deduplication script not found at ${DEDUP_SCRIPT}${NC}"
            echo "Please run it manually or check the script location."
        fi
    else
        echo -e "${YELLOW}⏭️  Celery deduplication skipped${NC}"
    fi
else
    echo -e "${GREEN}✅ Only ${CELERY_SERVICES} Celery worker(s) active, no duplicates${NC}"
fi

echo ""

# Step 8: Verify Deployment
echo -e "${GREEN}🔍 Step 8: Verifying deployment...${NC}"
echo ""

# Check if Django can respond
HEALTH_CHECK_URL="http://localhost:8000/api/health/"
HTTP_CODE=$(curl -o /dev/null -s -w "%{http_code}\n" "${HEALTH_CHECK_URL}" || echo "000")

if [ "${HTTP_CODE}" == "200" ] || [ "${HTTP_CODE}" == "404" ]; then
    echo -e "${GREEN}✅ Django application is responding${NC}"
else
    echo -e "${YELLOW}⚠️  Health check returned HTTP ${HTTP_CODE}${NC}"
    echo "This might be expected if /api/health/ endpoint doesn't exist."
fi

# Check Celery worker status
if systemctl is-active --quiet celery-worker 2>/dev/null; then
    echo -e "${GREEN}✅ Celery worker is running${NC}"
else
    echo -e "${YELLOW}⚠️  Celery worker status unknown${NC}"
fi

echo ""

# Step 9: Summary
echo "========================================="
echo -e "${GREEN}✅ Deployment Complete!${NC}"
echo "========================================="
echo ""
echo "📋 Summary:"
echo "  - Backup: ${BACKUP_FILE}"
echo "  - Migrations: Applied (if confirmed)"
echo "  - Services: Restarted"
echo ""
echo "🔍 Next Steps:"
echo "  1. Check application logs:"
echo "     journalctl -u teaching-panel -f"
echo ""
echo "  2. Check Celery logs:"
echo "     journalctl -u celery-worker -f"
echo ""
echo "  3. Monitor for errors:"
echo "     tail -f ${PROJECT_ROOT}/logs/django.log"
echo ""
echo "  4. Test critical functionality:"
echo "     - Login/Register"
echo "     - Lesson creation"
echo "     - Recording upload"
echo "     - Zoom webhook (create a test recording)"
echo ""
echo "🔄 To rollback database if needed:"
echo "  sudo cp ${BACKUP_FILE} ${PROJECT_ROOT}/db.sqlite3"
echo "  sudo chown www-data:www-data ${PROJECT_ROOT}/db.sqlite3"
echo "  sudo systemctl restart teaching_panel"
echo ""
