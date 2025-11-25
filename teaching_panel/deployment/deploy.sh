#!/bin/bash

# ========================================
# Teaching Panel Deployment Script
# ========================================
# This script automates deployment on Ubuntu/Debian servers
# Run with: sudo bash deploy.sh
# ========================================

set -e  # Exit on error

echo "========================================="
echo "Teaching Panel - Production Deployment"
echo "========================================="

# Configuration
PROJECT_NAME="teaching_panel"
PROJECT_DIR="/var/www/${PROJECT_NAME}"
VENV_DIR="${PROJECT_DIR}/venv"
BACKEND_DIR="${PROJECT_DIR}/teaching_panel"
FRONTEND_DIR="${PROJECT_DIR}/frontend"
LOG_DIR="/var/log/${PROJECT_NAME}"
RUN_DIR="/var/run/${PROJECT_NAME}"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

print_status() {
    echo -e "${GREEN}[✓]${NC} $1"
}

print_error() {
    echo -e "${RED}[✗]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[!]${NC} $1"
}

# Check if running as root
if [ "$EUID" -ne 0 ]; then 
    print_error "Please run as root (use sudo)"
    exit 1
fi

print_status "Starting deployment..."

# Step 1: Install system dependencies
print_status "Installing system dependencies..."
apt-get update
apt-get install -y \
    python3.11 \
    python3.11-venv \
    python3-pip \
    nginx \
    redis-server \
    postgresql \
    postgresql-contrib \
    libpq-dev \
    build-essential \
    git \
    supervisor \
    certbot \
    python3-certbot-nginx

# Step 2: Create project directories
print_status "Creating project directories..."
mkdir -p ${PROJECT_DIR}
mkdir -p ${LOG_DIR}
mkdir -p ${RUN_DIR}
mkdir -p ${BACKEND_DIR}/staticfiles
mkdir -p ${BACKEND_DIR}/media

# Step 3: Set up Python virtual environment
print_status "Setting up Python virtual environment..."
if [ ! -d "${VENV_DIR}" ]; then
    python3.11 -m venv ${VENV_DIR}
fi

# Activate virtual environment
source ${VENV_DIR}/bin/activate

# Step 4: Install Python dependencies
print_status "Installing Python dependencies..."
cd ${BACKEND_DIR}
pip install --upgrade pip
pip install -r requirements-production.txt

# Step 5: Configure environment variables
print_status "Checking environment configuration..."
if [ ! -f "${BACKEND_DIR}/.env" ]; then
    print_warning ".env file not found. Please create it from .env.example"
    print_warning "Copy .env.example to .env and fill in your production values:"
    print_warning "  cp ${BACKEND_DIR}/.env.example ${BACKEND_DIR}/.env"
    print_warning "  nano ${BACKEND_DIR}/.env"
    exit 1
fi

# Step 6: Generate SECRET_KEY if needed
if grep -q "your-secret-key-here-change-me" "${BACKEND_DIR}/.env"; then
    print_warning "Generating new SECRET_KEY..."
    NEW_SECRET_KEY=$(python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())")
    sed -i "s/SECRET_KEY=.*/SECRET_KEY=${NEW_SECRET_KEY}/" "${BACKEND_DIR}/.env"
    print_status "New SECRET_KEY generated"
fi

# Step 7: Database setup
print_status "Setting up database..."
# Create PostgreSQL database and user (modify as needed)
# sudo -u postgres psql -c "CREATE DATABASE teaching_panel;"
# sudo -u postgres psql -c "CREATE USER teaching_panel_user WITH PASSWORD 'your_password';"
# sudo -u postgres psql -c "GRANT ALL PRIVILEGES ON DATABASE teaching_panel TO teaching_panel_user;"

# Run migrations
python manage.py migrate --noinput
print_status "Database migrations completed"

# Step 8: Collect static files
print_status "Collecting static files..."
python manage.py collectstatic --noinput --clear

# Step 9: Create superuser (interactive)
print_warning "Do you want to create a superuser? (y/n)"
read -r CREATE_SUPERUSER
if [ "$CREATE_SUPERUSER" = "y" ]; then
    python manage.py createsuperuser
fi

# Step 10: Build React frontend
print_status "Building React frontend..."
cd ${FRONTEND_DIR}
if [ ! -d "node_modules" ]; then
    npm install
fi
npm run build

# Step 11: Set permissions
print_status "Setting permissions..."
chown -R www-data:www-data ${PROJECT_DIR}
chown -R www-data:www-data ${LOG_DIR}
chown -R www-data:www-data ${RUN_DIR}
chmod -R 755 ${PROJECT_DIR}

# Step 12: Configure systemd services
print_status "Configuring systemd services..."
cp ${BACKEND_DIR}/deployment/teaching_panel.service /etc/systemd/system/
cp ${BACKEND_DIR}/deployment/celery.service /etc/systemd/system/
cp ${BACKEND_DIR}/deployment/celery-beat.service /etc/systemd/system/

# Reload systemd
systemctl daemon-reload

# Enable services
systemctl enable teaching_panel.service
systemctl enable celery.service
systemctl enable celery-beat.service
systemctl enable redis-server.service

# Step 13: Configure Nginx
print_status "Configuring Nginx..."
cp ${BACKEND_DIR}/deployment/nginx.conf /etc/nginx/sites-available/${PROJECT_NAME}

# Update domain in nginx config
print_warning "Enter your domain name (e.g., teachingpanel.com):"
read -r DOMAIN_NAME
sed -i "s/yourdomain.com/${DOMAIN_NAME}/g" /etc/nginx/sites-available/${PROJECT_NAME}

# Enable site
ln -sf /etc/nginx/sites-available/${PROJECT_NAME} /etc/nginx/sites-enabled/
rm -f /etc/nginx/sites-enabled/default

# Test nginx configuration
nginx -t

# Step 14: SSL Certificate with Let's Encrypt
print_warning "Do you want to obtain SSL certificate with Let's Encrypt? (y/n)"
read -r SETUP_SSL
if [ "$SETUP_SSL" = "y" ]; then
    print_status "Obtaining SSL certificate..."
    certbot --nginx -d ${DOMAIN_NAME} -d www.${DOMAIN_NAME}
fi

# Step 15: Start services
print_status "Starting services..."
systemctl start redis-server
systemctl start teaching_panel
systemctl start celery
systemctl start celery-beat
systemctl restart nginx

# Step 16: Check service status
print_status "Checking service status..."
systemctl status teaching_panel --no-pager
systemctl status celery --no-pager
systemctl status celery-beat --no-pager
systemctl status nginx --no-pager

# Step 17: Setup log rotation
print_status "Setting up log rotation..."
cat > /etc/logrotate.d/${PROJECT_NAME} << EOF
${LOG_DIR}/*.log {
    daily
    missingok
    rotate 14
    compress
    delaycompress
    notifempty
    create 0640 www-data www-data
    sharedscripts
    postrotate
        systemctl reload teaching_panel > /dev/null 2>&1 || true
    endscript
}
EOF

# Step 18: Setup firewall (if ufw is installed)
if command -v ufw &> /dev/null; then
    print_status "Configuring firewall..."
    ufw allow 'Nginx Full'
    ufw allow OpenSSH
    # ufw enable  # Uncomment to enable firewall
fi

print_status "========================================="
print_status "Deployment completed successfully!"
print_status "========================================="
echo ""
print_status "Your application is now running at:"
echo "  https://${DOMAIN_NAME}"
echo ""
print_status "Next steps:"
echo "  1. Configure your .env file with production credentials"
echo "  2. Set up email SMTP settings"
echo "  3. Configure Zoom API credentials"
echo "  4. Set up reCAPTCHA keys"
echo "  5. Configure SMS.ru API if needed"
echo "  6. Test the application"
echo ""
print_status "Service management commands:"
echo "  sudo systemctl status teaching_panel"
echo "  sudo systemctl restart teaching_panel"
echo "  sudo systemctl logs -u teaching_panel -f"
echo ""
print_status "Logs location: ${LOG_DIR}"
