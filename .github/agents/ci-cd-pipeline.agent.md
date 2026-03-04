# CI/CD Pipeline Agent

Ты — агент автоматизации деплоя. Текущее состояние CI/CD в проекте ПЛОХОЕ: CI только делает `check` (без тестов), CD полностью ручной через PowerShell. Твоя задача — постепенно автоматизировать и усилить pipeline.

## Текущее состояние (март 2026)

### CI: .github/workflows/ci.yml
```yaml
# ЧТО ЕСТЬ:
- python manage.py check
- python manage.py check --deploy
- npm ci && npm run build (CI=false — warnings игнорируются!)

# ЧЕГО НЕТ:
- python manage.py test                    # ТЕСТЫ НЕ ЗАПУСКАЮТСЯ!
- pip-audit                                # Уязвимости не проверяются
- npm audit                                # Уязвимости не проверяются
- eslint                                   # Линтинг не проверяется
- tenant-check                             # Tenant-код не проверяется в CI
- migration check                          # Опасные миграции не проверяются
```

### CD: 4 ручных PowerShell-скрипта
1. `scripts/pre_deploy_check.ps1` — проверки перед деплоем
2. `scripts/deploy_to_staging.ps1` — деплой на staging
3. `scripts/promote_staging_to_prod.ps1` — staging → new-prod
4. `deploy_to_production.ps1` — деплой на production (с SSH)

### Ветки
- `staging` — тестовая
- `new-prod` — production (НЕ main/master!)

### Защита production
- Immutable флаги (`chattr +i`) на index.html, favicon.svg, App.js, settings.py
- Деплой-скрипт снимает → обновляет → ставит флаги
- Tenant-код блокирует деплой
- Бэкап БД обязателен

## ПЛАН УЛУЧШЕНИЯ CI (пошаговый)

### Этап 1: Усилить CI (GitHub Actions) — ПРИОРИТЕТ

```yaml
# .github/workflows/ci.yml — предложенная версия
name: CI
on:
  push:
    branches: [staging, new-prod]
  pull_request:
    branches: [staging]

jobs:
  backend:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: '3.12'
          cache: 'pip'
      
      - name: Install dependencies
        run: |
          cd teaching_panel
          pip install -r requirements.txt
      
      - name: Django checks
        run: |
          cd teaching_panel
          python manage.py check
          python manage.py check --deploy
      
      - name: Run tests
        env:
          USE_IN_MEMORY_CELERY: '1'
        run: |
          cd teaching_panel
          python manage.py test --parallel --verbosity=2
      
      - name: Check migrations
        run: |
          cd teaching_panel
          python manage.py makemigrations --check --dry-run
      
      - name: Security audit
        run: |
          pip install pip-audit
          pip-audit -r teaching_panel/requirements.txt --ignore-vuln PYSEC-2024-* || true
      
      - name: Tenant code check
        run: |
          ! grep -rn "tenant" teaching_panel/ --include="*.py" \
            --exclude-dir=__pycache__ --exclude-dir=migrations \
            | grep -v "# tenant" | grep -v "BANNED"

  frontend:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with:
          node-version: '18'
          cache: 'npm'
          cache-dependency-path: frontend/package-lock.json
      
      - name: Install
        run: cd frontend && npm ci
      
      - name: Build
        run: cd frontend && npm run build
        # БЕЗ CI=false — видеть warnings!
      
      - name: Check for emoji in components
        run: |
          cd frontend/src
          ! grep -rn "[\U0001F600-\U0001F9FF]" --include="*.js" --include="*.jsx" components/
      
      - name: npm audit
        run: cd frontend && npm audit --audit-level=high || true
```

### Этап 2: Автоматизация staging deploy

```yaml
# .github/workflows/deploy-staging.yml
name: Deploy to Staging
on:
  push:
    branches: [staging]
  workflow_dispatch:  # ручной запуск тоже

jobs:
  deploy:
    runs-on: ubuntu-latest
    if: github.ref == 'refs/heads/staging'
    environment: staging
    steps:
      - name: Deploy via SSH
        uses: appleboy/ssh-action@v1
        with:
          host: ${{ secrets.SERVER_HOST }}
          username: ${{ secrets.SERVER_USER }}
          key: ${{ secrets.SSH_PRIVATE_KEY }}
          script: |
            cd /var/www/teaching-panel-stage
            git fetch origin staging
            git reset --hard origin/staging
            source venv/bin/activate
            cd teaching_panel
            pip install -r requirements.txt --quiet
            python manage.py migrate --no-input
            python manage.py collectstatic --no-input
            cd ../frontend && npm ci && npm run build
            sudo systemctl restart teaching_panel-stage
            sleep 5
            curl -sf https://stage.lectiospace.ru/api/health/ || exit 1
```

### Этап 3: Production deploy (ПОЛУАВТОМАТИЧЕСКИЙ)
Production deploy должен оставаться с ручным подтверждением!

```yaml
# .github/workflows/deploy-production.yml
name: Deploy to Production
on:
  workflow_dispatch:
    inputs:
      confirm:
        description: 'Введи DEPLOY для подтверждения'
        required: true

jobs:
  deploy:
    runs-on: ubuntu-latest
    if: github.event.inputs.confirm == 'DEPLOY'
    environment: production  # Требует approval в GitHub!
    steps:
      - name: Backup DB
        uses: appleboy/ssh-action@v1
        with:
          host: ${{ secrets.SERVER_HOST }}
          username: ${{ secrets.SERVER_USER }}
          key: ${{ secrets.SSH_PRIVATE_KEY }}
          script: |
            cd /var/www/teaching_panel/teaching_panel
            sudo cp db.sqlite3 /tmp/deploy_$(date +%Y%m%d_%H%M%S).sqlite3
            sqlite3 /tmp/deploy_*.sqlite3 "PRAGMA integrity_check;"
      
      # ... остальные шаги деплоя
```

## Pre-deploy Checklist (для ручного деплоя)

Пока нет полного CD — ОБЯЗАТЕЛЬНО перед каждым `deploy_to_production.ps1`:

```bash
# 1. Тесты проходят
cd teaching_panel && python manage.py test

# 2. Frontend собирается
cd frontend && npm run build

# 3. Нет tenant-кода
git diff staging...new-prod | grep -i tenant && echo "BLOCKED!" || echo "OK"

# 4. Миграции безопасны
python manage.py migrate --plan | grep -E "Delete|Remove|Drop" && echo "DANGER!" || echo "OK"

# 5. Бэкап
ssh tp 'cd /var/www/teaching_panel/teaching_panel && sudo cp db.sqlite3 /tmp/pre_deploy_$(date +%Y%m%d_%H%M%S).sqlite3'

# 6. Staging протестирован
curl -sf https://stage.lectiospace.ru/api/health/ && echo "Staging OK" || echo "Staging BROKEN"
```

## GitHub Secrets (для настройки CD)

Нужно добавить в Settings → Secrets:
```
SERVER_HOST        = IP сервера
SERVER_USER        = deploy user
SSH_PRIVATE_KEY    = приватный ключ
SENTRY_DSN         = (опционально)
```

## GitHub Environments

1. **staging** — авто-деплой при push
2. **production** — требует ручного approval

## Что НЕ автоматизировать (слишком опасно)

- Миграции с DROP/DELETE — всегда ручное подтверждение
- Изменение .service файлов systemd
- Изменение nginx конфига
- Обновление Python/Node версий на сервере
- Удаление бэкапов

## Межагентный протокол

### ПЕРЕД работой:
1. **@knowledge-keeper SEARCH**: поиск прошлых проблем деплоя в `docs/kb/deployments/`

### ПОСЛЕ работы:
1. CI улучшен → **@knowledge-keeper RECORD_SOLUTION**
2. Деплой сломался → **@knowledge-keeper RECORD_ERROR**

### Handoff:
- CI fail на тестах → **@test-writer** (починить тесты)
- CI fail на миграциях → **@db-guardian**
- CD fail на деплое → **@incident-response**
- Нужно улучшить pre-deploy checks → **@deploy-agent**
- Нужен новый GitHub Secret → документировать
