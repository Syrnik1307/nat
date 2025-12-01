# 🔐 Telegram Registration Flow - Архитектура

## Концепция: "Мягкая обязательность с защитой безопасности"

### 🎯 Цели
1. ✅ Все учителя имеют привязанный Telegram для восстановления пароля
2. ✅ Не блокировать регистрацию полностью (снизить порог входа)
3. ✅ Обеспечить безопасность через ограничения до привязки
4. ✅ Мотивировать привязку через UX

---

## 📋 Этап 1: Регистрация

### Frontend: AuthPage.js

```javascript
// После успешной регистрации
const handleRegister = async (email, password, role) => {
  const response = await apiClient.post('/api/jwt/register/', {
    email, password, role, /* ... */
  });
  
  // Автологин
  localStorage.setItem('tp_access_token', response.data.access);
  localStorage.setItem('tp_refresh_token', response.data.refresh);
  
  // Для учителей → редирект на привязку Telegram
  if (role === 'teacher') {
    navigate('/onboarding/telegram');
  } else {
    navigate('/student');
  }
};
```

---

## 📋 Этап 2: Страница онбординга (только для учителей)

### Новая страница: `/onboarding/telegram`

**UI компоненты:**
- 🎨 Hero секция с объяснением зачем нужен Telegram
- 📱 QR-код + deep link для быстрой привязки
- 🔢 Код привязки (автоматически генерируется)
- ⏭️ Кнопка "Пропустить сейчас" (с предупреждением)

**Преимущества Telegram (показываем пользователю):**
- ✅ Восстановление пароля за 30 секунд
- ✅ Мгновенные уведомления о новых ДЗ
- ✅ Напоминания о занятиях
- ✅ Быстрая связь с поддержкой

### Код компонента

```javascript
// frontend/src/components/TelegramOnboarding.js
import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { generateTelegramCode, getTelegramStatus } from '../apiService';
import './TelegramOnboarding.css';

const TelegramOnboarding = () => {
  const navigate = useNavigate();
  const [code, setCode] = useState(null);
  const [qrUrl, setQrUrl] = useState('');
  const [deepLink, setDeepLink] = useState('');
  const [loading, setLoading] = useState(true);
  const [checking, setChecking] = useState(false);

  useEffect(() => {
    loadCode();
    // Проверяем статус каждые 3 секунды
    const interval = setInterval(checkStatus, 3000);
    return () => clearInterval(interval);
  }, []);

  const loadCode = async () => {
    try {
      const { data } = await generateTelegramCode();
      setCode(data.code);
      setDeepLink(data.deep_link);
      setQrUrl(`https://api.qrserver.com/v1/create-qr-code/?data=${encodeURIComponent(data.deep_link)}&size=300x300`);
    } catch (err) {
      console.error('Failed to generate code:', err);
    } finally {
      setLoading(false);
    }
  };

  const checkStatus = async () => {
    if (checking) return;
    setChecking(true);
    try {
      const { data } = await getTelegramStatus();
      if (data.telegram_linked) {
        // Успех! Редирект на дашборд
        navigate('/teacher', { 
          state: { message: '✅ Telegram успешно привязан!' } 
        });
      }
    } catch (err) {
      // Не привязан - продолжаем ждать
    } finally {
      setChecking(false);
    }
  };

  const handleSkip = () => {
    if (window.confirm(
      'Без Telegram вы не сможете восстановить пароль через бота.\n\n' +
      'Вы сможете привязать его позже в Профиле → Безопасность.\n\n' +
      'Продолжить без привязки?'
    )) {
      navigate('/teacher');
    }
  };

  if (loading) {
    return <div className="onboarding-loading">Генерируем код...</div>;
  }

  return (
    <div className="telegram-onboarding">
      <div className="onboarding-card">
        <div className="onboarding-header">
          <h1>🔐 Защитите свой аккаунт</h1>
          <p className="onboarding-subtitle">
            Привяжите Telegram для быстрого восстановления пароля и уведомлений
          </p>
        </div>

        <div className="onboarding-content">
          <div className="onboarding-benefits">
            <h3>Что это даёт?</h3>
            <ul>
              <li>✅ Восстановление пароля за 30 секунд</li>
              <li>✅ Мгновенные уведомления о новых ДЗ</li>
              <li>✅ Напоминания о занятиях</li>
              <li>✅ Быстрая связь с поддержкой</li>
            </ul>
          </div>

          <div className="onboarding-steps">
            <h3>Как привязать?</h3>
            
            {/* Вариант 1: QR-код */}
            <div className="onboarding-method">
              <h4>📱 Способ 1: Сканируйте QR-код</h4>
              <div className="qr-container">
                <img src={qrUrl} alt="QR код для привязки" />
                <p className="qr-hint">Наведите камеру телефона</p>
              </div>
            </div>

            <div className="onboarding-divider">или</div>

            {/* Вариант 2: Ручной ввод кода */}
            <div className="onboarding-method">
              <h4>⌨️ Способ 2: Введите код вручную</h4>
              <ol>
                <li>Откройте <a href="https://t.me/nat_panelbot" target="_blank">@nat_panelbot</a> в Telegram</li>
                <li>Отправьте команду <code>/start {code}</code></li>
                <li>Получите подтверждение</li>
              </ol>
              
              <div className="code-display">
                <span className="code-label">Ваш код:</span>
                <span className="code-value">{code}</span>
                <button 
                  className="copy-btn"
                  onClick={() => navigator.clipboard.writeText(`/start ${code}`)}
                >
                  Скопировать команду
                </button>
              </div>
            </div>

            {/* Кнопка быстрого перехода */}
            <a 
              href={deepLink} 
              target="_blank" 
              className="open-telegram-btn"
              rel="noopener noreferrer"
            >
              Открыть Telegram
            </a>
          </div>
        </div>

        <div className="onboarding-footer">
          <p className="waiting-text">
            {checking ? '🔄 Проверяем привязку...' : '⏳ Ожидаем подтверждения из Telegram...'}
          </p>
          
          <button 
            className="skip-btn"
            onClick={handleSkip}
          >
            Пропустить сейчас
          </button>
          
          <p className="skip-hint">
            Вы сможете привязать Telegram позже в Профиле → Безопасность
          </p>
        </div>
      </div>
    </div>
  );
};

export default TelegramOnboarding;
```

---

## 📋 Этап 3: Баннер-напоминание (после пропуска)

### Компонент: TelegramWarningBanner.js

Показывается на всех страницах учителя, если Telegram не привязан.

```javascript
// frontend/src/components/TelegramWarningBanner.js
import React, { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { getTelegramStatus } from '../apiService';
import './TelegramWarningBanner.css';

const TelegramWarningBanner = () => {
  const [show, setShow] = useState(false);
  const [dismissed, setDismissed] = useState(false);

  useEffect(() => {
    checkStatus();
  }, []);

  const checkStatus = async () => {
    try {
      const { data } = await getTelegramStatus();
      if (!data.telegram_linked) {
        setShow(true);
      }
    } catch (err) {
      console.error('Failed to check telegram status:', err);
    }
  };

  const handleDismiss = () => {
    setDismissed(true);
    // Запоминаем в sessionStorage (на сессию)
    sessionStorage.setItem('telegram_banner_dismissed', 'true');
  };

  if (!show || dismissed || sessionStorage.getItem('telegram_banner_dismissed')) {
    return null;
  }

  return (
    <div className="telegram-warning-banner">
      <div className="banner-content">
        <span className="banner-icon">⚠️</span>
        <div className="banner-text">
          <strong>Telegram не привязан</strong>
          <span>Привяжите для восстановления пароля и уведомлений</span>
        </div>
        <Link to="/profile?tab=security" className="banner-action">
          Привязать сейчас
        </Link>
        <button className="banner-dismiss" onClick={handleDismiss}>
          ✕
        </button>
      </div>
    </div>
  );
};

export default TelegramWarningBanner;
```

**Интеграция в TeacherHomePage.js:**

```javascript
import TelegramWarningBanner from './TelegramWarningBanner';

const TeacherHomePage = () => {
  return (
    <div className="teacher-home">
      <TelegramWarningBanner />
      {/* Остальной контент */}
    </div>
  );
};
```

---

## 📋 Этап 4: Ограничения функционала (Security Layer)

### Backend: Модификация password reset

```python
# accounts/views.py

class PasswordResetRequestView(APIView):
    """Запрос на сброс пароля - требует Telegram для учителей"""
    
    def post(self, request):
        email = request.data.get('email')
        user = CustomUser.objects.filter(email=email).first()
        
        if not user:
            # Для безопасности всегда возвращаем success
            return Response({'detail': 'Если email существует, вы получите инструкции'})
        
        # КРИТИЧНО: Учителя ОБЯЗАНЫ использовать Telegram
        if user.role == 'teacher':
            if not user.telegram_verified or not user.telegram_id:
                return Response({
                    'error': 'telegram_required',
                    'detail': 'Для учителей восстановление пароля доступно только через Telegram. Привяжите Telegram в профиле.',
                    'bot_username': 'nat_panelbot'
                }, status=400)
            
            # Отправляем уведомление в Telegram вместо email
            send_telegram_password_reset(user)
            return Response({
                'detail': 'Инструкции отправлены в Telegram',
                'method': 'telegram'
            })
        
        # Студенты могут использовать email
        send_email_password_reset(user)
        return Response({
            'detail': 'Инструкции отправлены на email',
            'method': 'email'
        })
```

### Frontend: Форма сброса пароля

```javascript
// frontend/src/components/ForgotPasswordPage.js

const handleSubmit = async (email) => {
  try {
    const { data } = await apiClient.post('/api/password/reset/', { email });
    
    if (data.method === 'telegram') {
      setMessage('✅ Проверьте Telegram! Мы отправили вам ссылку для сброса пароля.');
    } else {
      setMessage('✅ Проверьте email! Мы отправили инструкции.');
    }
  } catch (err) {
    if (err.response?.data?.error === 'telegram_required') {
      setError(
        'Для учителей сброс пароля доступен только через Telegram.\n\n' +
        'Привяжите Telegram в профиле или обратитесь в поддержку.'
      );
      setShowTelegramHelp(true);
    } else {
      setError('Не удалось отправить запрос. Попробуйте позже.');
    }
  }
};
```

---

## 📋 Этап 5: Email-уведомления (для тех, кто пропустил)

### Backend: Задача Celery

```python
# accounts/tasks.py

@shared_task
def remind_telegram_link():
    """Напоминание о привязке Telegram (запускается раз в день)"""
    from datetime import timedelta
    from django.utils import timezone
    
    # Учителя без Telegram, зарегистрированные более 3 дней назад
    cutoff = timezone.now() - timedelta(days=3)
    teachers = CustomUser.objects.filter(
        role='teacher',
        telegram_verified=False,
        created_at__lte=cutoff
    )
    
    for teacher in teachers:
        send_mail(
            subject='Защитите свой аккаунт — привяжите Telegram',
            message=f'''
            Здравствуйте, {teacher.first_name}!
            
            Вы зарегистрировались в Teaching Panel {teacher.created_at.strftime('%d.%m.%Y')},
            но ещё не привязали Telegram.
            
            Без Telegram вы не сможете:
            - Быстро восстановить пароль
            - Получать уведомления о новых ДЗ
            - Использовать напоминания о занятиях
            
            Привязать Telegram → https://teaching-panel.ru/profile?tab=security
            
            Это займёт 1 минуту!
            ''',
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[teacher.email]
        )

# settings.py - добавить в CELERY_BEAT_SCHEDULE
CELERY_BEAT_SCHEDULE = {
    'remind-telegram-link': {
        'task': 'accounts.tasks.remind_telegram_link',
        'schedule': crontab(hour=10, minute=0),  # Каждый день в 10:00
    },
}
```

---

## 📊 Метрики и аналитика

### Backend: Трекинг статуса привязки

```python
# analytics/views.py

@api_view(['GET'])
@permission_classes([IsAdminUser])
def telegram_link_stats(request):
    """Статистика привязки Telegram"""
    total_teachers = CustomUser.objects.filter(role='teacher').count()
    linked = CustomUser.objects.filter(role='teacher', telegram_verified=True).count()
    
    # По дням с момента регистрации
    from datetime import timedelta
    from django.utils import timezone
    now = timezone.now()
    
    stats = {
        'total': total_teachers,
        'linked': linked,
        'unlinked': total_teachers - linked,
        'percentage': round(linked / total_teachers * 100, 1) if total_teachers else 0,
        'by_age': {
            '0-1_days': CustomUser.objects.filter(
                role='teacher',
                telegram_verified=True,
                created_at__gte=now - timedelta(days=1)
            ).count(),
            '1-7_days': CustomUser.objects.filter(
                role='teacher',
                telegram_verified=True,
                created_at__range=[now - timedelta(days=7), now - timedelta(days=1)]
            ).count(),
            '7+_days': CustomUser.objects.filter(
                role='teacher',
                telegram_verified=True,
                created_at__lt=now - timedelta(days=7)
            ).count(),
        }
    }
    
    return Response(stats)
```

---

## 🎨 UX рекомендации

### 1. Тайминг показа онбординга
- ✅ Сразу после регистрации (когда мотивация высокая)
- ✅ Автопроверка статуса каждые 3 секунды
- ✅ Авто-редирект при успешной привязке

### 2. Тон коммуникации
- ❌ "Обязательно", "Требуется", "Необходимо"
- ✅ "Защитите", "Получите доступ", "Будьте в курсе"

### 3. Visual Hierarchy
- **Главное действие**: QR-код (самый простой способ)
- **Альтернатива**: Ручной ввод кода
- **Escape hatch**: Кнопка "Пропустить" (внизу, серая)

### 4. Gamification (опционально)
- Бейдж "Защищённый аккаунт" после привязки
- Прогресс-бар "Настройте профиль: 3/5"

---

## ✅ Чеклист внедрения

### Backend
- [ ] Миграция: добавить поле `telegram_onboarding_completed` (bool, default=False)
- [ ] Модифицировать `PasswordResetRequestView` (требовать Telegram для учителей)
- [ ] Celery task: `remind_telegram_link` (ежедневное напоминание)
- [ ] Admin endpoint: `/api/admin/telegram-stats/` (метрики)

### Frontend
- [ ] Страница `/onboarding/telegram` (TelegramOnboarding.js)
- [ ] Компонент `TelegramWarningBanner` (показывается до привязки)
- [ ] Редирект после регистрации учителя → `/onboarding/telegram`
- [ ] Модифицировать ForgotPasswordPage (обработка telegram_required error)
- [ ] Добавить query param в ProfilePage: `?tab=security` (прямая ссылка)

### Bot
- [ ] Команда `/verify` — показать статус привязки
- [ ] После успешной привязки — отправить Welcome message с инструкциями

### Testing
- [ ] E2E: регистрация → онбординг → привязка → редирект
- [ ] E2E: регистрация → пропуск → баннер → переход в профиль → привязка
- [ ] Unit: PasswordResetRequestView с/без Telegram
- [ ] Load: 100 одновременных регистраций

---

## 🚀 Поэтапное внедрение

### Фаза 1 (MVP): Soft onboarding
1. Онбординг-страница после регистрации
2. Можно пропустить
3. Баннер-напоминание

### Фаза 2: Ограничения безопасности
1. Сброс пароля только через Telegram для учителей
2. Email-напоминания через 3 дня

### Фаза 3: Мотивация
1. Эксклюзивные фичи для привязанных (например, расширенная аналитика)
2. Gamification (бейджи, прогресс)

---

## 📈 Ожидаемые результаты

- **День 0**: 60% привяжут сразу на онбординге
- **День 3**: 80% привяжут после email-напоминания
- **День 7**: 90% привяжут (остальные 10% — неактивные)

---

**Автор**: GitHub Copilot  
**Дата**: 1 декабря 2025 г.
