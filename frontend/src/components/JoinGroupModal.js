import React, { useState } from 'react';
import { joinGroupByCode } from '../apiService';
import '../styles/JoinGroupModal.css';

const JoinGroupModal = ({ onClose, onSuccess }) => {
  const [inviteCode, setInviteCode] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');

  const handleSubmit = async (e) => {
    e.preventDefault();
    
    if (!inviteCode.trim()) {
      setError('Введите код приглашения');
      return;
    }

    setLoading(true);
    setError('');
    setSuccess('');

    try {
      const response = await joinGroupByCode(inviteCode.trim().toUpperCase());
      setSuccess(response.data.message || 'Вы успешно присоединились к группе!');
      
      setTimeout(() => {
        if (onSuccess) onSuccess(response.data.group);
        onClose();
      }, 1500);
    } catch (err) {
      const errorMsg = err.response?.data?.error || 'Не удалось присоединиться к группе';
      setError(errorMsg);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="join-modal-overlay" onClick={onClose}>
      <div className="join-modal-content" onClick={(e) => e.stopPropagation()}>
        <button className="join-modal-close" onClick={onClose}>×</button>
        
        <div className="join-modal-icon">🎓</div>
        <h2>Присоединиться к группе</h2>
        <p className="join-modal-subtitle">Введите код приглашения от преподавателя</p>

        <form onSubmit={handleSubmit}>
          <div className="join-input-group">
            <input
              type="text"
              className="join-code-input"
              placeholder="Например: ABC12345"
              value={inviteCode}
              onChange={(e) => setInviteCode(e.target.value.toUpperCase())}
              maxLength={8}
              autoFocus
            />
          </div>

          {error && (
            <div className="join-error-message">
              ⚠️ {error}
            </div>
          )}

          {success && (
            <div className="join-success-message">
              ✓ {success}
            </div>
          )}

          <div className="join-actions">
            <button 
              type="button" 
              className="join-cancel-btn" 
              onClick={onClose}
              disabled={loading}
            >
              Отмена
            </button>
            <button 
              type="submit" 
              className="join-submit-btn"
              disabled={loading || !inviteCode.trim()}
            >
              {loading ? 'Присоединение...' : 'Присоединиться'}
            </button>
          </div>
        </form>

        <div className="join-help-text">
          <p>💡 Код приглашения состоит из 8 символов</p>
          <p>Вы можете получить его от преподавателя или отсканировать QR-код</p>
        </div>
      </div>
    </div>
  );
};

export default JoinGroupModal;
