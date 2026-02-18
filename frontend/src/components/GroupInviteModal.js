import React, { useState } from 'react';
import { regenerateGroupInviteCode } from '../apiService';
import { useNotifications } from '../shared/context/NotificationContext';
import Modal from '../shared/components/Modal';
import ConfirmModal from '../shared/components/ConfirmModal';
import '../styles/InviteModal.css';

const GroupInviteModal = ({ group, onClose }) => {
  const { toast } = useNotifications();
  const [inviteCode, setInviteCode] = useState(group?.invite_code || '');
  const [copiedCode, setCopiedCode] = useState(false);
  const [copiedLink, setCopiedLink] = useState(false);
  const [regenerating, setRegenerating] = useState(false);
  const [showConfirm, setShowConfirm] = useState(false);

  const inviteLink = `${window.location.origin}/student?code=${inviteCode}`;

  const handleCopy = async (text, type) => {
    const setCopied = type === 'code' ? setCopiedCode : setCopiedLink;
    
    try {
      // Попытка использовать Clipboard API
      if (navigator.clipboard && navigator.clipboard.writeText) {
        await navigator.clipboard.writeText(text);
        setCopied(true);
        setTimeout(() => setCopied(false), 2000);
        return;
      }
    } catch (error) {
      console.warn('Clipboard API failed, using fallback:', error);
    }
    
    // Fallback для HTTP или старых браузеров
    try {
      const textArea = document.createElement('textarea');
      textArea.value = text;
      textArea.style.position = 'fixed';
      textArea.style.top = '0';
      textArea.style.left = '0';
      textArea.style.opacity = '0';
      document.body.appendChild(textArea);
      textArea.focus();
      textArea.select();
      
      const successful = document.execCommand('copy');
      document.body.removeChild(textArea);
      
      if (successful) {
        setCopied(true);
        setTimeout(() => setCopied(false), 2000);
      } else {
        toast.warning('Скопируйте вручную: ' + text);
      }
    } catch (err) {
      console.error('Fallback copy failed:', err);
      toast.warning('Скопируйте вручную: ' + text);
    }
  };

  const handleRegenerateClick = () => {
    setShowConfirm(true);
  };

  const handleConfirmRegenerate = async () => {
    setRegenerating(true);
    try {
      const response = await regenerateGroupInviteCode(group.id);
      setInviteCode(response.data.invite_code);
    } catch (error) {
      console.error('Error regenerating code:', error);
      toast.error('Ошибка при генерации нового кода');
    } finally {
      setRegenerating(false);
    }
  };

  const footer = (
    <div className="invite-actions" style={{ marginTop: 0, paddingTop: 0, borderTop: 'none' }}>
      <button
        className="invite-regenerate-btn"
        onClick={handleRegenerateClick}
        disabled={regenerating}
      >
        {regenerating ? 'Генерация...' : 'Создать новый код'}
      </button>
      <button className="invite-done-btn" onClick={onClose}>
        Готово
      </button>
    </div>
  );

  return (
    <>
      <Modal
        isOpen={true}
        onClose={onClose}
        title="Пригласить учеников"
        size="medium"
        footer={footer}
      >
        <p className="invite-modal-subtitle">Группа: {group?.name}</p>

        <div className="invite-section">
          <h3>Код приглашения</h3>
          <div className="invite-code-display">
            <span className="invite-code-text">{inviteCode}</span>
            <button
              className="invite-copy-btn"
              onClick={() => handleCopy(inviteCode, 'code')}
            >
              {copiedCode ? 'Скопировано' : 'Копировать'}
            </button>
          </div>
          <p className="invite-hint">Ученики могут ввести этот код на странице "Мои курсы"</p>
        </div>

        <div className="invite-section">
          <h3>Ссылка-приглашение</h3>
          <div className="invite-link-display">
            <input
              type="text"
              value={inviteLink}
              readOnly
              className="invite-link-input"
            />
            <button
              className="invite-copy-btn"
              onClick={() => handleCopy(inviteLink, 'link')}
            >
              {copiedLink ? 'Скопировано' : 'Копировать'}
            </button>
          </div>
        </div>

        <div className="invite-section" style={{ marginBottom: 0 }}>
          <h3>QR-код</h3>
          <div className="invite-qr-placeholder">
            <img
              src={`https://api.qrserver.com/v1/create-qr-code/?size=200x200&data=${encodeURIComponent(inviteLink)}`}
              alt="QR Code"
              className="invite-qr-image"
            />
          </div>
          <p className="invite-hint">Покажите QR-код на экране, ученики отсканируют его</p>
        </div>
      </Modal>

      <ConfirmModal
        isOpen={showConfirm}
        onClose={() => setShowConfirm(false)}
        onConfirm={handleConfirmRegenerate}
        title="Создать новый код?"
        message="Старый код приглашения перестанет работать. Все ученики, у которых был старый код, больше не смогут присоединиться к группе."
        confirmText="Создать новый"
        cancelText="Отмена"
        variant="warning"
      />
    </>
  );
};

export default GroupInviteModal;
