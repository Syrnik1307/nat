# Google reCAPTCHA v3 - Руководство по настройке

## Что такое reCAPTCHA v3?

Google reCAPTCHA v3 - это невидимая защита от ботов, которая работает в фоновом режиме без необходимости решать головоломки. Система оценивает поведение пользователя и выдает score от 0.0 (бот) до 1.0 (человек).

## Регистрация и получение ключей

### Шаг 1: Регистрация сайта

1. Перейдите на https://www.google.com/recaptcha/admin/create
2. Войдите в свой Google аккаунт
3. Заполните форму регистрации:
   - **Label** (Метка): `Teaching Panel` (или любое название проекта)
   - **reCAPTCHA type**: Выберите **reCAPTCHA v3**
   - **Domains** (Домены): 
     - `localhost` (для разработки)
     - `127.0.0.1` (для разработки)
     - Ваш production домен (если есть)
4. Примите условия использования
5. Нажмите **Submit**

### Шаг 2: Получение ключей

После регистрации вы получите два ключа:

- **Site Key** (Открытый ключ) - используется на фронтенде
- **Secret Key** (Секретный ключ) - используется на бэкенде

⚠️ **ВАЖНО**: Secret Key должен храниться в секрете и никогда не публиковаться в коде!

## Настройка бэкенда (Django)

### 1. Установка пакета

```bash
pip install django-recaptcha
```

### 2. Настройка в settings.py

Уже настроено! Добавлено в `teaching_panel/settings.py`:

```python
# Google reCAPTCHA v3
RECAPTCHA_PUBLIC_KEY = os.environ.get('RECAPTCHA_SITE_KEY', '6LeIxAcTAAAAAJcZVRqyHh71UMIEGNQ_MXjiZKhI')
RECAPTCHA_PRIVATE_KEY = os.environ.get('RECAPTCHA_SECRET_KEY', '6LeIxAcTAAAAAGG-vFI1TnRWxMZNFuojJ4WifJWe')
RECAPTCHA_REQUIRED_SCORE = 0.5  # Минимальный score (0.0-1.0)
RECAPTCHA_ENABLED = os.environ.get('RECAPTCHA_ENABLED', 'false').lower() == 'true'
```

### 3. Установка переменных окружения

#### Windows PowerShell:
```powershell
$env:RECAPTCHA_SITE_KEY = "ваш_site_key"
$env:RECAPTCHA_SECRET_KEY = "ваш_secret_key"
$env:RECAPTCHA_ENABLED = "true"
```

#### Linux/Mac:
```bash
export RECAPTCHA_SITE_KEY="ваш_site_key"
export RECAPTCHA_SECRET_KEY="ваш_secret_key"
export RECAPTCHA_ENABLED="true"
```

### 4. Использование в коде

reCAPTCHA уже интегрирована в:

1. **Регистрация** (`register_user` в `accounts/views.py`):
   ```python
   # Проверка токена при регистрации
   recaptcha_token = data.get('recaptcha_token')
   recaptcha_result = verify_recaptcha(recaptcha_token, action='register')
   ```

2. **Email верификация** (`send_verification_email` в `accounts/email_views.py`):
   ```python
   # Опциональная проверка при отправке email
   recaptcha_token = request.data.get('recaptcha_token')
   recaptcha_result = verify_recaptcha(recaptcha_token, action='send_verification')
   ```

## Настройка фронтенда (React)

### 1. Добавить скрипт Google reCAPTCHA

В `frontend/public/index.html` добавьте перед закрывающим `</head>`:

```html
<script src="https://www.google.com/recaptcha/api.js?render=YOUR_SITE_KEY"></script>
```

Замените `YOUR_SITE_KEY` на ваш реальный Site Key.

### 2. Создать компонент для reCAPTCHA

Создайте `frontend/src/components/useRecaptcha.js`:

```javascript
import { useEffect } from 'react';

export const useRecaptcha = () => {
  useEffect(() => {
    // Загружаем reCAPTCHA скрипт
    const siteKey = process.env.REACT_APP_RECAPTCHA_SITE_KEY || '6LeIxAcTAAAAAJcZVRqyHh71UMIEGNQ_MXjiZKhI';
    
    const script = document.createElement('script');
    script.src = `https://www.google.com/recaptcha/api.js?render=${siteKey}`;
    script.async = true;
    document.head.appendChild(script);
    
    return () => {
      document.head.removeChild(script);
    };
  }, []);
  
  const executeRecaptcha = async (action) => {
    const siteKey = process.env.REACT_APP_RECAPTCHA_SITE_KEY || '6LeIxAcTAAAAAJcZVRqyHh71UMIEGNQ_MXjiZKhI';
    
    return new Promise((resolve, reject) => {
      if (!window.grecaptcha) {
        reject(new Error('reCAPTCHA not loaded'));
        return;
      }
      
      window.grecaptcha.ready(() => {
        window.grecaptcha.execute(siteKey, { action })
          .then(token => resolve(token))
          .catch(error => reject(error));
      });
    });
  };
  
  return { executeRecaptcha };
};
```

### 3. Использование в форме регистрации

```javascript
import { useRecaptcha } from './useRecaptcha';

const RegisterPage = () => {
  const { executeRecaptcha } = useRecaptcha();
  
  const handleSubmit = async (e) => {
    e.preventDefault();
    
    try {
      // Получаем токен reCAPTCHA
      const recaptchaToken = await executeRecaptcha('register');
      
      // Отправляем запрос с токеном
      const response = await fetch('http://localhost:8000/accounts/jwt/register/', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          email,
          password,
          role,
          recaptcha_token: recaptchaToken  // Добавляем токен
        })
      });
      
      // Обрабатываем ответ
      const data = await response.json();
      if (data.recaptcha_error) {
        alert('Ошибка защиты от роботов. Попробуйте позже.');
      }
    } catch (error) {
      console.error('reCAPTCHA error:', error);
    }
  };
  
  return (
    // Ваша форма
  );
};
```

### 4. Переменные окружения для фронтенда

Создайте `.env` в папке `frontend/`:

```
REACT_APP_RECAPTCHA_SITE_KEY=ваш_site_key
```

## Режимы работы

### Режим разработки (reCAPTCHA отключена)

По умолчанию reCAPTCHA **отключена** (`RECAPTCHA_ENABLED=false`). В этом режиме:

- ✅ Все запросы проходят без проверки
- ✅ Не нужно настраивать ключи
- ✅ Удобно для тестирования

### Режим production (reCAPTCHA включена)

Установите `RECAPTCHA_ENABLED=true` для активации:

```powershell
$env:RECAPTCHA_ENABLED = "true"
```

В этом режиме:

- 🔒 Проверяется каждый запрос
- 🔒 Требуются реальные ключи от Google
- 🔒 Блокируются подозрительные запросы (score < 0.5)

## Тестовые ключи Google

Google предоставляет тестовые ключи для разработки:

**Site Key (публичный):**
```
6LeIxAcTAAAAAJcZVRqyHh71UMIEGNQ_MXjiZKhI
```

**Secret Key (приватный):**
```
6LeIxAcTAAAAAGG-vFI1TnRWxMZNFuojJ4WifJWe
```

⚠️ **Эти ключи всегда возвращают success** и предназначены только для тестирования!

## Настройка Score

Score reCAPTCHA v3 находится в диапазоне 0.0 - 1.0:

- **1.0** - Определенно человек
- **0.9-0.7** - Вероятно человек
- **0.5** - Граница (по умолчанию)
- **0.3-0.0** - Вероятно бот

Рекомендуемые значения:

```python
# Строгий режим (меньше ботов, больше false positives)
RECAPTCHA_REQUIRED_SCORE = 0.7

# Стандартный режим (баланс)
RECAPTCHA_REQUIRED_SCORE = 0.5  # По умолчанию

# Мягкий режим (больше ботов, меньше false positives)
RECAPTCHA_REQUIRED_SCORE = 0.3
```

## API Endpoints с reCAPTCHA

### Регистрация
```bash
POST /accounts/jwt/register/
{
  "email": "user@example.com",
  "password": "Password123",
  "role": "student",
  "recaptcha_token": "03AGdBq24..."
}
```

### Отправка email верификации
```bash
POST /accounts/api/email/send-verification/
{
  "email": "user@example.com",
  "recaptcha_token": "03AGdBq24..."  # опционально
}
```

## Ошибки reCAPTCHA

Возможные ошибки от Google API:

- `missing-input-secret` - Secret key не указан
- `invalid-input-secret` - Secret key неверный
- `missing-input-response` - Токен не указан
- `invalid-input-response` - Токен неверный или истек
- `timeout-or-duplicate` - Токен уже использован или истек
- `bad-request` - Неверный формат запроса

## Мониторинг в Google Console

После настройки вы можете:

1. Перейти на https://www.google.com/recaptcha/admin
2. Выбрать свой сайт
3. Просматривать статистику:
   - Количество запросов
   - Распределение score
   - География запросов
   - Подозрительная активность

## Troubleshooting

### reCAPTCHA не работает на localhost

Убедитесь, что `localhost` добавлен в список доменов в Google Console.

### Score всегда 0.0 или 1.0

Проверьте, не используете ли вы тестовые ключи в production.

### "reCAPTCHA not loaded"

Убедитесь, что скрипт Google загружен:
```html
<script src="https://www.google.com/recaptcha/api.js?render=YOUR_SITE_KEY"></script>
```

## Полезные ссылки

- 📚 [Официальная документация reCAPTCHA v3](https://developers.google.com/recaptcha/docs/v3)
- 🔧 [Google reCAPTCHA Admin Console](https://www.google.com/recaptcha/admin)
- 📦 [django-recaptcha на GitHub](https://github.com/torchbox/django-recaptcha)
- 🧪 [Тестирование reCAPTCHA](https://developers.google.com/recaptcha/docs/faq#id-like-to-run-automated-tests-with-recaptcha.-what-should-i-do)

## Быстрый старт

1. **Получить ключи**: https://www.google.com/recaptcha/admin/create
2. **Установить переменные окружения**:
   ```powershell
   $env:RECAPTCHA_SITE_KEY = "ваш_site_key"
   $env:RECAPTCHA_SECRET_KEY = "ваш_secret_key"
   $env:RECAPTCHA_ENABLED = "true"
   ```
3. **Добавить Site Key на фронтенд** в `.env`:
   ```
   REACT_APP_RECAPTCHA_SITE_KEY=ваш_site_key
   ```
4. **Использовать в формах** - передавать `recaptcha_token` в API запросах

✅ Готово! reCAPTCHA защищает ваше приложение от ботов.
