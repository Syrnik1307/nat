#!/bin/bash
#
# Fix Duplicate Celery Workers
# Removes conflicting celery-worker.service and celery_worker.service
#
# Usage: bash fix_duplicate_celery_workers.sh
#

set -e  # Exit on error

echo "========================================"
echo "Celery Worker Deduplication Script"
echo "========================================"
echo ""

# Check if running as root or with sudo
if [ "$EUID" -ne 0 ]; then 
    echo "⚠️  This script requires sudo privileges."
    echo "Please run with: sudo bash fix_duplicate_celery_workers.sh"
    exit 1
fi

echo "🔍 Step 1: Identifying Celery worker services..."
echo ""

# List all celery-related services
SERVICES=(
    "celery-worker.service"
    "celery_worker.service"
    "teaching-panel-celery-worker.service"
)

ACTIVE_SERVICES=()
INACTIVE_SERVICES=()

for service in "${SERVICES[@]}"; do
    if systemctl list-unit-files | grep -q "^${service}"; then
        # Service exists - check if it's active
        if systemctl is-active --quiet "${service}"; then
            ACTIVE_SERVICES+=("${service}")
            echo "  ✅ ${service} - ACTIVE"
        else
            INACTIVE_SERVICES+=("${service}")
            echo "  ⚠️  ${service} - INACTIVE"
        fi
    fi
done

echo ""
echo "📊 Summary:"
echo "  Active services: ${#ACTIVE_SERVICES[@]}"
echo "  Inactive services: ${#INACTIVE_SERVICES[@]}"
echo ""

# If more than one active service, we have a conflict
if [ ${#ACTIVE_SERVICES[@]} -gt 1 ]; then
    echo "⚠️  CONFLICT DETECTED: Multiple active Celery workers running!"
    echo ""
    echo "Active services:"
    for svc in "${ACTIVE_SERVICES[@]}"; do
        echo "  - ${svc}"
        systemctl status "${svc}" --no-pager | head -5
    done
    echo ""
    
    # Choose canonical service (prefer hyphenated version)
    CANONICAL="celery-worker.service"
    if [[ ! " ${ACTIVE_SERVICES[@]} " =~ " ${CANONICAL} " ]]; then
        CANONICAL="${ACTIVE_SERVICES[0]}"
    fi
    
    echo "✅ Canonical service: ${CANONICAL}"
    echo ""
    
    # Stop and disable duplicates
    for svc in "${ACTIVE_SERVICES[@]}"; do
        if [ "${svc}" != "${CANONICAL}" ]; then
            echo "🛑 Stopping duplicate: ${svc}"
            systemctl stop "${svc}"
            echo "🔒 Disabling duplicate: ${svc}"
            systemctl disable "${svc}"
            INACTIVE_SERVICES+=("${svc}")
        fi
    done
    
elif [ ${#ACTIVE_SERVICES[@]} -eq 1 ]; then
    echo "✅ Only one active Celery worker found: ${ACTIVE_SERVICES[0]}"
    CANONICAL="${ACTIVE_SERVICES[0]}"
else
    echo "⚠️  No active Celery workers found!"
    echo "You may need to manually start the correct service."
    exit 0
fi

echo ""
echo "🔍 Step 2: Removing inactive/duplicate service files..."
echo ""

# Remove inactive service files (optional - asks for confirmation)
if [ ${#INACTIVE_SERVICES[@]} -gt 0 ]; then
    for svc in "${INACTIVE_SERVICES[@]}"; do
        SERVICE_FILE=$(systemctl show -p FragmentPath "${svc}" 2>/dev/null | cut -d= -f2)
        if [ -n "${SERVICE_FILE}" ] && [ -f "${SERVICE_FILE}" ]; then
            echo "Found service file: ${SERVICE_FILE}"
            read -p "  Remove ${SERVICE_FILE}? (y/n) " -n 1 -r
            echo ""
            if [[ $REPLY =~ ^[Yy]$ ]]; then
                rm -f "${SERVICE_FILE}"
                echo "  ✅ Removed ${SERVICE_FILE}"
            else
                echo "  ⏭️  Skipped ${SERVICE_FILE}"
            fi
        fi
    done
fi

echo ""
echo "🔄 Step 3: Reloading systemd daemon..."
systemctl daemon-reload

echo ""
echo "✅ Step 4: Verifying final state..."
systemctl status "${CANONICAL}" --no-pager | head -10

echo ""
echo "========================================="
echo "✅ Celery Worker Deduplication Complete!"
echo "========================================="
echo ""
echo "Active service: ${CANONICAL}"
echo ""
echo "Next steps:"
echo "  1. Verify worker is running: systemctl status ${CANONICAL}"
echo "  2. Check logs: journalctl -u ${CANONICAL} -f"
echo "  3. Test task execution: python manage.py shell -c 'from schedule.tasks import debug_task; debug_task.delay()'"
echo ""
