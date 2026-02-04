# Git Flow для безопасной разработки

## Структура веток

```
main (production Russia) ← защищена, только через PR
  ├── staging (тестирование) ← merge перед продом
  ├── develop (разработка) ← основная ветка для работы
  │   ├── feature/pwa-offline
  │   ├── feature/mobile-money
  │   ├── feature/adaptive-video
  │   └── feature/multilingual
  └── hotfix/* (срочные фиксы для прода)
```

## Workflow

### 1. Разработка новой фичи (например, PWA)
```bash
# Создаешь ветку от develop
git checkout develop
git pull origin develop
git checkout -b feature/pwa-offline

# Работаешь, коммитишь
git add .
git commit -m "feat(pwa): add service worker for offline mode"

# Пушишь в свою ветку
git push origin feature/pwa-offline

# Создаешь Pull Request: feature/pwa-offline → develop
```

### 2. Тестирование на staging
```bash
# Когда фича готова, мержишь в develop
git checkout develop
git merge feature/pwa-offline
git push origin develop

# Автоматический деплой на staging (через GitHub Actions)
# Тестируешь на https://stage.lectiospace.ru

# Если всё ОК, мержишь в staging ветку
git checkout staging
git merge develop
git push origin staging
```

### 3. Деплой в прод (ТОЛЬКО когда уверен)
```bash
# Создаешь PR: staging → main
# После ревью и тестов - мерж
# Автоматический деплой на lectiospace.ru
```

### 4. Срочный фикс бага в проде
```bash
# От main создаешь hotfix
git checkout main
git checkout -b hotfix/fix-payment-bug

# Фиксишь, коммитишь
git commit -m "fix(payments): handle null subscription"

# PR прямо в main
# После мержа - обратно мержишь в develop
git checkout develop
git merge hotfix/fix-payment-bug
```

## Правила защиты веток

### main (production)
- ❌ Прямой push запрещен
- ✅ Только через Pull Request
- ✅ Минимум 1 approve (от тебя или напарника)
- ✅ Все тесты должны пройти
- ✅ Code review обязателен

### staging
- ✅ Можно мержить из develop свободно
- ✅ Автоматический деплой на stage.lectiospace.ru

### develop
- ✅ Основная ветка для разработки
- ✅ Мержишь feature ветки сюда

### feature/*
- ✅ Свободная разработка
- ✅ Тестируешь локально

## Проверка перед мержем в main

```bash
# Чеклист перед PR в main:
☑️ Все тесты проходят (pytest)
☑️ Код отревьювен
☑️ Протестировано на staging минимум 2 дня
☑️ Feature flags настроены правильно
☑️ Нет хардкода для Africa в коде (только через flags)
☑️ Миграции БД совместимы (backward compatible)
```

## Команды для быстрого переключения

```bash
# Начать новую фичу
npm run feature:start pwa-offline  # создаст feature/pwa-offline

# Финишировать фичу (merge в develop)
npm run feature:finish pwa-offline

# Деплой на staging
npm run deploy:staging

# Деплой в прод (через PR)
npm run deploy:production
```
