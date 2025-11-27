import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { Modal, Button } from '../shared/components';
import './GroupChatModal.css';

/**
 * Модальное окно создания группового чата (только для преподавателей)
 * Преподаватель выбирает группу и участников
 */
const GroupChatModal = ({ isOpen, onClose, onSuccess }) => {
  const [mode, setMode] = useState('group'); // 'group' или 'custom'
  const [groups, setGroups] = useState([]);
  const [allUsers, setAllUsers] = useState([]);
  const [selectedGroup, setSelectedGroup] = useState(null);
  const [groupStudents, setGroupStudents] = useState([]);
  const [selectedStudents, setSelectedStudents] = useState([]);
  const [chatName, setChatName] = useState('');
  const [loading, setLoading] = useState(false);
  const [creating, setCreating] = useState(false);
  const [searchQuery, setSearchQuery] = useState('');

  useEffect(() => {
    if (isOpen) {
      loadGroups();
      loadAllUsers();
    }
  }, [isOpen]);

  useEffect(() => {
    if (selectedGroup) {
      loadGroupStudents();
      // Автоматическое название группы
      if (!chatName) {
        setChatName(`Группа ${selectedGroup.name}`);
      }
    }
  }, [selectedGroup]);

  const loadGroups = async () => {
    setLoading(true);
    try {
      const token = localStorage.getItem('access_token');
      const response = await axios.get('/api/groups/', {
        headers: { Authorization: `Bearer ${token}` }
      });
      setGroups(response.data);
    } catch (error) {
      console.error('Ошибка загрузки групп:', error);
    } finally {
      setLoading(false);
    }
  };

  const loadAllUsers = async () => {
    setLoading(true);
    try {
      const token = localStorage.getItem('access_token');
      const response = await axios.get('/api/users/', {
        headers: { Authorization: `Bearer ${token}` }
      });
      // Фильтруем текущего пользователя
      const currentUserId = JSON.parse(localStorage.getItem('user'))?.id;
      const users = response.data.filter(u => u.id !== currentUserId);
      setAllUsers(users);
    } catch (error) {
      console.error('Ошибка загрузки пользователей:', error);
    } finally {
      setLoading(false);
    }
  };

  const loadGroupStudents = async () => {
    if (!selectedGroup?.id) return;
    
    setLoading(true);
    try {
      const token = localStorage.getItem('access_token');
      const response = await axios.get(
        `/api/groups/${selectedGroup.id}/students/`,
        { headers: { Authorization: `Bearer ${token}` } }
      );
      setGroupStudents(response.data);
      // Автоматически выбираем всех студентов
      setSelectedStudents(response.data.map(s => s.id));
    } catch (error) {
      console.error('Ошибка загрузки студентов группы:', error);
    } finally {
      setLoading(false);
    }
  };

  const toggleStudent = (studentId) => {
    setSelectedStudents(prev => 
      prev.includes(studentId)
        ? prev.filter(id => id !== studentId)
        : [...prev, studentId]
    );
  };

  const toggleAllStudents = () => {
    const currentList = mode === 'custom' ? filteredUsers : groupStudents;
    if (selectedStudents.length === currentList.length) {
      setSelectedStudents([]);
    } else {
      setSelectedStudents(currentList.map(s => s.id));
    }
  };

  const filteredUsers = allUsers.filter(user =>
    searchQuery.trim() === '' ||
    `${user.first_name} ${user.last_name}`.toLowerCase().includes(searchQuery.toLowerCase()) ||
    user.email?.toLowerCase().includes(searchQuery.toLowerCase()) ||
    user.username_handle?.toLowerCase().includes(searchQuery.toLowerCase())
  );

  const createGroupChat = async () => {
    if (!chatName.trim() || selectedStudents.length === 0 || creating) return;
    
    setCreating(true);
    try {
      const token = localStorage.getItem('access_token');
      const response = await axios.post(
        '/api/chats/create_group/',
        {
          name: chatName,
          participant_ids: selectedStudents,
          group_id: selectedGroup?.id
        },
        { headers: { Authorization: `Bearer ${token}` } }
      );
      
      onSuccess && onSuccess(response.data);
      handleClose();
    } catch (error) {
      console.error('Ошибка создания группового чата:', error);
      alert('Ошибка создания чата. Попробуйте еще раз.');
    } finally {
      setCreating(false);
    }
  };

  const handleClose = () => {
    setMode('group');
    setSelectedGroup(null);
    setGroupStudents([]);
    setAllUsers([]);
    setSelectedStudents([]);
    setChatName('');
    setSearchQuery('');
    onClose();
  };

  return (
    <Modal
      isOpen={isOpen}
      onClose={handleClose}
      title="Создать групповой чат"
      size="large"
    >
      <div className="group-chat-modal">
        {/* Выбор режима */}
        <div className="form-section">
          <div className="mode-tabs">
            <button
              className={`mode-tab ${mode === 'group' ? 'active' : ''}`}
              onClick={() => {
                setMode('group');
                setSelectedStudents([]);
                setChatName('');
              }}
            >
              📚 Из учебной группы
            </button>
            <button
              className={`mode-tab ${mode === 'custom' ? 'active' : ''}`}
              onClick={() => {
                setMode('custom');
                setSelectedGroup(null);
                setSelectedStudents([]);
                setChatName('');
              }}
            >
              ⚙️ Произвольная группа
            </button>
          </div>
        </div>

        {/* Название чата */}
        <div className="form-section">
          <label className="form-label">
            Название чата
          </label>
          <input
            type="text"
            className="form-input"
            placeholder="Введите название чата"
            value={chatName}
            onChange={(e) => setChatName(e.target.value)}
          />
        </div>

        {/* Выбор группы */}
        {mode === 'group' && (
          <div className="form-section">
            <label className="form-label">
              Выберите группу
            </label>
          
          {loading && !selectedGroup ? (
            <div className="loading-indicator">
              <span className="loader-icon">🔄</span>
              Загрузка групп...
            </div>
          ) : (
            <div className="groups-grid">
              {groups.map(group => (
                <div
                  key={group.id}
                  className={`group-card ${selectedGroup?.id === group.id ? 'selected' : ''}`}
                  onClick={() => setSelectedGroup(group)}
                >
                  <div className="group-card-icon">👥</div>
                  <div className="group-card-name">{group.name}</div>
                  <div className="group-card-meta">
                    Уровень: {group.level}
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
        )}

        {/* Поиск пользователей для произвольной группы */}
        {mode === 'custom' && (
          <div className="form-section">
            <label className="form-label">
              Поиск пользователей
            </label>
            <input
              type="text"
              className="form-input search-input"
              placeholder="Поиск по имени, email или username..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
            />
          </div>
        )}

        {/* Выбор участников */}
        {(selectedGroup || mode === 'custom') && (
          <div className="form-section">
            <div className="participants-header">
              <label className="form-label">
                Участники чата
              </label>
              
              <button
                className="select-all-button"
                onClick={toggleAllStudents}
              >
                {selectedStudents.length === (mode === 'custom' ? filteredUsers : groupStudents).length ? '❌' : '✅'}
                {selectedStudents.length === (mode === 'custom' ? filteredUsers : groupStudents).length ? 'Снять все' : 'Выбрать все'}
              </button>
            </div>

            {loading ? (
              <div className="loading-indicator">
                <span className="loader-icon">🔄</span>
                {mode === 'custom' ? 'Загрузка пользователей...' : 'Загрузка студентов...'}
              </div>
            ) : mode === 'custom' ? (
              filteredUsers.length === 0 ? (
                <div className="no-students">
                  <span className="empty-icon">🔍</span>
                  <p>{searchQuery ? 'Пользователи не найдены' : 'Введите запрос для поиска'}</p>
                </div>
              ) : (
                <div className="students-list">
                  {filteredUsers.map(user => (
                    <div
                      key={user.id}
                      className={`student-item ${selectedStudents.includes(user.id) ? 'selected' : ''}`}
                      onClick={() => toggleStudent(user.id)}
                    >
                      <div className="student-checkbox">
                        {selectedStudents.includes(user.id) ? '✅' : '⬜'}
                      </div>
                      
                      <div className="student-avatar">
                        {user.first_name[0]}
                      </div>
                      
                      <div className="student-info">
                        <div className="student-name">
                          {user.first_name} {user.last_name}
                        </div>
                        <div className="student-username">
                          {user.email}
                        </div>
                        <div className="student-role">
                          {user.role === 'teacher' ? '👨‍🏫 Преподаватель' : '👨‍🎓 Студент'}
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              )
            ) : groupStudents.length === 0 ? (
              <div className="no-students">
                <span className="empty-icon">👥</span>
                <p>В группе пока нет студентов</p>
              </div>
            ) : (
              <div className="students-list">
                {groupStudents.map(student => (
                  <div
                    key={student.id}
                    className={`student-item ${selectedStudents.includes(student.id) ? 'selected' : ''}`}
                    onClick={() => toggleStudent(student.id)}
                  >
                    <div className="student-checkbox">
                      {selectedStudents.includes(student.id) ? '✅' : '⬜'}
                    </div>
                    
                    <div className="student-avatar">
                      {student.first_name[0]}
                    </div>
                    
                    <div className="student-info">
                      <div className="student-name">
                        {student.first_name} {student.last_name}
                      </div>
                      {student.username_handle && (
                        <div className="student-username">
                          @{student.username_handle}
                        </div>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            )}

            <div className="selected-count">
              Выбрано: {selectedStudents.length} {mode === 'custom' ? `из ${filteredUsers.length}` : `из ${groupStudents.length}`}
            </div>
          </div>
        )}

        {/* Footer */}
        <div className="modal-footer">
          <Button
            variant="secondary"
            onClick={handleClose}
            disabled={creating}
          >
            Отмена
          </Button>
          
          <Button
            variant="primary"
            onClick={createGroupChat}
            disabled={!chatName.trim() || selectedStudents.length === 0 || creating}
            loading={creating}
          >
            {creating ? 'Создание...' : 'Создать чат'}
          </Button>
        </div>
      </div>
    </Modal>
  );
};

export default GroupChatModal;
