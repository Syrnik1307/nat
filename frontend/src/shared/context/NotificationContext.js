import React, { createContext, useContext, useState, useCallback, useRef } from 'react';
import ConfirmModal from '../components/ConfirmModal';
import Toast from '../components/Toast';
import '../components/Toast.css';

const NotificationContext = createContext(null);

/**
 * Провайдер глобальных уведомлений и подтверждений
 * Заменяет window.alert() и window.confirm() на красивые модалки
 */
export const NotificationProvider = ({ children }) => {
  // Toast уведомления
  const [toasts, setToasts] = useState([]);
  const toastIdCounter = useRef(0);
  
  // Confirm модалка
  const [confirmState, setConfirmState] = useState({
    isOpen: false,
    title: '',
    message: '',
    variant: 'warning',
    confirmText: 'Подтвердить',
    cancelText: 'Отмена',
  });
  const confirmResolver = useRef(null);

  // Показать toast уведомление (замена alert)
  const showToast = useCallback((type, title, message, duration = 4000) => {
    const id = ++toastIdCounter.current;
    setToasts(prev => [...prev, { id, type, title, message, duration }]);
  }, []);

  // Удалить toast
  const removeToast = useCallback((id) => {
    setToasts(prev => prev.filter(t => t.id !== id));
  }, []);

  // Shortcut методы для разных типов
  const toast = {
    success: (message, title = 'Успешно') => showToast('success', title, message),
    error: (message, title = 'Ошибка') => showToast('error', title, message),
    warning: (message, title = 'Внимание') => showToast('warning', title, message),
    info: (message, title = 'Информация') => showToast('info', title, message),
  };

  // Показать confirm диалог (замена window.confirm)
  const showConfirm = useCallback((options) => {
    return new Promise((resolve) => {
      confirmResolver.current = resolve;
      setConfirmState({
        isOpen: true,
        title: options.title || 'Подтверждение',
        message: options.message || '',
        variant: options.variant || 'warning',
        confirmText: options.confirmText || 'Подтвердить',
        cancelText: options.cancelText || 'Отмена',
      });
    });
  }, []);

  const handleConfirm = useCallback(() => {
    if (confirmResolver.current) {
      confirmResolver.current(true);
      confirmResolver.current = null;
    }
    setConfirmState(prev => ({ ...prev, isOpen: false }));
  }, []);

  const handleCancel = useCallback(() => {
    if (confirmResolver.current) {
      confirmResolver.current(false);
      confirmResolver.current = null;
    }
    setConfirmState(prev => ({ ...prev, isOpen: false }));
  }, []);

  const value = {
    toast,
    showConfirm,
  };

  return (
    <NotificationContext.Provider value={value}>
      {children}
      
      {/* Toast container */}
      <div className="toast-container">
        {toasts.map((t) => (
          <Toast
            key={t.id}
            isOpen={true}
            type={t.type}
            title={t.title}
            message={t.message}
            duration={t.duration}
            onClose={() => removeToast(t.id)}
          />
        ))}
      </div>
      
      {/* Confirm modal */}
      <ConfirmModal
        isOpen={confirmState.isOpen}
        onClose={handleCancel}
        onConfirm={handleConfirm}
        title={confirmState.title}
        message={confirmState.message}
        variant={confirmState.variant}
        confirmText={confirmState.confirmText}
        cancelText={confirmState.cancelText}
      />
    </NotificationContext.Provider>
  );
};

/**
 * Хук для использования глобальных уведомлений
 * 
 * @example
 * const { toast, showConfirm } = useNotifications();
 * 
 * // Вместо alert('Ошибка')
 * toast.error('Что-то пошло не так');
 * 
 * // Вместо window.confirm('Удалить?')
 * const confirmed = await showConfirm({ 
 *   title: 'Удаление', 
 *   message: 'Вы уверены?',
 *   variant: 'danger'
 * });
 * if (confirmed) { ... }
 */
export const useNotifications = () => {
  const context = useContext(NotificationContext);
  if (!context) {
    throw new Error('useNotifications must be used within NotificationProvider');
  }
  return context;
};

export default NotificationContext;
