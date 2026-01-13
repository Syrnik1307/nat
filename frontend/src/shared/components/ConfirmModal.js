import React from 'react';
import Modal from './Modal';
import Button from './Button';

const ConfirmModal = ({ 
  isOpen, 
  onClose, 
  onConfirm, 
  title = 'Подтверждение',
  message,
  confirmText = 'Подтвердить',
  cancelText = 'Отмена',
  variant = 'warning'
}) => {
  const handleConfirm = () => {
    onConfirm();
    onClose();
  };

  const confirmVariant = variant === 'danger' ? 'danger' : 'primary';

  return (
    <Modal
      isOpen={isOpen}
      onClose={onClose}
      title={title}
      size="small"
      closeOnBackdrop
      footer={(
        <>
          <Button variant="secondary" onClick={onClose}>
            {cancelText}
          </Button>
          <Button variant={confirmVariant} onClick={handleConfirm}>
            {confirmText}
          </Button>
        </>
      )}
    >
      {message ? (
        <p style={{ margin: 0, color: 'var(--text-secondary)', lineHeight: 'var(--leading-relaxed)' }}>
          {message}
        </p>
      ) : null}
    </Modal>
  );
};

export default ConfirmModal;
