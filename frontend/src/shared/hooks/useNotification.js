import { useState } from 'react';

const useNotification = () => {
  const [notification, setNotification] = useState({
    isOpen: false,
    type: 'info',
    title: '',
    message: ''
  });

  const [confirm, setConfirm] = useState({
    isOpen: false,
    title: 'Подтверждение',
    message: '',
    onConfirm: null,
    variant: 'warning',
    confirmText: 'Подтвердить',
    cancelText: 'Отмена'
  });

  const showNotification = (type, title, message) => {
    setNotification({ isOpen: true, type, title, message });
  };

  const closeNotification = () => {
    setNotification({ ...notification, isOpen: false });
  };

  const showConfirm = (options) => {
    return new Promise((resolve) => {
      setConfirm({
        isOpen: true,
        title: options.title || 'Подтверждение',
        message: options.message,
        variant: options.variant || 'warning',
        confirmText: options.confirmText || 'Подтвердить',
        cancelText: options.cancelText || 'Отмена',
        onConfirm: () => {
          resolve(true);
          closeConfirm();
        }
      });
    });
  };

  const closeConfirm = () => {
    setConfirm({ ...confirm, isOpen: false });
  };

  const handleConfirmCancel = () => {
    closeConfirm();
  };

  return {
    notification,
    confirm,
    showNotification,
    closeNotification,
    showConfirm,
    closeConfirm: handleConfirmCancel
  };
};

export default useNotification;
