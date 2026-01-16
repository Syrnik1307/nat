import React, { useState } from 'react';
import { Button, Input } from '../shared/components';
import './PlatformInstructionModal.css';

/**
 * Модальное окно с инструкцией по подключению Zoom или Google Meet
 * Каждый учитель создаёт свой проект и вводит свои credentials
 */

const IconClose = () => (
  <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
    <line x1="18" y1="6" x2="6" y2="18"/>
    <line x1="6" y1="6" x2="18" y2="18"/>
  </svg>
);

const IconExternalLink = () => (
  <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
    <path d="M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6"/>
    <polyline points="15,3 21,3 21,9"/>
    <line x1="10" y1="14" x2="21" y2="3"/>
  </svg>
);

const IconCheck = () => (
  <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="3">
    <polyline points="20 6 9 17 4 12"/>
  </svg>
);

const IconCopy = () => (
  <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
    <rect x="9" y="9" width="13" height="13" rx="2" ry="2"/>
    <path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"/>
  </svg>
);

const IconLock = () => (
  <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
    <rect x="3" y="11" width="18" height="11" rx="2" ry="2"/>
    <path d="M7 11V7a5 5 0 0 1 10 0v4"/>
  </svg>
);

// Данные платформ с подробными инструкциями
const PLATFORM_DATA = {
  zoom: {
    name: 'Zoom',
    color: '#2D8CFF',
    gradient: 'linear-gradient(135deg, #2D8CFF 0%, #0B5CFF 100%)',
    lightBg: '#EBF5FF',
    icon: (
      <svg viewBox="0 0 24 24" fill="currentColor" width="28" height="28">
        <path d="M4.585 11.828V16a2 2 0 002 2h7.829a2 2 0 002-2v-4.172a2 2 0 00-2-2H6.585a2 2 0 00-2 2zm13.243 4.415l2.829 2.122a.75.75 0 001.193-.607V10.071a.75.75 0 00-1.193-.607l-2.829 2.122v4.657z"/>
      </svg>
    ),
    requiresCredentials: true,
    credentialFields: [
      { id: 'accountId', label: 'Account ID', placeholder: 'xxxxxxxxx', type: 'text' },
      { id: 'clientId', label: 'Client ID', placeholder: 'xxxxxxxxx', type: 'text' },
      { id: 'clientSecret', label: 'Client Secret', placeholder: 'xxxxxxxxx', type: 'password' }
    ],
    validateCredentials: (creds) => {
      if (!creds.accountId?.trim()) return 'Введите Account ID';
      if (!creds.clientId?.trim()) return 'Введите Client ID';
      if (!creds.clientSecret?.trim()) return 'Введите Client Secret';
      return null;
    },
    instructions: [
      {
        title: 'Создайте приложение в Zoom Marketplace',
        description: 'Войдите и создайте Server-to-Server OAuth приложение',
        link: 'https://marketplace.zoom.us/develop/create',
        linkText: 'Открыть Zoom Marketplace',
        substeps: [
          'Нажмите "Develop" в правом верхнем углу',
          'Выберите "Build App"',
          'Найдите "Server-to-Server OAuth" и нажмите "Create"',
          'Введите название приложения (например "Lectio")',
          'Нажмите "Create"'
        ]
      },
      {
        title: 'Скопируйте учётные данные',
        description: 'На странице "App Credentials" найдите три значения',
        substeps: [
          'Account ID - длинная строка сверху',
          'Client ID - идентификатор клиента',
          'Client Secret - нажмите "Show" чтобы увидеть'
        ]
      },
      {
        title: 'Добавьте разрешения (Scopes)',
        description: 'Перейдите на вкладку "Scopes"',
        substeps: [
          'Нажмите "+ Add Scopes"',
          'В поиске введите "meeting"',
          'Добавьте: meeting:write:admin',
          'В поиске введите "user"',
          'Добавьте: user:read:admin',
          'Нажмите "Done"'
        ]
      },
      {
        title: 'Активируйте приложение',
        description: 'Перейдите на вкладку "Activation"',
        substeps: [
          'Нажмите "Activate your app"',
          'Статус изменится на "Activated"'
        ]
      },
      {
        title: 'Введите данные ниже',
        description: 'Вставьте скопированные учётные данные',
        isCredentialsStep: true
      }
    ],
    benefits: [
      'Ученики без регистрации',
      'Автозапись уроков',
      'Стабильное качество'
    ]
  },
  google_meet: {
    name: 'Google Meet',
    color: '#00897B',
    gradient: 'linear-gradient(135deg, #00897B 0%, #00695C 100%)',
    lightBg: '#E0F2F1',
    icon: (
      <svg viewBox="0 0 24 24" width="28" height="28">
        <path fill="#00832d" d="M12 14.5l6-4.5v9H6v-9z"/>
        <path fill="#0066da" d="M6 10l6 4.5V19H6z"/>
        <path fill="#e94235" d="M12 5l6 4.5L12 14V5z"/>
        <path fill="#2684fc" d="M6 10l6 4V5L6 9.5z"/>
        <path fill="#00ac47" d="M18 10l-6 4.5V19l6-4.5z"/>
        <path fill="#ffba00" d="M18 5v4.5l-6 4.5V5h6z"/>
      </svg>
    ),
    requiresCredentials: true,
    credentialFields: [
      { id: 'clientId', label: 'Client ID', placeholder: 'xxxxx.apps.googleusercontent.com', type: 'text' },
      { id: 'clientSecret', label: 'Client Secret', placeholder: 'GOCSPX-xxxxxxxxx', type: 'password' }
    ],
    validateCredentials: (creds) => {
      if (!creds.clientId?.trim()) return 'Введите Client ID';
      if (!creds.clientId.endsWith('.apps.googleusercontent.com')) {
        return 'Client ID должен заканчиваться на .apps.googleusercontent.com';
      }
      if (!creds.clientSecret?.trim()) return 'Введите Client Secret';
      return null;
    },
    instructions: [
      {
        title: 'Создайте проект в Google Cloud',
        description: 'Откройте консоль и создайте новый проект',
        link: 'https://console.cloud.google.com/projectcreate',
        linkText: 'Открыть Google Cloud Console',
        substeps: [
          'Введите название проекта (например "Lectio")',
          'Нажмите "Create"',
          'Дождитесь создания проекта (10-20 сек)'
        ]
      },
      {
        title: 'Включите Google Calendar API',
        description: 'API необходим для создания встреч Meet',
        link: 'https://console.cloud.google.com/apis/library/calendar-json.googleapis.com',
        linkText: 'Открыть Calendar API',
        substeps: [
          'Убедитесь что выбран ваш проект в шапке',
          'Нажмите большую синюю кнопку "Enable"'
        ]
      },
      {
        title: 'Настройте OAuth Consent Screen',
        description: 'Создайте экран согласия для авторизации',
        link: 'https://console.cloud.google.com/apis/credentials/consent',
        linkText: 'Настроить Consent Screen',
        substeps: [
          'Выберите "External" и нажмите "Create"',
          'App name: введите "Lectio"',
          'User support email: выберите ваш email',
          'Developer contact: введите ваш email',
          'Нажмите "Save and Continue"',
          'Пропустите Scopes - нажмите "Save and Continue"',
          'На Test Users нажмите "Add Users"',
          'Введите ваш Google email',
          'Нажмите "Save and Continue"'
        ]
      },
      {
        title: 'Создайте OAuth Client ID',
        description: 'Получите учётные данные для интеграции',
        link: 'https://console.cloud.google.com/apis/credentials',
        linkText: 'Создать Credentials',
        substeps: [
          'Нажмите "+ Create Credentials"',
          'Выберите "OAuth client ID"',
          'Application type: "Web application"',
          'Name: "Lectio Web"',
          'В "Authorized redirect URIs" нажмите "+ Add URI"',
          'Вставьте URI из поля ниже',
          'Нажмите "Create"',
          'Скопируйте Client ID и Client Secret из окна'
        ],
        copyValue: 'https://lectio.tw1.ru/api/integrations/google-meet/callback/'
      },
      {
        title: 'Введите данные ниже',
        description: 'Вставьте Client ID и Client Secret',
        isCredentialsStep: true
      }
    ],
    benefits: [
      'Бесплатный сервис',
      'Google Calendar',
      'Надёжная работа'
    ]
  }
};

// Компонент одного шага
const InstructionStep = ({ step, index, platformColor, platformGradient }) => {
  const [copied, setCopied] = useState(false);
  const [expanded, setExpanded] = useState(false);

  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(step.copyValue);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch (err) {
      console.error('Copy failed:', err);
    }
  };

  return (
    <div className="instruction-step">
      <div className="instruction-step-marker" style={{ background: platformGradient }}>
        {index + 1}
      </div>
      <div className="instruction-step-body">
        <div className="instruction-step-header">
          <h4>{step.title}</h4>
          {step.link && (
            <a 
              href={step.link} 
              target="_blank" 
              rel="noopener noreferrer"
              className="instruction-step-link"
              style={{ color: platformColor }}
            >
              {step.linkText} <IconExternalLink />
            </a>
          )}
        </div>
        <p className="instruction-step-desc">{step.description}</p>
        
        {step.substeps && step.substeps.length > 0 && (
          <>
            <button 
              type="button" 
              className="substeps-toggle"
              onClick={() => setExpanded(!expanded)}
            >
              {expanded ? 'Скрыть подробности' : 'Показать подробности'}
            </button>
            {expanded && (
              <ul className="instruction-substeps">
                {step.substeps.map((substep, idx) => (
                  <li key={idx}>{substep}</li>
                ))}
              </ul>
            )}
          </>
        )}
        
        {step.copyValue && (
          <div className="copy-uri-box">
            <code>{step.copyValue}</code>
            <button 
              type="button" 
              className={`copy-uri-btn ${copied ? 'copied' : ''}`}
              onClick={handleCopy}
            >
              {copied ? <><IconCheck /> Скопировано</> : <><IconCopy /> Копировать</>}
            </button>
          </div>
        )}
      </div>
    </div>
  );
};

// Форма ввода credentials
const CredentialsForm = ({ fields, values, onChange, error }) => {
  return (
    <div className="credentials-form-modern">
      {fields.map((field) => (
        <div key={field.id} className="credentials-input-group">
          <label htmlFor={field.id}>{field.label}</label>
          <div className="credentials-input-wrapper">
            <Input
              id={field.id}
              type={field.type}
              value={values[field.id] || ''}
              onChange={(e) => onChange(field.id, e.target.value)}
              placeholder={field.placeholder}
            />
            {field.type === 'password' && (
              <span className="input-icon-right"><IconLock /></span>
            )}
          </div>
        </div>
      ))}
      {error && <p className="credentials-error-msg">{error}</p>}
    </div>
  );
};

const PlatformInstructionModal = ({ 
  platform,
  isOpen, 
  onClose, 
  onConnect,
  isConnecting = false
}) => {
  const [credentials, setCredentials] = useState({});
  const [error, setError] = useState('');

  if (!isOpen || !platform) return null;

  const data = PLATFORM_DATA[platform];
  if (!data) return null;

  const handleBackdropClick = (e) => {
    if (e.target === e.currentTarget) {
      onClose();
    }
  };

  const handleCredentialChange = (field, value) => {
    setCredentials(prev => ({ ...prev, [field]: value }));
    setError('');
  };

  const handleConnect = () => {
    if (data.requiresCredentials && data.validateCredentials) {
      const validationError = data.validateCredentials(credentials);
      if (validationError) {
        setError(validationError);
        return;
      }
    }
    setError('');
    
    if (platform === 'google_meet') {
      onConnect({ 
        clientId: credentials.clientId?.trim(), 
        clientSecret: credentials.clientSecret?.trim() 
      });
    } else if (platform === 'zoom') {
      onConnect({
        accountId: credentials.accountId?.trim(),
        clientId: credentials.clientId?.trim(),
        clientSecret: credentials.clientSecret?.trim()
      });
    } else {
      onConnect();
    }
  };

  const isValid = !data.requiresCredentials || 
    (data.validateCredentials && !data.validateCredentials(credentials));

  return (
    <div className="platform-modal-overlay" onClick={handleBackdropClick}>
      <div className="platform-modal-modern">
        {/* Закрыть */}
        <button className="modal-close-btn" onClick={onClose} type="button">
          <IconClose />
        </button>

        {/* Заголовок */}
        <header className="modal-header-modern" style={{ '--accent': data.color, '--accent-bg': data.lightBg }}>
          <div className="modal-platform-badge" style={{ background: data.gradient }}>
            {data.icon}
          </div>
          <div>
            <h2>Подключение {data.name}</h2>
            <p>Создайте своё приложение для интеграции</p>
          </div>
        </header>

        {/* Шаги инструкции */}
        <div className="modal-instructions-list">
          {data.instructions.map((step, index) => (
            step.isCredentialsStep ? (
              <div key={index} className="instruction-step credentials-step-container">
                <div className="instruction-step-marker" style={{ background: data.gradient }}>
                  {index + 1}
                </div>
                <div className="instruction-step-body">
                  <h4>{step.title}</h4>
                  <p className="instruction-step-desc">{step.description}</p>
                  <CredentialsForm
                    fields={data.credentialFields}
                    values={credentials}
                    onChange={handleCredentialChange}
                    error={error}
                  />
                </div>
              </div>
            ) : (
              <InstructionStep
                key={index}
                step={step}
                index={index}
                platformColor={data.color}
                platformGradient={data.gradient}
              />
            )
          ))}
        </div>

        {/* Преимущества */}
        <div className="modal-benefits" style={{ background: data.lightBg }}>
          <span className="benefits-label">Преимущества:</span>
          <div className="benefits-list">
            {data.benefits.map((benefit, idx) => (
              <span key={idx} className="benefit-tag" style={{ color: data.color }}>
                <IconCheck /> {benefit}
              </span>
            ))}
          </div>
        </div>

        {/* Действия */}
        <footer className="modal-footer-modern">
          <Button variant="secondary" onClick={onClose}>
            Отмена
          </Button>
          <Button 
            variant="primary" 
            onClick={handleConnect}
            disabled={isConnecting || !isValid}
            style={{ background: isValid ? data.gradient : undefined }}
          >
            {isConnecting ? 'Подключение...' : 'Подключить'}
          </Button>
        </footer>
      </div>
    </div>
  );
};

export default PlatformInstructionModal;
