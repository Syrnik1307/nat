import React, { useCallback, useEffect, useRef, useState } from 'react';
import { Link } from 'react-router-dom';
import { getTelegramStatus } from '../apiService';
import './TelegramReminderToast.css';

const STORAGE_KEY = 'tp_telegram_reminder';
const REMIND_LATER_DAYS = 7;
const SHOW_DELAY_MS = 900;

const shouldShowReminder = () => {
  try {
    const stored = localStorage.getItem(STORAGE_KEY);
    if (!stored) return true;
    const data = JSON.parse(stored);
    if (data.dismissed === 'never') return false;
    if (data.dismissed === 'later' && data.remindAfter) {
      return new Date() >= new Date(data.remindAfter);
    }
    return true;
  } catch {
    return true;
  }
};

const saveChoice = (choice) => {
  try {
    const data = { dismissed: choice };
    if (choice === 'later') {
      const remindDate = new Date();
      remindDate.setDate(remindDate.getDate() + REMIND_LATER_DAYS);
      data.remindAfter = remindDate.toISOString();
    }
    localStorage.setItem(STORAGE_KEY, JSON.stringify(data));
  } catch {
    // ignore
  }
};

const TelegramReminderToast = () => {
  const [visible, setVisible] = useState(false);
  const [closing, setClosing] = useState(false);
  const [loading, setLoading] = useState(true);
  const showTimerRef = useRef(null);
  const hideTimerRef = useRef(null);

  const checkAndShow = useCallback(async () => {
    if (!shouldShowReminder()) {
      setLoading(false);
      return;
    }

    try {
      const { data } = await getTelegramStatus();
      if (data.telegram_linked) {
        try { localStorage.removeItem(STORAGE_KEY); } catch { /* ignore */ }
        setLoading(false);
        return;
      }

      showTimerRef.current = setTimeout(() => {
        setVisible(true);
        setLoading(false);
      }, SHOW_DELAY_MS);
    } catch {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    checkAndShow();
    return () => {
      if (showTimerRef.current) clearTimeout(showTimerRef.current);
      if (hideTimerRef.current) clearTimeout(hideTimerRef.current);
    };
  }, [checkAndShow]);

  const close = (choice) => {
    saveChoice(choice);
    setClosing(true);
    hideTimerRef.current = setTimeout(() => {
      setVisible(false);
      setClosing(false);
    }, 200);
  };

  if (loading || !visible) return null;

  return (
    <>
      <div className="tg-hint-spacer" aria-hidden="true" />
      <div className={`tg-hint ${closing ? 'closing' : ''}`} role="region" aria-label="Подсказка Telegram">
        <span className="tg-hint-text">
          Подключите Telegram — напоминания о занятиях и важные события будут приходить сразу.
        </span>
        <Link to="/profile?tab=security" className="tg-hint-link">
          Подключить
        </Link>
        <button type="button" className="tg-hint-later" onClick={() => close('later')}>
          Позже
        </button>
        <button type="button" className="tg-hint-never" onClick={() => close('never')}>
          Не напоминать
        </button>
        <button type="button" className="tg-hint-dismiss" onClick={() => close('later')} aria-label="Закрыть">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <line x1="18" y1="6" x2="6" y2="18" />
            <line x1="6" y1="6" x2="18" y2="18" />
          </svg>
        </button>
      </div>
    </>
  );
};

export default TelegramReminderToast;
