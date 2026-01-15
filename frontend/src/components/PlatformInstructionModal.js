import React from 'react';
import { Button } from '../shared/components';
import './PlatformInstructionModal.css';

/**
 * Модальное окно с инструкцией по подключению Zoom или Google Meet
 */

const IconClose = () => (
  <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
    <line x1="18" y1="6" x2="6" y2="18"/>
    <line x1="6" y1="6" x2="18" y2="18"/>
  </svg>
);

const IconPlay = () => (
  <svg width="16" height="16" viewBox="0 0 24 24" fill="currentColor">
    <polygon points="5,3 19,12 5,21"/>
  </svg>
);

const IconExternalLink = () => (
  <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
    <path d="M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6"/>
    <polyline points="15,3 21,3 21,9"/>
    <line x1="10" y1="14" x2="21" y2="3"/>
  </svg>
);

// Инструкции для каждой платформы
const PLATFORM_DATA = {
  zoom: {
    name: 'Zoom',
    color: '#0d6efd',
    gradient: 'linear-gradient(135deg, #0d6efd 0%, #1d4ed8 100%)',
    icon: (
      <svg viewBox="0 0 24 24" fill="currentColor" width="32" height="32">
        <path d="M4.585 11.828V16a2 2 0 002 2h7.829a2 2 0 002-2v-4.172a2 2 0 00-2-2H6.585a2 2 0 00-2 2zm13.243 4.415l2.829 2.122a.75.75 0 001.193-.607V10.071a.75.75 0 00-1.193-.607l-2.829 2.122v4.657z"/>
      </svg>
    ),
    videoUrl: 'https://www.youtube.com/watch?v=dQw4w9WgXcQ', // Заменить на реальное видео
    instructions: [
      {
        title: 'Создайте Zoom приложение',
        description: 'Перейдите в Zoom Marketplace и создайте Server-to-Server OAuth приложение',
        link: 'https://marketplace.zoom.us/',
        linkText: 'Открыть Zoom Marketplace'
      },
      {
        title: 'Скопируйте учётные данные',
        description: 'Account ID, Client ID и Client Secret из созданного приложения'
      },
      {
        title: 'Передайте администратору',
        description: 'Отправьте эти данные администратору платформы для добавления в систему'
      },
      {
        title: 'Проверьте подключение',
        description: 'После настройки администратором Zoom появится как доступная платформа'
      }
    ],
    oauthInstructions: [
      {
        title: 'Нажмите "Подключить"',
        description: 'Откроется страница авторизации Zoom'
      },
      {
        title: 'Войдите в Zoom аккаунт',
        description: 'Используйте ваш Zoom аккаунт для входа'
      },
      {
        title: 'Разрешите доступ',
        description: 'Подтвердите разрешение на создание конференций'
      },
      {
        title: 'Готово',
        description: 'Вы будете перенаправлены обратно на платформу'
      }
    ],
    tips: [
      'Zoom работает без регистрации для учеников',
      'Поддерживается автоматическая запись уроков',
      'Можно использовать с любого устройства'
    ]
  },
  google_meet: {
    name: 'Google Meet',
    color: '#16a34a',
    gradient: 'linear-gradient(135deg, #16a34a 0%, #00832d 100%)',
    icon: (
      <svg viewBox="0 0 24 24" fill="currentColor" width="32" height="32">
        <path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm-2 15l-5-5 1.41-1.41L10 14.17l7.59-7.59L19 8l-9 9z"/>
      </svg>
    ),
    videoUrl: 'https://www.youtube.com/watch?v=dQw4w9WgXcQ', // Заменить на реальное видео
    instructions: [
      {
        title: 'Нажмите "Подключить"',
        description: 'Откроется страница авторизации Google'
      },
      {
        title: 'Выберите Google аккаунт',
        description: 'Используйте аккаунт, с которого хотите создавать встречи'
      },
      {
        title: 'Разрешите доступ к календарю',
        description: 'Платформа создаёт события в Google Calendar с ссылкой на Meet'
      },
      {
        title: 'Готово',
        description: 'После подтверждения вы вернётесь на платформу'
      }
    ],
    tips: [
      'Ученикам нужен Google аккаунт для входа',
      'Записи настраиваются в вашем Google аккаунте',
      'Интеграция с Google Calendar'
    ]
  }
};

const PlatformInstructionModal = ({ 
  platform, // 'zoom' | 'google_meet'
  isOpen, 
  onClose, 
  onConnect,
  isConnecting = false
}) => {
  if (!isOpen || !platform) return null;

  const data = PLATFORM_DATA[platform];
  if (!data) return null;

  const handleBackdropClick = (e) => {
    if (e.target === e.currentTarget) {
      onClose();
    }
  };

  const handleVideoClick = () => {
    if (data.videoUrl) {
      window.open(data.videoUrl, '_blank', 'noopener,noreferrer');
    }
  };

  return (
    <div className="platform-modal-overlay" onClick={handleBackdropClick}>
      <div className="platform-modal">
        <button className="platform-modal-close" onClick={onClose}>
          <IconClose />
        </button>

        {/* Заголовок */}
        <div className="platform-modal-header" style={{ '--platform-color': data.color, '--platform-gradient': data.gradient }}>
          <div className="platform-modal-icon">
            {data.icon}
          </div>
          <div className="platform-modal-title-group">
            <h2>Подключение {data.name}</h2>
            <p>Следуйте инструкции для настройки интеграции</p>
          </div>
        </div>

        {/* Ссылка на видео */}
        <div className="platform-modal-video-link" onClick={handleVideoClick}>
          <IconPlay />
          <span>Смотреть <a href={data.videoUrl} target="_blank" rel="noopener noreferrer" onClick={(e) => e.stopPropagation()}>видео</a>-инструкцию</span>
          <IconExternalLink />
        </div>

        {/* Шаги инструкции */}
        <div className="platform-modal-steps">
          {data.instructions.map((step, index) => (
            <div key={index} className="platform-modal-step">
              <span className="platform-modal-step-num" style={{ background: data.gradient }}>
                {index + 1}
              </span>
              <div className="platform-modal-step-content">
                <strong>{step.title}</strong>
                <p>{step.description}</p>
                {step.link && (
                  <a 
                    href={step.link} 
                    target="_blank" 
                    rel="noopener noreferrer"
                    className="platform-modal-step-link"
                  >
                    {step.linkText} <IconExternalLink />
                  </a>
                )}
              </div>
            </div>
          ))}
        </div>

        {/* Подсказки */}
        <div className="platform-modal-tips">
          <p className="platform-modal-tips-title">Полезная информация:</p>
          <ul>
            {data.tips.map((tip, index) => (
              <li key={index}>{tip}</li>
            ))}
          </ul>
        </div>

        {/* Кнопки */}
        <div className="platform-modal-footer">
          <Button variant="secondary" onClick={onClose}>
            Закрыть
          </Button>
          <Button 
            variant="primary" 
            onClick={onConnect}
            disabled={isConnecting}
            style={{ background: data.gradient }}
          >
            {isConnecting ? 'Подключение...' : `Подключить ${data.name}`}
          </Button>
        </div>
      </div>
    </div>
  );
};

export default PlatformInstructionModal;
