import React, { useState } from 'react';
import { regenerateIndividualInviteCode } from '../apiService';
import ConfirmModal from '../shared/components/ConfirmModal';
import '../styles/InviteModal.css';

const IndividualInviteModal = ({ code, onClose }) => {
  const [inviteCode, setInviteCode] = useState(code?.invite_code || '');
  const [copiedCode, setCopiedCode] = useState(false);
  const [copiedLink, setCopiedLink] = useState(false);
  const [regenerating, setRegenerating] = useState(false);
  const [showConfirm, setShowConfirm] = useState(false);

  const inviteLink = `${window.location.origin}/student?individual-code=${inviteCode}`;

  const handleCopy = async (text, type) => {
    const setCopied = type === 'code' ? setCopiedCode : setCopiedLink;

    try {
      if (navigator.clipboard && navigator.clipboard.writeText) {
        await navigator.clipboard.writeText(text);
        setCopied(true);
        setTimeout(() => setCopied(false), 2000);
        return;
      }
    } catch (error) {
      console.warn('Clipboard API failed, using fallback:', error);
    }

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
        alert('Не удалось скопировать. Пожалуйста, скопируйте вручную:\n' + text);
      }
    } catch (error) {
      console.error('Copy failed:', error);
      alert('Не удалось скопировать');
    }
  };

  const handleRegenerate = async () => {
    setRegenerating(true);
    try {
      const response = await regenerateIndividualInviteCode(code.id);
      const newCode = response?.code?.invite_code || response?.data?.code?.invite_code || response?.data?.invite_code;
      if (newCode) {
        setInviteCode(newCode);
      }
    } catch (error) {
      console.error('Failed to regenerate code:', error);
      alert('Ошибка при регенерации кода');
    } finally {
      setRegenerating(false);
      setShowConfirm(false);
    }
  };

  return (
    <>
      <div className="invite-modal-overlay" onClick={onClose}>
        <div className="invite-modal-content" onClick={(e) => e.stopPropagation()}>
          <button className="invite-modal-close" onClick={onClose}>×</button>

          <h2>Пригласить ученика</h2>
          <p className="invite-modal-subtitle">Предмет: <strong>{code?.subject}</strong></p>

          <div className="invite-section">
            <h3>Код приглашения</h3>
            <div className="invite-code-display">
              <span className="invite-code-text">{inviteCode}</span>
              <button
                className="invite-copy-btn"
                onClick={() => handleCopy(inviteCode, 'code')}
                title="Скопировать код"
              >
                {copiedCode ? '✓ Скопировано' : '📋 Скопировать'}
              </button>
            </div>
            <p className="invite-hint">Ученик вводит этот код в поле приглашения</p>
          </div>

          <div className="invite-section">
            <h3>Ссылка приглашения</h3>
            <div className="invite-link-display">
              <input
                type="text"
                readOnly
                value={inviteLink}
                className="invite-link-input"
              />
              <button
                className="invite-copy-btn"
                onClick={() => handleCopy(inviteLink, 'link')}
                title="Скопировать ссылку"
              >
                {copiedLink ? '✓ Скопировано' : '📋 Скопировать'}
              </button>
            </div>
            <p className="invite-hint">Ученик переходит по ссылке и автоматически присоединяется</p>
          </div>

          <div className="invite-actions">
            <button
              className="invite-regenerate-btn"
              onClick={() => setShowConfirm(true)}
              disabled={regenerating}
            >
              🔄 Сгенерировать новый код
            </button>
            <button className="invite-done-btn" onClick={onClose}>
              Закрыть
            </button>
          </div>
        </div>
      </div>

      {showConfirm && (
        <ConfirmModal
          title="Сгенерировать новый код?"
          message="Текущий код перестанет действовать. Ученик не сможет использовать старый код."
          onConfirm={handleRegenerate}
          onCancel={() => setShowConfirm(false)}
          confirmText="Сгенерировать"
          cancelText="Отмена"
          isLoading={regenerating}
        />
      )}
    </>
  );
};

export default IndividualInviteModal;
