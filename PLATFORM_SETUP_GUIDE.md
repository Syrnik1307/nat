# Руководство по подключению платформ видеоконференций

## Обзор

Teaching Panel поддерживает две платформы для проведения уроков:
- **Zoom** — надёжное решение для видеоконференций
- **Google Meet** — альтернатива от Google (требует feature flag `GOOGLE_MEET_ENABLED=1`)

---

## Zoom

### Вариант 1: Общий пул Zoom-аккаунтов (рекомендуется)

Это основной способ — учителя используют общий пул Zoom-аккаунтов платформы.

**Преимущества:**
- Не нужен личный Zoom-аккаунт
- Автоматическое распределение аккаунтов
- Освобождение аккаунта после завершения урока

**Настройка для администратора:**

1. Создайте Zoom-аккаунт(ы) с нужным планом (Pro/Business)
2. В админ-панели Django: **Zoom pool → Zoom accounts → Add**
3. Заполните поля:
   - `Email`: email Zoom-аккаунта
   - `Zoom user ID`: ID пользователя в Zoom (из настроек профиля Zoom)
   - `Is active`: включен
   - `In use`: выключен

### Вариант 2: Личный Zoom-аккаунт

Учитель может подключить свой личный Zoom-аккаунт.

**Инструкция для учителя:**

1. Перейдите в **Профиль → Платформы**
2. В секции "Zoom (личный аккаунт)" нажмите **"Подключить"**
3. Войдите в свой Zoom-аккаунт и разрешите доступ
4. После успешного подключения увидите статус "Подключён"

**Настройка Zoom OAuth для администратора:**

1. Войдите в [Zoom App Marketplace](https://marketplace.zoom.us/)
2. **Develop → Build App → Server-to-Server OAuth**
3. Создайте приложение:
   - App Name: `Teaching Panel`
   - Select scopes: `meeting:write`, `recording:read`
4. Скопируйте:
   - Account ID
   - Client ID
   - Client Secret
5. Добавьте в `.env`:
```env
ZOOM_ACCOUNT_ID=your_account_id
ZOOM_CLIENT_ID=your_client_id
ZOOM_CLIENT_SECRET=your_client_secret
```

---

## Google Meet

> **Внимание**: Для использования Google Meet необходимо включить feature flag `GOOGLE_MEET_ENABLED=1`

### Шаг 1: Создание проекта в Google Cloud Console

1. Перейдите в [Google Cloud Console](https://console.cloud.google.com/)
2. Нажмите **Select a project → New Project**
3. Введите название: `Teaching Panel` → **Create**
4. Дождитесь создания и выберите проект

### Шаг 2: Включение Google Calendar API

1. В боковом меню: **APIs & Services → Library**
2. В поиске введите: `Google Calendar API`
3. Нажмите на **Google Calendar API** → **Enable**

### Шаг 3: Настройка OAuth Consent Screen

1. **APIs & Services → OAuth consent screen**
2. Выберите **External** (или Internal для Workspace)
3. Заполните обязательные поля:
   - **App name**: `Teaching Panel`
   - **User support email**: ваш email
   - **Developer contact information**: ваш email
4. Нажмите **Save and Continue**
5. На экране **Scopes** нажмите **Add or Remove Scopes**:
   - `https://www.googleapis.com/auth/calendar.events`
   - `https://www.googleapis.com/auth/userinfo.email`
6. **Save and Continue**
7. На экране **Test users** добавьте email-ы тестовых учителей
8. **Save and Continue → Back to Dashboard**

### Шаг 4: Создание OAuth Credentials

1. **APIs & Services → Credentials**
2. **+ Create Credentials → OAuth client ID**
3. Application type: **Web application**
4. Name: `Teaching Panel Web Client`
5. **Authorized redirect URIs**: добавьте:
   ```
   http://localhost:8000/api/integrations/google-meet/callback/
   https://your-domain.com/api/integrations/google-meet/callback/
   ```
6. Нажмите **Create**
7. Скопируйте **Client ID** и **Client Secret**

### Шаг 5: Добавление переменных окружения

Добавьте в `.env`:

```env
# Feature flag для Google Meet
GOOGLE_MEET_ENABLED=1

# OAuth credentials
GOOGLE_MEET_CLIENT_ID=your_client_id.apps.googleusercontent.com
GOOGLE_MEET_CLIENT_SECRET=your_client_secret

# Redirect URI (должен совпадать с настройками в Google Console)
GOOGLE_MEET_REDIRECT_URI=http://localhost:8000/api/integrations/google-meet/callback/
# Для продакшена:
# GOOGLE_MEET_REDIRECT_URI=https://your-domain.com/api/integrations/google-meet/callback/
```

### Шаг 6: Подключение для учителя

1. Перейдите в **Профиль → Платформы**
2. В секции "Google Meet" нажмите **"Подключить Google Meet"**
3. В открывшемся окне войдите в Google-аккаунт
4. Разрешите доступ к календарю
5. Вы будете перенаправлены обратно на платформу
6. Статус изменится на "Подключён" с указанием email

### Важные ограничения

- **Квота API**: Стандартный лимит — 1,000,000 запросов в день
- **Действие токенов**: Access token действует 1 час, автоматически обновляется
- **Test users**: Пока приложение в режиме Testing, работает только для добавленных тестовых пользователей
- **Publishing**: Для production отправьте приложение на верификацию Google

---

## Использование платформ при проведении урока

### Запуск урока

1. Откройте карточку урока
2. Нажмите кнопку **"Начать урок"**
3. В появившемся окне выберите платформу:
   - **Zoom из пула** — использует общий аккаунт платформы
   - **Zoom (личный)** — использует ваш подключённый Zoom
   - **Google Meet** — создаёт встречу в Google Meet
4. Нажмите **"Запустить"**
5. Конференция откроется в новой вкладке

### Для студентов

Студенты видят только кнопку **"Присоединиться"** — им не нужно знать, какая платформа используется. Ссылка автоматически ведёт на нужную платформу.

---

## Устранение неполадок

### Zoom

| Проблема | Решение |
|----------|---------|
| "Нет свободных аккаунтов" | Дождитесь освобождения аккаунта или добавьте новые |
| "Invalid credentials" | Проверьте ZOOM_CLIENT_ID и ZOOM_CLIENT_SECRET |
| "OAuth token expired" | Повторно подключите аккаунт в профиле |

### Google Meet

| Проблема | Решение |
|----------|---------|
| "Access denied" | Убедитесь, что ваш email добавлен в Test users |
| "Feature disabled" | Проверьте GOOGLE_MEET_ENABLED=1 в .env |
| "Invalid redirect_uri" | Проверьте соответствие GOOGLE_MEET_REDIRECT_URI в .env и Google Console |
| "Token has been expired or revoked" | Отключите и подключите Google Meet заново |

---

## Checklist для production

- [ ] GOOGLE_MEET_ENABLED=1 в production
- [ ] Production redirect URI добавлен в Google Console
- [ ] Приложение опубликовано (или все учителя в Test users)
- [ ] HTTPS настроен (обязательно для OAuth)
- [ ] Zoom-аккаунты добавлены в пул

---

## Ссылки

- [Zoom App Marketplace](https://marketplace.zoom.us/)
- [Google Cloud Console](https://console.cloud.google.com/)
- [Google Calendar API Documentation](https://developers.google.com/calendar/api)
- [OAuth 2.0 Scopes](https://developers.google.com/identity/protocols/oauth2/scopes)

---

*Последнее обновление: Январь 2025*
