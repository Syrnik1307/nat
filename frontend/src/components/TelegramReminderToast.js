import React, { useState, useEffect, useCallback } from 'react';
import { Link } from 'react-router-dom';
import { getTelegramStatus } from '../apiService';
import './TelegramReminderToast.css';

// Telegram icon (brand)
const IconTelegram = ({ size = 20, className = '' }) => (
  <svg width={size} height={size} viewBox="0 0 24 24" fill="currentColor" className={className}>
    <path d="M11.944 0A12 12 0 0 0 0 12a12 12 0 0 0 12 12 12 12 0 0 0 12-12A12 12 0 0 0 12 0a12 12 0 0 0-.056 0zm4.962 7.224c.1-.002.321.023.465.14a.506.506 0 0 1 .171.325c.016.093.036.306.02.472-.18 1.898-.962 6.502-1.36 8.627-.168.9-.499 1.201-.82 1.23-.696.065-1.225-.46-1.9-.902-1.056-.693-1.653-1.124-2.678-1.8-1.185-.78-.417-1.21.258-1.91.177-.184 3.247-2.977 3.307-3.23.007-.032.014-.15-.056-.212s-.174-.041-.249-.024c-.106.024-1.793 1.14-5.061 3.345-.48.33-.913.49-1.302.48-.428-.008-1.252-.241-1.865-.44-.752-.245-1.349-.374-1.297-.789.027-.216.325-.437.893-.663 3.498-1.524 5.83-2.529 6.998-3.014 3.332-1.386 4.025-1.627 4.476-1.635z"/>
  </svg>
);

// Close icon
const IconX = ({ size = 16 }) => (
  <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <line x1="18" y1="6" x2="6" y2="18"></line>
    <line x1="6" y1="6" x2="18" y2="18"></line>
  </svg>
);

// Bell icon
const IconBell = ({ size = 14 }) => (
  <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <path d="M6 8a6 6 0 0 1 12 0c0 7 3 9 3 9H3s3-2 3-9"/>
    <path d="M10.3 21a1.94 1.94 0 0 0 3.4 0"/>
  </svg>
);

// Shield icon
const IconShield = ({ size = 14 }) => (
  <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/>
  </svg>
);

const STORAGE_KEY = 'tp_telegram_reminder';
const REMIND_LATER_DAYS = 3;

/**
 * Проверяет, нужно ли показывать напоминание
 */
const shouldShowReminder = () => {
  const stored = localStorage.getItem(STORAGE_KEY);
  if (!stored) return true;
  
  try {
    const data = JSON.parse(stored);
    
    // Никогда не показывать
    if (data.dismissed === 'never') return false;
    
    // Напомнить позже - проверяем дату
    if (data.dismissed === 'later' && data.remindAfter) {
      const remindDate = new Date(data.remindAfter);
      return new Date() >= remindDate;
    }
    
    return true;
  } catch {
    return true;
  }
};

/**
 * Сохраняет выбор пользователя
 */
const saveChoice = (choice) => {
  const data = { dismissed: choice };
  
  if (choice === 'later') {
    const remindDate = new Date();
    remindDate.setDate(remindDate.getDate() + REMIND_LATER_DAYS);
    data.remindAfter = remindDate.toISOString();
  }
  
  localStorage.setItem(STORAGE_KEY, JSON.stringify(data));
};

/**
 * Ненавязчивое напоминание о подключении Telegram
 * Отображается как небольшой toast в нижнем правом углу
 */
const TelegramReminderToast = () => {
  const [visible, setVisible] = useState(false);
  const [closing, setClosing] = useState(false);
  const [loading, setLoading] = useState(true);

  const checkAndShow = useCallback(async () => {
    // Сначала проверяем localStorage
    if (!shouldShowReminder()) {
      setLoading(false);
      return;
    }
    
    try {
      const { data } = await getTelegramStatus();
      
      // Если Telegram уже привязан - не показываем
      if (data.telegram_linked) {
        // Очищаем сохранённые настройки, т.к. уже привязан
        localStorage.removeItem(STORAGE_KEY);
        setLoading(false);
        return;
      }
      
      // Показываем с небольшой задержкой для плавности
      setTimeout(() => {
        setVisible(true);
        setLoading(false);
      }, 1500);
    } catch (err) {
      console.error('[TelegramReminder] Failed to check status:', err);
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    checkAndShow();
  }, [checkAndShow]);

  const handleClose = (choice) => {
    setClosing(true);
    saveChoice(choice);
    
    // Ждём завершения анимации
    setTimeout(() => {
      setVisible(false);
      setClosing(false);
    }, 300);
  };

  if (loading || !visible) return null;

  return (
    <div className={`tg-reminder-toast ${closing ? 'closing' : ''}`}>
      <div className="tg-reminder-content">
        <div className="tg-reminder-icon">
          <IconTelegram size={24} />
        </div>
        
        <div className="tg-reminder-body">
          <h4 className="tg-reminder-title">Подключите Telegram</h4>
          <p className="tg-reminder-text">
            Мгновенные уведомления и быстрое восстановление пароля
          </p>
          
          <div className="tg-reminder-benefits">
            <span className="tg-benefit">
              <IconBell size={12} />
              Уведомления
            </span>
            <span className="tg-benefit">
              <IconShield size={12} />
              Безопасность
            </span>
          </div>
        </div>
        
        <button 
          className="tg-reminder-close"
          onClick={() => handleClose('later')}
          title="Напомнить позже"
        >
          <IconX size={14} />
        </button>
      </div>
      
      <div className="tg-reminder-actions">
        <Link to="/profile?tab=security" className="tg-reminder-btn primary">
          Подключить
        </Link>
        <button 
          className="tg-reminder-btn secondary"
          onClick={() => handleClose('later')}
        >
          Позже
        </button>
        <button 
          className="tg-reminder-btn tertiary"
          onClick={() => handleClose('never')}
        >
          Не напоминать
        </button>
      </div>
    </div>
  );
};

export default TelegramReminderToast;
