import React, { useState } from 'react';
import { joinIndividualByCode } from '../apiService';
import '../styles/JoinModal.css';

const JoinIndividualModal = ({ onClose, onSuccess }) => {
  const [inviteCode, setInviteCode] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState(false);
  const [joinedTeacher, setJoinedTeacher] = useState(null);

  const handleCodeChange = (e) => {
    const value = e.target.value.toUpperCase().slice(0, 8);
    setInviteCode(value);
    setError('');
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    
    if (inviteCode.length !== 8) {
      setError('Код должен состоять из 8 символов');
      return;
    }

    setLoading(true);
    try {
      const response = await joinIndividualByCode(inviteCode);
      
      if (response && response.teacher) {
        setJoinedTeacher(response.teacher);
        setSuccess(true);
        setTimeout(() => {
          if (onSuccess) onSuccess();
          onClose();
        }, 2000);
      }
    } catch (err) {
      console.error('Failed to join:', err);
      const errorMsg = err.response?.data?.error || 'Ошибка при присоединении';
      setError(errorMsg);
    } finally {
      setLoading(false);
    }
  };

  if (success) {
    return (
      <div className="modal-overlay" onClick={onClose}>
        <div className="join-modal success" onClick={(e) => e.stopPropagation()}>
          <div className="success-icon">✓</div>
          <h2>Вы присоединились!</h2>
          <p>Предметы преподавателя <strong>{joinedTeacher?.first_name} {joinedTeacher?.last_name}</strong> добавлены в ваш профиль</p>
          <p className="secondary-text">Перенаправление...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="join-modal" onClick={(e) => e.stopPropagation()}>
        <button className="modal-close" onClick={onClose}>×</button>
        
        <h2>Присоединиться по коду</h2>
        <p className="modal-subtitle">Введите 8-символьный код от преподавателя</p>
        
        <form onSubmit={handleSubmit}>
          <div className="form-group">
            <label htmlFor="invite-code">Код приглашения</label>
            <input
              id="invite-code"
              type="text"
              maxLength="8"
              placeholder="XXXXXXXX"
              value={inviteCode}
              onChange={handleCodeChange}
              disabled={loading}
              autoFocus
              className={error ? 'input-error' : ''}
            />
            {error && <p className="error-text">{error}</p>}
            <p className="hint-text">Коды состоят из букв и цифр</p>
          </div>

          <div className="form-actions">
            <button
              type="button"
              className="btn-secondary"
              onClick={onClose}
              disabled={loading}
            >
              Отмена
            </button>
            <button
              type="submit"
              className="btn-primary"
              disabled={loading || inviteCode.length !== 8}
            >
              {loading ? 'Присоединение...' : 'Присоединиться'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};

export default JoinIndividualModal;
