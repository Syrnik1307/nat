# Git Strategy для двух независимых продуктов

## Структура веток

```
┌─────────────────────────────────────────┐
│  РОССИЙСКИЙ ПРОДУКТ (lectiospace.ru)    │
└─────────────────────────────────────────┘
main (lectiospace.ru - PRODUCTION RU)
  │
  └── staging-russia (stage.lectiospace.ru - STAGING RU)
       │
       └── feature/fix-payments-ru
       └── feature/new-analytics-ru

┌─────────────────────────────────────────┐
│  АФРИКАНСКИЙ ПРОДУКТ (lectiospace.online)│
└─────────────────────────────────────────┘
main-africa (lectiospace.online - PRODUCTION AFRICA)
  │
  └── feature/pwa-offline
  └── feature/mobile-money
  └── feature/adaptive-video
```

---

## Workflow: Изменения для РОССИИ

### Сценарий: Фикс бага или новая фича для RU рынка

```powershell
# 1. Создаешь ветку от staging-russia
git checkout staging-russia
git pull origin staging-russia
git checkout -b feature/fix-payment-bug-ru

# 2. Работаешь, коммитишь
git add .
git commit -m "fix(payments): handle subscription edge case"
git push origin feature/fix-payment-bug-ru

# 3. Мержишь в staging-russia
git checkout staging-russia
git merge feature/fix-payment-bug-ru
git push origin staging-russia

# 4. Деплой на STAGING RUSSIA (тестирование!)
.\deploy_multi.ps1 -Target russia-stage

# 5. Тестируешь на https://stage.lectiospace.ru
# - Проверяешь фикс
- Тестируешь оплату (тестовый YooKassa)
# - Смотришь нет ли регрессий
# - 2-3 дня в staging

# 6. Когда всё ОК - в PRODUCTION RUSSIA
git checkout main
git merge staging-russia
git push origin main

# 7. Деплой в ПРОД (требуется подтверждение!)
.\deploy_multi.ps1 -Target russia-prod
# Введи "DEPLOY" для подтверждения

# ✅ Изменения в российском проде!
```

---

## Workflow: Разработка для АФРИКИ

### Сценарий: Новая фича для африканского рынка

```powershell
# 1. Создаешь ветку от main-africa
git checkout main-africa
git pull origin main-africa
git checkout -b feature/pwa-offline

# 2. Разрабатываешь фичу с feature flags
# Backend: @require_feature('PWA_OFFLINE')
# Frontend: featureFlags.isEnabled('pwaOffline')

# 3. Коммитишь
git add .
git commit -m "feat(pwa): add service worker for offline mode"
git push origin feature/pwa-offline

# 4. Мержишь ПРЯМО в main-africa (нет staging!)
git checkout main-africa
git merge feature/pwa-offline
git push origin main-africa

# 5. Деплой на lectiospace.online (это и есть "обкатка")
.\deploy_multi.ps1 -Target africa-prod

# 6. Тестируешь на lectiospace.online
# - Фича включена через feature flags
# - Мониторишь логи, ошибки
# - Собираешь feedback
# - Это PRODUCTION, но для экспериментов!

# ✅ Фича обкатана в Африке
```

---

## Переезд фичи из Африки в Россию

### Сценарий: PWA отлично работает в Африке, хотим в России

```powershell
# 1. Фича уже в main-africa, работает на lectiospace.online
# Проверяем что feature flag настроен правильно

# 2. Cherry-pick коммитов из main-africa в staging-russia
git checkout staging-russia
git log main-africa --oneline | grep "pwa"  # находим нужные коммиты
git cherry-pick abc123def456  # коммит с PWA

# Или мерж конкретных файлов:
git checkout main-africa -- teaching_panel/pwa/
git checkout main-africa -- frontend/src/serviceWorker.js
git commit -m "feat(pwa): bring PWA from Africa to Russia"

# 3. Обновляем feature flags для staging
# В settings_staging_russia.py:
# FEATURE_PWA_OFFLINE = True

# 4. Тестируем на stage.lectiospace.ru
git push origin staging-russia
.\deploy_multi.ps1 -Target russia-stage

# 5. Когда ОК - включаем в проде России
# В settings_production_russia.py:
# FEATURE_PWA_OFFLINE = True

git checkout main
git merge staging-russia
.\deploy_multi.ps1 -Target russia-prod

# ✅ Фича из Африки теперь и в России!
```

---

## Критичные правила

### ❌ НИКОГДА не делай:
- Прямой push в `main` (RU прод) без staging
- Деплой в RU прод без 2-3 дней в staging
- Тестирование платежей на lectiospace.ru (только staging!)

### ✅ ВСЕГДА делай:
- Новые фичи для РФ: `staging-russia` → `main`
- Эксперименты: сразу в `main-africa` (lectiospace.online)
- Feature flags для новых фич (можно откатить без деплоя)

---

## Команды на каждый день

```powershell
# Деплой для тестирования российских изменений
.\deploy_multi.ps1 -Target russia-stage

# Деплой в российский прод (осторожно!)
.\deploy_multi.ps1 -Target russia-prod

# Деплой для обкатки африканских фич
.\deploy_multi.ps1 -Target africa-prod

# Статус всех сервисов
ssh nat@lectiospace.ru "
    systemctl status teaching-panel --no-pager | head -3
    systemctl status teaching-panel-stage-ru --no-pager | head -3
    systemctl status teaching-panel-africa --no-pager | head -3
"

# Логи всех окружений
ssh nat@lectiospace.ru "
    echo '=== RUSSIA PROD ===' && tail -5 /var/www/teaching-panel/logs/error.log && \
    echo '=== RUSSIA STAGE ===' && tail -5 /var/www/teaching-panel-stage-ru/logs/error.log && \
    echo '=== AFRICA PROD ===' && tail -5 /var/www/teaching-panel-africa/logs/error.log
"
```

---

## Сценарии использования

### 🇷🇺 Разработка для России (стабильность)
1. Пишешь фичу → `feature/new-thing-ru`
2. Тестируешь на `stage.lectiospace.ru` (2-3 дня)
3. Деплой в `lectiospace.ru` (прод)
4. **Никакого риска для пользователей!**

### 🌍 Разработка для Африки (скорость)
1. Пишешь фичу → `feature/pwa-offline`
2. Деплой сразу на `lectiospace.online` (прод Африка)
3. Обкатка на реальных пользователях
4. Быстрая итерация, feature flags для контроля

### 🔄 Перенос проверенных фич
1. Фича работает в Африке? Cherry-pick в RU staging
2. Тестируешь на `stage.lectiospace.ru`
3. Включаешь в `lectiospace.ru`
4. **Двойная проверка = минимум багов**

---

## Преимущества этой стратегии

✅ **Россия защищена** (staging ловит баги)
✅ **Африка = полигон** (быстрая обкатка)
✅ **Один сервер** (экономия ~$0)
✅ **Изолированные базы** (нельзя сломать прод РФ)
✅ **Feature flags** (откат без деплоя)
✅ **Разные фичи** (YooKassa в РФ, Mobile Money в Африке)

---

## FAQ

**Q: Где тестировать изменения для lectiospace.ru?**  
A: На `stage.lectiospace.ru` (точная копия прода)

**Q: Где обкатывать PWA, Mobile Money и т.д.?**  
A: На `lectiospace.online` (прод Африка)

**Q: Можно ли откатить фичу без деплоя?**  
A: Да! Выключить feature flag через админку или .env

**Q: Что если баг в staging России?**  
A: Фиксишь в `staging-russia`, тестируешь, потом в `main`

**Q: Что если баг в проде Африки?**  
A: Фиксишь в `main-africa`, деплоишь (это "обкатка")

**Q: Как не сломать российский прод?**  
A: ВСЕГДА через `staging-russia` → `main`, без исключений!
