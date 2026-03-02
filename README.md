# Lectio Space

> LMS-платформа для преподавателей: уроки, домашние задания, записи, Zoom-интеграция, подписки.

**[Полное руководство](docs/GUIDES.md)** | **[AI-инструкции](.github/copilot-instructions.md)** | **[UX-правила](FRONTEND_SMOOTHNESS_RULES.md)**

---

## Технологический стек

- **Backend**: Django 5.2 + Django REST Framework + JWT
- **Frontend**: React 18 + React Router v6
- **Database**: SQLite (dev) / PostgreSQL (production)
- **Payments**: YooKassa + T-Bank
- **Integrations**: Zoom API (Server-to-Server OAuth), Telegram Bot, Google Drive, Google Meet
- **Production**: lectiospace.ru, VPS 72.56.81.163

## Структура проекта

```
nat/
├── teaching_panel/              # Django backend
│   ├── accounts/                # Аутентификация, подписки, платежи
│   ├── schedule/                # Уроки, группы, записи, посещаемость
│   ├── homework/                # Домашние задания и сдачи
│   ├── analytics/               # Журнал, контрольные точки, статистика
│   ├── zoom_pool/               # Пул Zoom-аккаунтов
│   ├── support/                 # Тикеты поддержки + Telegram
│   ├── core/                    # Legacy courses module
│   └── teaching_panel/settings.py
├── frontend/                    # React SPA
│   ├── src/apiService.js        # Axios + JWT auto-refresh
│   ├── src/auth.js              # AuthContext
│   ├── src/components/          # Страницы
│   ├── src/modules/             # Фичи (homework-analytics, Recordings, chat)
│   └── src/shared/components/   # Button, Input, Modal, Card, Badge
├── docs/                        # Документация
│   ├── GUIDES.md                # Сводное руководство по всем интеграциям
│   ├── ERRORS/                  # Решения известных ошибок
│   └── knowledge/               # FAQ и troubleshooting для пользователей
└── deploy/                      # Конфигурации деплоя и масштабирования
```

## Быстрый старт

### Backend

```powershell
cd teaching_panel
..\venv\Scripts\Activate.ps1
pip install -r requirements.txt
python manage.py migrate
python manage.py runserver          # http://127.0.0.1:8000
```

### Frontend

```powershell
cd frontend
npm install
npm start                           # http://localhost:3000
> Django ДОЛЖЕН быть запущен до тестирования фронтенда.

## Деплой

```powershell
.\auto_deploy.ps1                    # Автоматический деплой (интерактивное меню)
.\deploy_fast.ps1 -SkipDeps         # Быстрый деплой без обновления зависимостей
.\deploy_to_production.ps1           # Production деплой с бэкапом БД
```

Подробности: [docs/GUIDES.md](docs/GUIDES.md#2-деплой)

## Ключевые API

```
POST /api/jwt/token/                       # Логин -> {access, refresh}
POST /api/jwt/register/                    # Регистрация
POST /api/schedule/lessons/{id}/start-new/ # Запуск урока через Zoom Pool
POST /api/schedule/lessons/quick-start/    # Быстрый урок
POST /api/subscription/create-payment/     # Создать платёж
GET  /api/me/                              # Текущий пользователь
```

Полный API reference: [docs/GUIDES.md](docs/GUIDES.md#22-api-reference)

## Документация

| Документ | Описание |
|----------|----------|
| [docs/GUIDES.md](docs/GUIDES.md) | Сводное руководство (деплой, Zoom, GDrive, платежи, Telegram, и т.д.) |
| [.github/copilot-instructions.md](.github/copilot-instructions.md) | Инструкции для AI-агента, архитектура, конвенции |
| [FRONTEND_SMOOTHNESS_RULES.md](FRONTEND_SMOOTHNESS_RULES.md) | Правила плавного UI |
| [docs/ERRORS/](docs/ERRORS/) | Решения известных production-ошибок |
| [docs/knowledge/](docs/knowledge/) | FAQ и troubleshooting для пользователей |

## Лицензия

MIT
