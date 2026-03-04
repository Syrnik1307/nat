import React, { useState, useEffect, useRef } from 'react';
import { createPortal } from 'react-dom';
import { useNavigate, useLocation } from 'react-router-dom';
import { useAuth } from '../auth';
import { featureFlags } from '../config/featureFlags';
import { supportApi } from '../apiService';
import './SupportWidget.css';

const POLL_INTERVAL = 60_000; // 60 секунд

/**
 * SupportWidget v2 — плавающая кнопка (FAB) с редиректом на /support.
 *
 * Когда supportV2 включён:
 *   - Клик → navigate('/support') (или /admin/support для админов)
 *   - Поллинг непрочитанных → бейдж на FAB
 *
 * Когда supportV2 выключен → виджет вообще не рендерится (fallback на старый TG-флоу
 * через SupportWidget.css .support-fab скрыт — но мы не удаляем компонент, чтобы
 * родителям не менять импорты).
 */
const SupportWidget = () => {
  const { accessTokenValid, role } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const [unreadCount, setUnreadCount] = useState(0);
  const timerRef = useRef(null);

  // Не показываем FAB, если supportV2 выключен
  if (!featureFlags.supportV2) return null;

  // Скрываем FAB на самих страницах поддержки — навигация уже там
  const onSupportPage = location.pathname.startsWith('/support') || location.pathname.startsWith('/admin/support');

  // Поллинг непрочитанных
  // eslint-disable-next-line react-hooks/rules-of-hooks
  useEffect(() => {
    if (!accessTokenValid) {
      setUnreadCount(0);
      return;
    }

    const fetchUnread = async () => {
      try {
        const res = await supportApi.getUnreadCount();
        setUnreadCount(res.data?.unread_count ?? 0);
      } catch {
        // best-effort
      }
    };

    fetchUnread();
    timerRef.current = setInterval(fetchUnread, POLL_INTERVAL);
    return () => clearInterval(timerRef.current);
  }, [accessTokenValid]);

  const handleClick = () => {
    if (role === 'admin') {
      navigate('/admin/support');
    } else {
      navigate('/support');
    }
  };

  if (onSupportPage) return null;

  const ui = (
    <button
      className="support-fab"
      onClick={handleClick}
      title="Поддержка"
      aria-label="Открыть поддержку"
    >
      <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
        <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/>
      </svg>
      {unreadCount > 0 && (
        <span className="support-fab-badge">
          {unreadCount > 9 ? '9+' : unreadCount}
        </span>
      )}
    </button>
  );

  // Рендерим через портал, чтобы fixed-позиционирование не ломалось из-за transform/overflow у контейнеров страниц
  if (typeof document === 'undefined') return null;
  return createPortal(ui, document.body);
};

export default SupportWidget;
