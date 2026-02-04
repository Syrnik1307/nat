# Git Workflow для одного человека (без localhost)

## Структура веток

```
main (lectiospace.ru - PRODUCTION)
  |
  └── staging (lectiospace.online - STAGING)
       |
       └── feature/pwa-offline (твоя ветка для разработки)
```

## Ежедневная работа

### 1. Начинаешь новую фичу
```powershell
# Создаешь ветку от staging
git checkout staging
git pull origin staging
git checkout -b feature/pwa-offline

# Работаешь, коммитишь
git add .
git commit -m "feat(pwa): add service worker"
git push origin feature/pwa-offline
```

### 2. Тестирование на staging (lectiospace.online)
```powershell
# Мержишь в staging
git checkout staging
git merge feature/pwa-offline
git push origin staging

# Деплой на lectiospace.online (АВТОМАТИЧЕСКИ на сервере!)
.\deploy_simple.ps1 -Target staging

# Открываешь https://lectiospace.online - тестируешь
```

### 3. Когда всё работает - в прод
```powershell
# Мержишь staging в main
git checkout main
git merge staging
git push origin main

# Деплой на lectiospace.ru (прод)
.\deploy_simple.ps1 -Target production

# Всё! Прод обновлен
```

### 4. Срочный фикс бага в проде
```powershell
# Фиксишь прямо в main
git checkout main
git checkout -b hotfix/payment-bug
# ... фиксишь ...
git commit -m "fix(payments): handle null user"

# Деплой hotfix
git checkout main
git merge hotfix/payment-bug
.\deploy_simple.ps1 -Target production

# Не забудь слить обратно в staging!
git checkout staging
git merge main
git push origin staging
```

## Зачем нужен staging (lectiospace.online)?

✅ **Тестируешь на реальном сервере** (не на слабом ноутбуке)
✅ **С реальным доменом и SSL** (как в проде)
✅ **Можешь показать клиентам/тестерам** (дать ссылку)
✅ **Баги находишь ДО прода** (prод не ломается)
✅ **Feature flags протестированы** (переключаешь и смотришь)

## Простое правило

```
1. Пишешь код → коммитишь → пушишь в feature ветку
2. Мержишь в staging → деплоишь на lectiospace.online → тестируешь
3. Всё ОК → мержишь в main → деплоишь на lectiospace.ru (прод)
```

## Команды на каждый день

```powershell
# Деплой на staging (для тестирования)
.\deploy_simple.ps1 -Target staging

# Деплой в прод (когда уверен)
.\deploy_simple.ps1 -Target production

# Проверить статус на сервере
ssh root@lectiospace.ru "systemctl status teaching-panel-staging"
ssh root@lectiospace.ru "systemctl status teaching-panel"

# Посмотреть логи
ssh root@lectiospace.ru "tail -f /var/www/teaching-panel-staging/logs/error.log"
ssh root@lectiospace.ru "tail -f /var/www/teaching-panel/logs/error.log"
```

## Что происходит при деплое?

1. **На ноутбуке:** только `git push` (легко!)
2. **На сервере:** 
   - Git pull
   - Установка зависимостей
   - Миграции БД
   - Build фронтенда (на сервере!)
   - Restart сервиса
   - Проверка

**Твой ноутбук НЕ НАПРЯГАЕТСЯ!** Всё происходит на сервере.
