import React, { useState, useEffect } from 'react';
import './TeacherRecordingsPage.css';
import api from '../../apiService';
import RecordingCard from './RecordingCard';
import RecordingPlayer from './RecordingPlayer';

function TeacherRecordingsPage() {
  const [recordings, setRecordings] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [selectedRecording, setSelectedRecording] = useState(null);
  const [searchTerm, setSearchTerm] = useState('');
  const [groupFilter, setGroupFilter] = useState('all');
  const [statusFilter, setStatusFilter] = useState('all');
  const [groups, setGroups] = useState([]);
  const [stats, setStats] = useState({
    total: 0,
    ready: 0,
    processing: 0,
    failed: 0
  });

  useEffect(() => {
    loadRecordings();
    loadGroups();
  }, []);

  const loadRecordings = async () => {
    try {
      setLoading(true);
      setError(null);
      const response = await api.get('/schedule/api/recordings/teacher/');
      const recordingsData = response.data.results || response.data;
      setRecordings(recordingsData);
      
      // Подсчитываем статистику
      const stats = {
        total: recordingsData.length,
        ready: recordingsData.filter(r => r.status === 'ready').length,
        processing: recordingsData.filter(r => r.status === 'processing').length,
        failed: recordingsData.filter(r => r.status === 'failed').length
      };
      setStats(stats);
    } catch (err) {
      console.error('Error loading recordings:', err);
      setError('Не удалось загрузить записи. Попробуйте позже.');
    } finally {
      setLoading(false);
    }
  };

  const loadGroups = async () => {
    try {
      const response = await api.get('/schedule/api/teacher/groups/');
      setGroups(response.data);
    } catch (err) {
      console.error('Error loading groups:', err);
    }
  };

  const openPlayer = async (recording) => {
    setSelectedRecording(recording);
    // Трекаем просмотр
    try {
      await api.post(`/schedule/api/recordings/${recording.id}/view/`);
    } catch (err) {
      console.error('Error tracking view:', err);
    }
  };

  const closePlayer = () => {
    setSelectedRecording(null);
    // Обновляем список чтобы показать новый счетчик просмотров
    loadRecordings();
  };

  const handleDelete = async (recordingId) => {
    if (!window.confirm('Вы уверены, что хотите удалить эту запись? Это действие необратимо.')) {
      return;
    }

    try {
      await api.delete(`/schedule/api/recordings/${recordingId}/`);
      setRecordings(recordings.filter(r => r.id !== recordingId));
      alert('Запись успешно удалена');
    } catch (err) {
      console.error('Error deleting recording:', err);
      alert('Не удалось удалить запись. Попробуйте позже.');
    }
  };

  // Фильтрация записей
  const filteredRecordings = recordings.filter(recording => {
    const matchesSearch = recording.lesson_info?.subject?.toLowerCase().includes(searchTerm.toLowerCase()) ||
                         recording.lesson_info?.group_name?.toLowerCase().includes(searchTerm.toLowerCase());
    const matchesGroup = groupFilter === 'all' || recording.lesson_info?.group_id === parseInt(groupFilter);
    const matchesStatus = statusFilter === 'all' || recording.status === statusFilter;
    
    return matchesSearch && matchesGroup && matchesStatus;
  });

  return (
    <div className="teacher-recordings-page">
      <div className="teacher-recordings-header">
        <h1>📹 Записи моих уроков</h1>
        <p className="teacher-recordings-subtitle">Управление и просмотр записей занятий</p>
      </div>

      {/* Статистика */}
      <div className="teacher-stats-grid">
        <div className="teacher-stat-card">
          <div className="teacher-stat-icon">📊</div>
          <div className="teacher-stat-info">
            <div className="teacher-stat-value">{stats.total}</div>
            <div className="teacher-stat-label">Всего записей</div>
          </div>
        </div>
        <div className="teacher-stat-card teacher-stat-success">
          <div className="teacher-stat-icon">✅</div>
          <div className="teacher-stat-info">
            <div className="teacher-stat-value">{stats.ready}</div>
            <div className="teacher-stat-label">Готово</div>
          </div>
        </div>
        <div className="teacher-stat-card teacher-stat-warning">
          <div className="teacher-stat-icon">⏳</div>
          <div className="teacher-stat-info">
            <div className="teacher-stat-value">{stats.processing}</div>
            <div className="teacher-stat-label">Обрабатывается</div>
          </div>
        </div>
        <div className="teacher-stat-card teacher-stat-danger">
          <div className="teacher-stat-icon">❌</div>
          <div className="teacher-stat-info">
            <div className="teacher-stat-value">{stats.failed}</div>
            <div className="teacher-stat-label">Ошибка</div>
          </div>
        </div>
      </div>

      {/* Фильтры */}
      <div className="teacher-recordings-filters">
        <div className="teacher-search-box">
          <input
            type="text"
            placeholder="🔍 Поиск по предмету или группе..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            className="teacher-search-input"
          />
        </div>

        <div className="teacher-filter-group">
          <label>Группа:</label>
          <select
            value={groupFilter}
            onChange={(e) => setGroupFilter(e.target.value)}
            className="teacher-filter-select"
          >
            <option value="all">Все группы</option>
            {groups.map(group => (
              <option key={group.id} value={group.id}>{group.name}</option>
            ))}
          </select>
        </div>

        <div className="teacher-filter-group">
          <label>Статус:</label>
          <select
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value)}
            className="teacher-filter-select"
          >
            <option value="all">Все статусы</option>
            <option value="ready">Готово</option>
            <option value="processing">Обрабатывается</option>
            <option value="failed">Ошибка</option>
            <option value="archived">Архивировано</option>
          </select>
        </div>

        <button onClick={loadRecordings} className="teacher-refresh-btn">
          🔄 Обновить
        </button>
      </div>

      {/* Контент */}
      {loading ? (
        <div className="teacher-recordings-loading">
          <div className="teacher-spinner"></div>
          <p>Загрузка записей...</p>
        </div>
      ) : error ? (
        <div className="teacher-recordings-error">
          <p>❌ {error}</p>
          <button onClick={loadRecordings} className="teacher-retry-btn">
            Попробовать снова
          </button>
        </div>
      ) : filteredRecordings.length === 0 ? (
        <div className="teacher-recordings-empty">
          <div className="teacher-empty-icon">📹</div>
          <h3>Записей не найдено</h3>
          <p>
            {recordings.length === 0
              ? 'Пока нет записанных уроков. Включите запись при создании урока.'
              : 'Попробуйте изменить фильтры или поисковый запрос.'}
          </p>
        </div>
      ) : (
        <>
          <div className="teacher-recordings-count">
            Найдено записей: <strong>{filteredRecordings.length}</strong>
          </div>
          <div className="teacher-recordings-grid">
            {filteredRecordings.map(recording => (
              <RecordingCard
                key={recording.id}
                recording={recording}
                onPlay={openPlayer}
                onDelete={handleDelete}
                showDelete={true}
              />
            ))}
          </div>
        </>
      )}

      {/* Плеер */}
      {selectedRecording && (
        <RecordingPlayer
          recording={selectedRecording}
          onClose={closePlayer}
        />
      )}
    </div>
  );
}

export default TeacherRecordingsPage;
