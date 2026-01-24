import React, { useState, useEffect, useRef } from 'react';
import api, { withScheduleApiBase } from '../../apiService';
import { getCached } from '../../utils/dataCache';
import RecordingCard from './RecordingCard';
import FastVideoModal from './FastVideoModal';
import './RecordingsPage.css';

function RecordingsPage() {
  const [recordings, setRecordings] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [selectedRecording, setSelectedRecording] = useState(null);
  const [searchTerm, setSearchTerm] = useState('');
  const [groupFilter, setGroupFilter] = useState('all');
  const [groups, setGroups] = useState([]);
  const [filterOpen, setFilterOpen] = useState(false);
  const filterRef = useRef(null);
  const initialLoadDone = useRef(false);

  useEffect(() => {
    loadData(!initialLoadDone.current);
    initialLoadDone.current = true;
  }, []);

  const loadData = async (useCache = true) => {
    const cacheTTL = 30000; // 30 секунд
    
    if (useCache) {
      try {
        const [cachedRecordings, cachedGroups] = await Promise.all([
          getCached('student:recordings', async () => {
            return await fetchRecordings();
          }, cacheTTL),
          getCached('student:rec-groups', async () => {
            return await fetchGroups();
          }, cacheTTL),
        ]);
        setRecordings(cachedRecordings);
        setGroups(cachedGroups);
        setLoading(false);
        return;
      } catch (e) {
        console.error('Error loading cached data:', e);
      }
    }
    
    // Fallback: загружаем без кэша
    await loadRecordings();
    await loadGroups();
  };

  const fetchRecordings = async () => {
    const tryFetch = async (path) => {
      const response = await api.get(path, withScheduleApiBase());
      const data = response?.data;
      const results = Array.isArray(data?.results) ? data.results : null;
      const arr = results ?? (Array.isArray(data) ? data : []);
      if (!results && !Array.isArray(data)) {
        console.warn('[RecordingsPage] Unexpected recordings response shape:', data);
      }
      return arr;
    };

    let arr = [];
    try {
      arr = await tryFetch('recordings/');
    } catch (primaryErr) {
      if (primaryErr?.response?.status === 404) {
        try {
          arr = await tryFetch('recordings/teacher/');
        } catch (fallbackErr) {
          throw fallbackErr;
        }
      } else {
        throw primaryErr;
      }
    }
    return arr;
  };

  const fetchGroups = async () => {
    const response = await api.get('groups/');
    const data = response?.data;
    const results = Array.isArray(data?.results) ? data.results : null;
    const arr = results ?? (Array.isArray(data) ? data : []);
    if (!results && !Array.isArray(data)) {
      console.warn('[RecordingsPage] Unexpected groups response shape:', data);
    }
    return arr;
  };

  const loadRecordings = async () => {
    try {
      setLoading(true);
      setError(null);
      const arr = await fetchRecordings();
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
      const arr = await fetchGroups();
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

  // close custom dropdown when clicking outside
  useEffect(() => {
    const onDocClick = (e) => {
      if (filterRef.current && !filterRef.current.contains(e.target)) {
        setFilterOpen(false);
      }
    };
    document.addEventListener('mousedown', onDocClick);
    return () => document.removeEventListener('mousedown', onDocClick);
  }, []);

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
        <h1>Записи уроков</h1>
        <p className="subtitle">Все записи ваших занятий в одном месте</p>
      </div>

      {error && (
        <div className="error-message">
          <span className="error-icon"></span>
          {error}
        </div>
      )}

      {/* Фильтры и поиск */}
      <div className="recordings-filters">
        <div className="search-box">
          <input
            type="text"
            placeholder="Поиск по названию или предмету..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            className="search-input"
          />
        </div>

        <div className="filter-group" ref={filterRef}>
          <label>Группа:</label>
          <button
            type="button"
            className="filter-select"
            aria-haspopup="listbox"
            aria-expanded={filterOpen}
            onClick={() => setFilterOpen((v) => !v)}
            onKeyDown={(e) => { if (e.key === 'Escape') setFilterOpen(false); }}
          >
            <span>{groupFilter === 'all' ? 'Все группы' : (groups.find(g => String(g.id) === String(groupFilter))?.name || 'Группа')}</span>
            <span className="filter-caret" aria-hidden>{filterOpen ? '▴' : '▾'}</span>
          </button>
          {filterOpen && (
            <div className="filter-menu" role="listbox" aria-label="Фильтр по группе">
              <button
                type="button"
                className={`filter-option ${groupFilter === 'all' ? 'selected' : ''}`}
                role="option"
                aria-selected={groupFilter === 'all'}
                onClick={() => { setGroupFilter('all'); setFilterOpen(false); }}
              >
                Все группы
              </button>
              {groups.map((group) => (
                <button
                  key={group.id}
                  type="button"
                  className={`filter-option ${String(groupFilter) === String(group.id) ? 'selected' : ''}`}
                  role="option"
                  aria-selected={String(groupFilter) === String(group.id)}
                  onClick={() => { setGroupFilter(String(group.id)); setFilterOpen(false); }}
                >
                  {group.name}
                </button>
              ))}
            </div>
          )}
        </div>
      </div>

      {/* Список записей */}
      {filteredRecordings.length === 0 ? (
        <div className="empty-state">
          <div className="empty-icon"></div>
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
        <FastVideoModal
          recording={selectedRecording}
          onClose={closePlayer}
        />
      )}
    </div>
  );
}

export default RecordingsPage;
