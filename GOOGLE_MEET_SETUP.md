# Настройка интеграции Google Meet

## Шаг 1: Создание проекта в Google Cloud Console

1. Перейдите на https://console.cloud.google.com/
2. Создайте новый проект или выберите существующий
3. В меню выберите **APIs & Services** → **Library**
4. Найдите и включите **Google Calendar API**

## Шаг 2: Создание OAuth 2.0 Credentials

1. Перейдите в **APIs & Services** → **Credentials**
2. Нажмите **+ CREATE CREDENTIALS** → **OAuth client ID**
3. Если требуется настроить OAuth consent screen:
   - User Type: **External** (для тестирования) или **Internal** (если G Suite)
   - App name: **Lectio Space**
   - User support email: ваш email
   - Scopes: добавьте:
     - `https://www.googleapis.com/auth/calendar.events`
     - `https://www.googleapis.com/auth/userinfo.email`
     - `openid`
   - Test users: добавьте email учителей для тестирования
4. Вернитесь в **Credentials** → **Create OAuth client ID**
5. Application type: **Web application**
6. Name: **Lectio Space Meet Integration**
7. Authorized redirect URIs: добавьте:
   - `https://lectio.tw1.ru/api/integrations/google-meet/callback/`
8. Нажмите **CREATE**
9. Скопируйте **Client ID** и **Client Secret**

## Шаг 3: Настройка переменных окружения на сервере

SSH на сервер и добавьте переменные в `/etc/systemd/system/teaching_panel.service.d/override.conf`:

```bash
sudo nano /etc/systemd/system/teaching_panel.service.d/override.conf
```

Добавьте в секцию `[Service]`:

```ini
Environment="GOOGLE_MEET_ENABLED=1"
Environment="GOOGLE_MEET_CLIENT_ID=ваш-client-id.apps.googleusercontent.com"
Environment="GOOGLE_MEET_CLIENT_SECRET=ваш-client-secret"
Environment="GOOGLE_MEET_REDIRECT_URI=https://lectio.tw1.ru/api/integrations/google-meet/callback/"
```

Перезапустите сервис:

```bash
sudo systemctl daemon-reload
sudo systemctl restart teaching_panel
```

## Шаг 4: Проверка

1. Откройте https://lectio.tw1.ru/profile?tab=platforms
2. Кнопка "Подключить" для Google Meet должна стать активной
3. При нажатии откроется страница авторизации Google
4. После подтверждения доступа вы вернётесь на страницу профиля

## Важно: OAuth Consent Screen

Если приложение в режиме "Testing", только добавленные тест-пользователи смогут авторизоваться.

Для публикации приложения нужно:
1. Добавить Privacy Policy URL
2. Пройти верификацию Google (если нужны sensitive scopes)

## Troubleshooting

### Ошибка "redirect_uri_mismatch"
- Проверьте, что redirect URI в Google Console **точно** совпадает с `GOOGLE_MEET_REDIRECT_URI`
- Убедитесь, что используется HTTPS

### Ошибка "access_denied"
- Проверьте, что email пользователя добавлен в Test users (если в режиме Testing)
- Проверьте, что все scopes добавлены в OAuth consent screen

### Ошибка "invalid_client"
- Проверьте правильность Client ID и Client Secret
- Убедитесь, что нет лишних пробелов в переменных окружения
