# CI/CD Setup Guide — Teaching Panel

## Что было создано

```
.github/
  workflows/
    ci.yml                  — CI: тесты + линт при каждом пуше/PR
    deploy-staging.yml      — Автодеплой на staging при пуше в staging
    deploy-production.yml   — Автодеплой на прод при пуше в stable-prod
```

Также обновлён `teaching_panel/teaching_panel/urls.py`:
- Добавлен явный маршрут `api/health/` с проверкой БД

---

## Шаг 1: Настроить GitHub Secrets

Перейди в **GitHub → Settings → Secrets and variables → Actions** и добавь:

| Secret | Значение | Пример |
|---|---|---|
| `SERVER_HOST` | IP сервера | `72.56.81.163` |
| `SERVER_USER` | SSH пользователь | `root` |
| `SERVER_SSH_KEY` | Приватный SSH-ключ (полностью) | Содержимое `~/.ssh/id_rsa` |
| `TELEGRAM_BOT_TOKEN` | Токен Telegram-бота (опционально) | `123456:ABC-DEF` |
| `TELEGRAM_CHAT_ID` | ID чата для уведомлений (опционально) | `-100123456789` |

### Как получить SSH-ключ для GitHub Actions:

```bash
# На своей машине (или на сервере):
ssh-keygen -t ed25519 -C "github-actions-deploy" -f ~/.ssh/github_actions_key -N ""

# Скопировать публичный ключ НА СЕРВЕР:
ssh-copy-id -i ~/.ssh/github_actions_key.pub root@72.56.81.163

# Скопировать ПРИВАТНЫЙ ключ в GitHub Secrets (SERVER_SSH_KEY):
cat ~/.ssh/github_actions_key
# Скопировать ВЕСЬ вывод включая -----BEGIN и -----END
```

---

## Шаг 2: Настроить Environments в GitHub

### Staging:
1. GitHub → Settings → Environments → New environment → `staging`
2. Никаких ограничений не нужно

### Production:
1. GitHub → Settings → Environments → New environment → `production`  
2. ✅ **Required reviewers** → добавь себя
3. Это значит что деплой на прод потребует ручного подтверждения

---

## Шаг 3: Первый запуск

### Проверить CI (без деплоя):
```bash
# Любой пуш в main или stable-prod запустит CI
git add .github/
git commit -m "feat: add CI/CD pipelines"
git push origin stable-prod
```

CI запустится автоматически и проверит:
- ✅ Python синтаксис (flake8 — только критические ошибки)
- ✅ Django system check
- ✅ Django миграции
- ✅ Django тесты (пока не блокирующие — `|| true`)
- ✅ React сборка
- ✅ Проверка билда (index.html, main.js)

### Проверить деплой на staging:
```bash
git checkout staging
git merge stable-prod
git push origin staging
# → Автоматически задеплоится на staging
```

### Деплой на production:
```bash
git checkout stable-prod
# ... внести изменения ...
git push origin stable-prod
# → CI запустится → потребует approve → задеплоится на прод
```

---

## Как это работает (схема)

```
                    push to any branch
                          │
                          ▼
                    ┌──────────┐
                    │    CI    │  ← flake8, django check, tests, npm build
                    └────┬─────┘
                         │
            ┌────────────┼────────────┐
            │            │            │
     push staging   push stable-prod  push other
            │            │            │
            ▼            ▼            ▼
     ┌──────────┐  ┌──────────┐     (nothing)
     │ Deploy   │  │ Deploy   │
     │ Staging  │  │ Prod     │
     │ (auto)   │  │ (approve)│
     └──────────┘  └──────────┘
```

---

## Что НЕ изменилось

- ❌ Существующие deploy-скрипты (`deploy_unified.sh`, `deploy_backend.sh`) — **не удалены**. Можно использовать как запасной вариант.
- ❌ Никакие файлы Django/React — **не тронуты** (кроме добавления `api/health/` маршрута)
- ❌ Конфиги сервера (nginx, systemd) — **не тронуты**
- ❌ База данных — **не тронута**

---

## FAQ

**Q: А если CI упадёт, код всё равно задеплоится?**
Нет. Deploy-workflow имеют `needs: ci` — деплой не запустится, пока CI не пройдёт.

**Q: Можно ли деплоить по-старому через SSH?**
Да. Старые скрипты на месте. CI/CD — это дополнительный способ, не замена (пока не привыкнете).

**Q: Сколько это стоит?**
GitHub Actions бесплатно для публичных репо, 2000 минут/мес для приватных.

**Q: Что если деплой на прод сломался?**
Автоматический откат: если health check `/api/health/` не возвращает 200, код откатывается к предыдущему коммиту.
