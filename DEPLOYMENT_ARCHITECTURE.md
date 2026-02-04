# СХЕМА ОКРУЖЕНИЙ - Teaching Panel

```
┌────────────────────────────────────────────────────────────────────┐
│                         🖥️ ОДИН СЕРВЕР                             │
│                      lectiospace.ru (IP)                           │
└────────────────────────────────────────────────────────────────────┘
                                  │
                    ┌─────────────┴──────────────┐
                    │                             │
                    ▼                             ▼
        ┌───────────────────────┐     ┌───────────────────────┐
        │  🇷🇺 РОССИЙСКИЙ РЫНОК  │     │  🌍 АФРИКАНСКИЙ РЫНОК  │
        │   (Стабильность)      │     │    (Эксперименты)     │
        └───────────────────────┘     └───────────────────────┘
                    │                             │
        ┌───────────┴───────────┐                 │
        ▼                       ▼                 ▼
┌──────────────┐       ┌──────────────┐   ┌──────────────┐
│   PROD RU    │       │  STAGE RU    │   │  PROD AFRICA │
├──────────────┤       ├──────────────┤   ├──────────────┤
│lectiospace.ru│       │stage.lect... │   │lect...online │
│              │       │              │   │              │
│Port: 8000    │       │Port: 8001    │   │Port: 8002    │
│Branch: main  │       │Branch:       │   │Branch:       │
│              │       │staging-russia│   │main-africa   │
│Feature Flags:│       │              │   │              │
│✅ YooKassa   │       │✅ YooKassa   │   │❌ YooKassa   │
│✅ Telegram   │       │✅ Telegram   │   │❌ Telegram   │
│❌ PWA        │       │🧪 PWA (test) │   │✅ PWA        │
│❌ Mobile$    │       │🧪 Mobile$ ?  │   │✅ Mobile$    │
│❌ SMS        │       │❌ SMS        │   │✅ SMS        │
│              │       │              │   │              │
│DB:           │       │DB:           │   │DB:           │
│db_russia     │       │db_stage_ru   │   │db_africa     │
│              │       │(копия прода) │   │              │
└──────────────┘       └──────────────┘   └──────────────┘
       ▲                      ▲                   ▲
       │                      │                   │
       │                      │                   │
┌──────┴──────────────────────┴───────────────────┴─────────┐
│                  📱 ТВОЙ НОУТБУК                           │
│                  (только git push!)                        │
│                                                            │
│  git checkout staging-russia  →  stage.lectiospace.ru     │
│  git checkout main            →  lectiospace.ru           │
│  git checkout main-africa     →  lectiospace.online       │
│                                                            │
│  .\deploy_multi.ps1 -Target russia-stage  (тест)          │
│  .\deploy_multi.ps1 -Target russia-prod   (прод РФ)       │
│  .\deploy_multi.ps1 -Target africa-prod   (обкатка)       │
└────────────────────────────────────────────────────────────┘
```

---

## Workflow: Новая фича для России

```
1. РАЗРАБОТКА (ноутбук)
   ┌─────────────────┐
   │ git checkout    │
   │ staging-russia  │
   │                 │
   │ git checkout -b │
   │ feature/fix-bug │
   │                 │
   │ ... пишешь код  │
   │ ... коммитишь   │
   └─────────────────┘
           │
           ▼
2. STAGING (stage.lectiospace.ru)
   ┌─────────────────┐
   │ git push origin │
   │ staging-russia  │
   │                 │
   │ deploy_multi.ps1│
   │ -Target         │
   │ russia-stage    │
   │                 │
   │ 🧪 ТЕСТИРУЕШЬ   │
   │ 2-3 дня         │
   └─────────────────┘
           │
           ▼ (всё ОК?)
3. PRODUCTION (lectiospace.ru)
   ┌─────────────────┐
   │ git checkout    │
   │ main            │
   │ git merge       │
   │ staging-russia  │
   │                 │
   │ deploy_multi.ps1│
   │ -Target         │
   │ russia-prod     │
   │                 │
   │ ✅ В ПРОДЕ РФ   │
   └─────────────────┘
```

---

## Workflow: Новая фича для Африки

```
1. РАЗРАБОТКА (ноутбук)
   ┌─────────────────┐
   │ git checkout    │
   │ main-africa     │
   │                 │
   │ git checkout -b │
   │ feature/pwa     │
   │                 │
   │ ... пишешь код  │
   │ + feature flags │
   └─────────────────┘
           │
           ▼
2. PRODUCTION AFRICA (lectiospace.online)
   ┌─────────────────┐
   │ git merge в     │
   │ main-africa     │
   │                 │
   │ deploy_multi.ps1│
   │ -Target         │
   │ africa-prod     │
   │                 │
   │ ✅ ОБКАТКА!     │
   │ (это прод)      │
   └─────────────────┘
           │
           ▼ (работает отлично?)
3. ПЕРЕНОС В РОССИЮ (опционально)
   ┌─────────────────┐
   │ git checkout    │
   │ staging-russia  │
   │                 │
   │ git cherry-pick │
   │ <commit PWA>    │
   │                 │
   │ Тест на staging │
   │ → прод РФ       │
   └─────────────────┘
```

---

## Стоимость

- Один VPS сервер: **$20-40/мес** (текущий)
- Три окружения на одном: **+$0**
- SSL сертификаты: **$0** (Let's Encrypt)
- **ИТОГО: $0 дополнительно**

---

## Безопасность

### lectiospace.ru (PROD RU)
- ✅ Защищен staging слоем
- ✅ Feature flags для контроля
- ✅ Отдельная БД (невозможно сломать)
- ✅ Требует подтверждение деплоя

### stage.lectiospace.ru (STAGING RU)
- ✅ Тестовые ключи платежей
- ✅ Копия данных прода (периодическая)
- ✅ DEBUG=True (видны ошибки)

### lectiospace.online (PROD AFRICA)
- ✅ Независимая БД
- ✅ Экспериментальные фичи
- ✅ Feature flags для A/B тестов
- ✅ Быстрая итерация

---

## Итого

**Вопрос:** Где тестировать изменения для lectiospace.ru?  
**Ответ:** На **stage.lectiospace.ru**

**Вопрос:** Где обкатывать новые фичи (PWA, Mobile Money)?  
**Ответ:** На **lectiospace.online** (прод Африка)

**Вопрос:** Можно ли держать на одном сервере?  
**Ответ:** **ДА!** Три порта (8000, 8001, 8002), три домена, три изолированные БД

**Результат:**
- 🇷🇺 Россия = стабильность (staging → prod)
- 🌍 Африка = скорость (прямо в прод для обкатки)
- 💰 Экономия = $0 (один сервер)
