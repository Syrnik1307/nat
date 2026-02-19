#!/bin/bash

set -euo pipefail

if [ "$#" -lt 1 ]; then
  echo "Usage: sudo bash deployment/setup_stage_subdomain.sh <stage-domain>"
  echo "Example: sudo bash deployment/setup_stage_subdomain.sh stage.yourdomain.com"
  exit 1
fi

DOMAIN="$1"
ROOT_DOMAIN="${DOMAIN#*.}"
SUBDOMAIN="${DOMAIN%%.*}"

PROJECT_ROOT="/var/www/teaching_panel"
BACKEND_DIR="${PROJECT_ROOT}/teaching_panel"
FRONTEND_DIR="${PROJECT_ROOT}/frontend"
ENV_FILE="${BACKEND_DIR}/.env"
NGINX_TEMPLATE="${BACKEND_DIR}/deployment/nginx.stage.conf.template"
NGINX_TARGET="/etc/nginx/sites-available/teaching_panel-stage"

if [ "${EUID}" -ne 0 ]; then
  echo "Run as root: sudo bash deployment/setup_stage_subdomain.sh ${DOMAIN}"
  exit 1
fi

if [ ! -f "${ENV_FILE}" ]; then
  echo "Missing ${ENV_FILE}. Create it first."
  exit 1
fi

if [ ! -f "${NGINX_TEMPLATE}" ]; then
  echo "Missing nginx template: ${NGINX_TEMPLATE}"
  exit 1
fi

backup_file() {
  local path="$1"
  local ts
  ts="$(date +%Y%m%d_%H%M%S)"
  cp "${path}" "${path}.bak.${ts}"
}

upsert_env() {
  local key="$1"
  local value="$2"
  local escaped
  escaped=$(printf '%s' "${value}" | sed 's/[&]/\\&/g')

  if grep -q "^${key}=" "${ENV_FILE}"; then
    sed -i "s|^${key}=.*|${key}=${escaped}|" "${ENV_FILE}"
  else
    echo "${key}=${value}" >> "${ENV_FILE}"
  fi
}

echo "[1/8] Backup .env"
backup_file "${ENV_FILE}"

echo "[2/8] Apply stage env values"
upsert_env "DEBUG" "False"
upsert_env "ALLOWED_HOSTS" "${DOMAIN},.${ROOT_DOMAIN},localhost,127.0.0.1"
upsert_env "SERVER_HOST" "${DOMAIN}"
upsert_env "CORS_WILDCARD_DOMAIN" "${ROOT_DOMAIN}"
upsert_env "CORS_EXTRA" "https://${DOMAIN}"
upsert_env "FRONTEND_URL" "https://${DOMAIN}"
upsert_env "CSRF_TRUSTED_ORIGINS" "https://${DOMAIN}"
upsert_env "SECURE_SSL_REDIRECT" "True"
upsert_env "SESSION_COOKIE_SECURE" "True"
upsert_env "CSRF_COOKIE_SECURE" "True"
upsert_env "OLGA_TENANT_SLUG" "${SUBDOMAIN}"
upsert_env "BASE_DOMAIN" "${ROOT_DOMAIN}"
upsert_env "FRONTEND_BASE_URL" "https://${DOMAIN}"

echo "[3/8] Build frontend"
cd "${FRONTEND_DIR}"
npm ci
npm run build

echo "[4/8] Django migrate/static"
cd "${BACKEND_DIR}"
source "${PROJECT_ROOT}/venv/bin/activate"
python manage.py migrate --noinput
python manage.py collectstatic --noinput

echo "[5/8] Seed Olga stage tenant/courses"
python manage.py shell -c "exec(open('create_olga_tenant.py', encoding='utf-8').read())"
python manage.py shell -c "exec(open('create_olga_courses.py', encoding='utf-8').read())"

echo "[6/8] Configure nginx"
cp "${NGINX_TEMPLATE}" "${NGINX_TARGET}"
sed -i "s/__DOMAIN__/${DOMAIN}/g" "${NGINX_TARGET}"
ln -sfn "${NGINX_TARGET}" /etc/nginx/sites-enabled/teaching_panel-stage
nginx -t

echo "[7/8] Obtain/renew certificate"
certbot --nginx -d "${DOMAIN}" --non-interactive --agree-tos -m "admin@${ROOT_DOMAIN}" || true

echo "[8/8] Restart services"
systemctl restart teaching_panel
systemctl restart celery
systemctl restart celery-beat
systemctl restart nginx

echo "Done. Check:"
echo "  https://${DOMAIN}/health"
echo "  https://${DOMAIN}/admin/"
echo "  https://${DOMAIN}/api/"
