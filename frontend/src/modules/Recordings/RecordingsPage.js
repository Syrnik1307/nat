import React, { useState, useEffect } from 'react';
import api, { withScheduleApiBase } from '../../apiService';
import RecordingCard from './RecordingCard';
import RecordingPlayer from './RecordingPlayer';
import './RecordingsPage.css';

function RecordingsPage() {
  const [recordings, setRecordings] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [selectedRecording, setSelectedRecording] = useState(null);
  const [searchTerm, setSearchTerm] = useState('');
  const [groupFilter, setGroupFilter] = useState('all');
  const [groups, setGroups] = useState([]);

  useEffect(() => {
    loadRecordings();
    loadGroups();
  }, []);

  const loadRecordings = async () => {
    try {
      setLoading(true);
      setError(null);
      const response = await api.get('recordings/', withScheduleApiBase());
      const data = response?.data;
      const results = Array.isArray(data?.results) ? data.results : null;
      const arr = results ?? (Array.isArray(data) ? data : []);
      if (!results && !Array.isArray(data)) {
        console.warn('[RecordingsPage] Unexpected recordings response shape:', data);
      }
      setRecordings(arr);
    } catch (err) {
      console.error('Failed to load recordings:', err);
      setError('Не удалось загрузить записи. Попробуйте обновить страницу.');
    } finally {
      setLoading(false);
    }
  };

  const loadGroups = async () => {
    try {
      const response = await api.get('groups/', withScheduleApiBase());
      const data = response?.data;
      const results = Array.isArray(data?.results) ? data.results : null;
      const arr = results ?? (Array.isArray(data) ? data : []);
      if (!results && !Array.isArray(data)) {
        console.warn('[RecordingsPage] Unexpected groups response shape:', data);
      }
      setGroups(arr);
    } catch (err) {
      console.error('Failed to load groups:', err);
    }
  };

  const openPlayer = (recording) => {
    setSelectedRecording(recording);
    // Отслеживаем просмотр
    api.post(`recordings/${recording.id}/view/`, {}, withScheduleApiBase())
      .catch(err => console.error('Failed to track view:', err));
  };

  const closePlayer = () => {
    setSelectedRecording(null);
  };

  // Фильтрация записей
  const getAccessGroupIds = (rec) => {
    if (Array.isArray(rec.access_groups) && rec.access_groups.length > 0) {
      return rec.access_groups.map((group) => group.id);
    }
    const fallbackId = rec.lesson_info?.group_id;
    return fallbackId ? [fallbackId] : [];
  };

  const filteredRecordings = recordings.filter(rec => {
    const normalizedSearch = searchTerm.trim().toLowerCase();
    const matchesSearch = !normalizedSearch || 
      rec.lesson_info?.title?.toLowerCase().includes(normalizedSearch) ||
      rec.lesson_info?.subject?.toLowerCase().includes(normalizedSearch) ||
      (Array.isArray(rec.access_groups) && rec.access_groups
        .some(group => (group.name || '').toLowerCase().includes(normalizedSearch)));
    
    const accessGroupIds = getAccessGroupIds(rec);
    const matchesGroup = groupFilter === 'all' || 
      accessGroupIds.includes(Number(groupFilter));
    
    return matchesSearch && matchesGroup;
  });

  if (loading) {
    return (
      <div className="recordings-page">
        <div className="loading-container">
          <div className="spinner"></div>
          <p>Загрузка записей...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="recordings-page">
      <div className="recordings-header">
        <h1>📹 Записи уроков</h1>
        <p className="subtitle">Все записи ваших занятий в одном месте</p>
      </div>

      {error && (
        <div className="error-message">
          <span className="error-icon">⚠️</span>
          {error}
        </div>
      )}

      {/* Фильтры и поиск */}
      <div className="recordings-filters">
        <div className="search-box">
          <input
            type="text"
            placeholder="🔍 Поиск по названию или предмету..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            className="search-input"
          />
        </div>

        <div className="filter-group">
          <label>Группа:</label>
          <select
            value={groupFilter}
            onChange={(e) => setGroupFilter(e.target.value)}
            className="filter-select"
          >
            <option value="all">Все группы</option>
            {groups.map(group => (
              <option key={group.id} value={group.id}>
                {group.name}
              </option>
            ))}
          </select>
        </div>
      </div>

      {/* Список записей */}
      {filteredRecordings.length === 0 ? (
        <div className="empty-state">
          <div className="empty-icon">🎥</div>
          <h3>Пока нет доступных записей</h3>
          <p>Записи появятся здесь после проведения уроков с включенной записью</p>
        </div>
      ) : (
        <>
          <div className="recordings-stats">
            <span className="stat-item">
              <strong>{filteredRecordings.length}</strong> записей
            </span>
            {searchTerm && (
              <span className="stat-item">
                (найдено по запросу: "{searchTerm}")
              </span>
            )}
          </div>

          <div className="recordings-grid">
            {filteredRecordings.map(recording => (
              <RecordingCard
                key={recording.id}
                recording={recording}
                onPlay={openPlayer}
              />
            ))}
          </div>
        </>
      )}

      {/* Модальное окно с плеером */}
      {selectedRecording && (
        <RecordingPlayer
          recording={selectedRecording}
          onClose={closePlayer}
        />
      )}
    </div>
  );
}

export default RecordingsPage;
