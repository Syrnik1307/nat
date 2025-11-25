#!/bin/bash

# ========================================
# Database Migration & Management Script
# ========================================
# Safely handles database migrations for Teaching Panel
# ========================================

set -e

# Configuration
BACKEND_DIR="/var/www/teaching_panel/teaching_panel"
VENV_DIR="/var/www/teaching_panel/venv"
BACKUP_DIR="/var/backups/teaching_panel"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

print_status() { echo -e "${GREEN}[✓]${NC} $1"; }
print_error() { echo -e "${RED}[✗]${NC} $1"; }
print_warning() { echo -e "${YELLOW}[!]${NC} $1"; }

# Load environment
cd ${BACKEND_DIR}
source ${VENV_DIR}/bin/activate

# Function: Create database backup
backup_database() {
    print_status "Creating database backup..."
    mkdir -p ${BACKUP_DIR}
    
    # PostgreSQL backup
    if [ ! -z "$DATABASE_URL" ] && [[ $DATABASE_URL == postgresql* ]]; then
        DB_NAME=$(echo $DATABASE_URL | sed -n 's/.*\/\([^?]*\).*/\1/p')
        sudo -u postgres pg_dump ${DB_NAME} > ${BACKUP_DIR}/backup_${TIMESTAMP}.sql
        print_status "PostgreSQL backup created: ${BACKUP_DIR}/backup_${TIMESTAMP}.sql"
    
    # SQLite backup
    elif [ -f "${BACKEND_DIR}/db.sqlite3" ]; then
        cp ${BACKEND_DIR}/db.sqlite3 ${BACKUP_DIR}/db.sqlite3.${TIMESTAMP}
        print_status "SQLite backup created: ${BACKUP_DIR}/db.sqlite3.${TIMESTAMP}"
    fi
}

# Function: Check for pending migrations
check_migrations() {
    print_status "Checking for pending migrations..."
    python manage.py showmigrations --plan | grep '\[ \]' && {
        print_warning "Pending migrations found"
        return 0
    } || {
        print_status "No pending migrations"
        return 1
    }
}

# Function: Run migrations
run_migrations() {
    print_status "Running database migrations..."
    python manage.py migrate --noinput
    print_status "Migrations completed successfully"
}

# Function: Make migrations
make_migrations() {
    print_status "Creating new migrations..."
    python manage.py makemigrations
    print_status "New migrations created"
}

# Function: Rollback last migration
rollback_migration() {
    print_warning "Rolling back last migration..."
    read -p "Enter app name: " APP_NAME
    read -p "Enter migration name to rollback to: " MIGRATION_NAME
    python manage.py migrate ${APP_NAME} ${MIGRATION_NAME}
    print_status "Rollback completed"
}

# Function: List migrations
list_migrations() {
    print_status "Current migration status:"
    python manage.py showmigrations
}

# Function: Restore database backup
restore_backup() {
    print_warning "Available backups:"
    ls -lh ${BACKUP_DIR}/
    echo ""
    read -p "Enter backup filename to restore: " BACKUP_FILE
    
    if [ ! -f "${BACKUP_DIR}/${BACKUP_FILE}" ]; then
        print_error "Backup file not found!"
        exit 1
    fi
    
    print_warning "This will overwrite the current database. Are you sure? (yes/no)"
    read -r CONFIRM
    if [ "$CONFIRM" != "yes" ]; then
        print_error "Restore cancelled"
        exit 1
    fi
    
    # PostgreSQL restore
    if [[ $BACKUP_FILE == *.sql ]]; then
        DB_NAME=$(echo $DATABASE_URL | sed -n 's/.*\/\([^?]*\).*/\1/p')
        sudo -u postgres psql ${DB_NAME} < ${BACKUP_DIR}/${BACKUP_FILE}
        print_status "PostgreSQL database restored"
    
    # SQLite restore
    elif [[ $BACKUP_FILE == *.sqlite3.* ]]; then
        cp ${BACKUP_DIR}/${BACKUP_FILE} ${BACKEND_DIR}/db.sqlite3
        print_status "SQLite database restored"
    fi
}

# Main menu
echo "========================================="
echo "Teaching Panel - Database Management"
echo "========================================="
echo "1. Check for pending migrations"
echo "2. Run migrations (with backup)"
echo "3. Create new migrations"
echo "4. List all migrations"
echo "5. Rollback migration"
echo "6. Backup database only"
echo "7. Restore database from backup"
echo "8. Exit"
echo "========================================="
read -p "Select option: " OPTION

case $OPTION in
    1)
        check_migrations
        ;;
    2)
        backup_database
        run_migrations
        ;;
    3)
        make_migrations
        ;;
    4)
        list_migrations
        ;;
    5)
        backup_database
        rollback_migration
        ;;
    6)
        backup_database
        ;;
    7)
        restore_backup
        ;;
    8)
        print_status "Exiting..."
        exit 0
        ;;
    *)
        print_error "Invalid option"
        exit 1
        ;;
esac

print_status "Operation completed successfully"
