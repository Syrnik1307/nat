import React, { useCallback, useEffect, useMemo, useState } from 'react';
import api, { withScheduleApiBase } from '../../apiService';
import { Notification, ConfirmModal } from '../../shared/components';
import useNotification from '../../shared/hooks/useNotification';
import './StorageQuotaModal.css';

const formatBytes = (bytes) => {
  if (bytes === null || bytes === undefined || isNaN(bytes)) return '—';
  if (bytes === 0) return '0 Б';
  
  const units = ['Б', 'КБ', 'МБ', 'ГБ', 'ТБ'];
  const i = Math.floor(Math.log(bytes) / Math.log(1024));
  const value = bytes / Math.pow(1024, i);
  
  return `${value.toFixed(i > 1 ? 2 : 0)} ${units[i]}`;
};

const formatGB = (gb) => {
  if (gb === null || gb === undefined || isNaN(gb)) return '—';
  return `${gb.toFixed(2)} ГБ`;
};

const StorageQuotaModal = ({ onClose }) => {
  const { notification, confirm, closeNotification, closeConfirm } = useNotification();
  const [gdriveStats, setGdriveStats] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [search, setSearch] = useState('');
  const [selectedTeacher, setSelectedTeacher] = useState(null);
  const [sortBy, setSortBy] = useState('total_size');
  const [sortOrder, setSortOrder] = useState('desc');

  const loadData = useCallback(async () => {
    setLoading(true);
    setError('');
    try {
      const response = await api.get('storage/gdrive-stats/all/', withScheduleApiBase());
      setGdriveStats(response.data);
    } catch (err) {
      console.error('Failed to load storage stats', err);
      setError('Не удалось загрузить данные. Попробуйте ещё раз.');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadData();
  }, [loadData]);

  const filteredTeachers = useMemo(() => {
    if (!gdriveStats?.teachers) return [];
    
    let result = gdriveStats.teachers;
    
    // Фильтр по поиску
    if (search.trim()) {
      const searchLower = search.toLowerCase();
      result = result.filter(t => 
        t.teacher_name?.toLowerCase().includes(searchLower) ||
        t.teacher_email?.toLowerCase().includes(searchLower)
      );
    }
    
    // Сортировка
    result = [...result].sort((a, b) => {
      let aVal, bVal;
      switch (sortBy) {
        case 'total_size':
          aVal = a.total_size || 0;
          bVal = b.total_size || 0;
          break;
        case 'recordings':
          aVal = a.recordings?.size_mb || 0;
          bVal = b.recordings?.size_mb || 0;
          break;
        case 'homework':
          aVal = a.homework?.size_mb || 0;
          bVal = b.homework?.size_mb || 0;
          break;
        case 'materials':
          aVal = a.materials?.size_mb || 0;
          bVal = b.materials?.size_mb || 0;
          break;
        case 'name':
          aVal = a.teacher_name || '';
          bVal = b.teacher_name || '';
          return sortOrder === 'asc' ? aVal.localeCompare(bVal) : bVal.localeCompare(aVal);
        default:
          aVal = a.total_size || 0;
          bVal = b.total_size || 0;
      }
      return sortOrder === 'asc' ? aVal - bVal : bVal - aVal;
    });
    
    return result;
  }, [gdriveStats, search, sortBy, sortOrder]);

  const handleSort = (field) => {
    if (sortBy === field) {
      setSortOrder(prev => prev === 'asc' ? 'desc' : 'asc');
    } else {
      setSortBy(field);
      setSortOrder('desc');
    }
  };

  const getSortIcon = (field) => {
    if (sortBy !== field) return '';
    return sortOrder === 'asc' ? ' ↑' : ' ↓';
  };

  const getCategoryColor = (category) => {
    const colors = {
      recordings: '#3b82f6',
      homework: '#10b981',
      materials: '#f59e0b',
      students_data: '#8b5cf6'
    };
    return colors[category] || '#6b7280';
  };

  const getCategoryName = (category) => {
    const names = {
      recordings: 'Записи уроков',
      homework: 'Домашние задания',
      materials: 'Материалы',
      students_data: 'Данные учеников'
    };
    return names[category] || category;
  };

  const renderStorageBar = (teacher) => {
    const total = teacher.total_size || 1;
    const recordings = teacher.recordings?.size_mb * 1024 * 1024 || 0;
    const homework = teacher.homework?.size_mb * 1024 * 1024 || 0;
    const materials = teacher.materials?.size_mb * 1024 * 1024 || 0;
    const students = teacher.students_data?.size_mb * 1024 * 1024 || 0;

    const segments = [
      { key: 'recordings', size: recordings, color: getCategoryColor('recordings') },
      { key: 'homework', size: homework, color: getCategoryColor('homework') },
      { key: 'materials', size: materials, color: getCategoryColor('materials') },
      { key: 'students_data', size: students, color: getCategoryColor('students_data') }
    ];

    return (
      <div className="storage-category-bar">
        {segments.map(seg => {
          const percent = (seg.size / total) * 100;
          if (percent < 0.5) return null;
          return (
            <div
              key={seg.key}
              className="storage-category-segment"
              style={{ width: `${percent}%`, backgroundColor: seg.color }}
              title={`${getCategoryName(seg.key)}: ${formatBytes(seg.size)}`}
            />
          );
        })}
      </div>
    );
  };

  const renderTeacherDetails = () => {
    if (!selectedTeacher) {
      return (
        <div className="storage-details-placeholder">
          <div className="storage-details-icon">
            <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
              <path d="M22 19a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h5l2 3h9a2 2 0 0 1 2 2z"/>
            </svg>
          </div>
          <p>Выберите преподавателя слева для просмотра детальной статистики хранилища</p>
        </div>
      );
    }

    const categories = [
      { key: 'recordings', data: selectedTeacher.recordings },
      { key: 'homework', data: selectedTeacher.homework },
      { key: 'materials', data: selectedTeacher.materials },
      { key: 'students_data', data: selectedTeacher.students_data }
    ];

    const totalSize = selectedTeacher.total_size || 0;

    return (
      <div className="storage-details-content">
        <div className="storage-details-header">
          <h3>{selectedTeacher.teacher_name}</h3>
          <p className="storage-details-email">{selectedTeacher.teacher_email}</p>
        </div>

        <div className="storage-details-total">
          <div className="storage-details-total-value">{formatGB(selectedTeacher.total_size_gb)}</div>
          <div className="storage-details-total-label">Всего использовано</div>
        </div>

        <div className="storage-details-categories">
          {categories.map(cat => {
            const sizeMb = cat.data?.size_mb || 0;
            const sizeBytes = sizeMb * 1024 * 1024;
            const files = cat.data?.files || 0;
            const percent = totalSize > 0 ? (sizeBytes / totalSize) * 100 : 0;

            return (
              <div key={cat.key} className="storage-category-item">
                <div className="storage-category-header">
                  <div 
                    className="storage-category-dot" 
                    style={{ backgroundColor: getCategoryColor(cat.key) }}
                  />
                  <span className="storage-category-name">{getCategoryName(cat.key)}</span>
                </div>
                <div className="storage-category-stats">
                  <div className="storage-category-size">
                    {sizeMb >= 1024 ? formatGB(sizeMb / 1024) : `${sizeMb.toFixed(1)} МБ`}
                  </div>
                  <div className="storage-category-files">{files} файлов</div>
                </div>
                <div className="storage-category-bar-container">
                  <div 
                    className="storage-category-bar-fill"
                    style={{ 
                      width: `${Math.min(percent, 100)}%`,
                      backgroundColor: getCategoryColor(cat.key)
                    }}
                  />
                </div>
                <div className="storage-category-percent">{percent.toFixed(1)}%</div>
              </div>
            );
          })}
        </div>

        <div className="storage-details-info">
          <div className="storage-info-item">
            <span className="storage-info-label">Всего файлов:</span>
            <span className="storage-info-value">
              {categories.reduce((sum, cat) => sum + (cat.data?.files || 0), 0)}
            </span>
          </div>
        </div>
      </div>
    );
  };

  const renderSummary = () => {
    if (!gdriveStats?.summary) return null;

    const { summary, drive_quota } = gdriveStats;

    return (
      <div className="storage-summary">
        <div className="storage-summary-item">
          <div className="storage-summary-value">{summary.total_teachers}</div>
          <div className="storage-summary-label">Преподавателей</div>
        </div>
        <div className="storage-summary-item">
          <div className="storage-summary-value">{formatGB(summary.total_size_gb)}</div>
          <div className="storage-summary-label">Использовано</div>
        </div>
        <div className="storage-summary-item">
          <div className="storage-summary-value">{summary.total_files}</div>
          <div className="storage-summary-label">Всего файлов</div>
        </div>
        {drive_quota && (
          <div className="storage-summary-item storage-summary-quota">
            <div className="storage-summary-value">
              {formatGB(drive_quota.usage_gb)} / {formatGB(drive_quota.limit_gb)}
            </div>
            <div className="storage-summary-label">
              Google Drive ({drive_quota.usage_percent?.toFixed(1)}%)
            </div>
            <div className="storage-quota-bar">
              <div 
                className="storage-quota-bar-fill"
                style={{ 
                  width: `${Math.min(drive_quota.usage_percent || 0, 100)}%`,
                  backgroundColor: drive_quota.usage_percent > 90 ? '#ef4444' : 
                                   drive_quota.usage_percent > 70 ? '#f59e0b' : '#10b981'
                }}
              />
            </div>
          </div>
        )}
      </div>
    );
  };

  const renderLegend = () => (
    <div className="storage-legend">
      <div className="storage-legend-item">
        <div className="storage-legend-dot" style={{ backgroundColor: getCategoryColor('recordings') }} />
        <span>Записи</span>
      </div>
      <div className="storage-legend-item">
        <div className="storage-legend-dot" style={{ backgroundColor: getCategoryColor('homework') }} />
        <span>ДЗ</span>
      </div>
      <div className="storage-legend-item">
        <div className="storage-legend-dot" style={{ backgroundColor: getCategoryColor('materials') }} />
        <span>Материалы</span>
      </div>
      <div className="storage-legend-item">
        <div className="storage-legend-dot" style={{ backgroundColor: getCategoryColor('students_data') }} />
        <span>Ученики</span>
      </div>
    </div>
  );

  return (
    <div className="storage-modal-overlay" onClick={onClose}>
      <div className="storage-modal storage-modal-v2" onClick={(e) => e.stopPropagation()}>
        <div className="storage-modal-header">
          <div className="storage-modal-title">
            <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <path d="M22 19a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h5l2 3h9a2 2 0 0 1 2 2z"/>
            </svg>
            <h2>Управление хранилищем</h2>
          </div>
          <button className="modal-close" onClick={onClose} aria-label="Закрыть">
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <path d="M18 6L6 18M6 6l12 12"/>
            </svg>
          </button>
        </div>
        
        <p className="storage-modal-subtitle">
          Просматривайте использование хранилища Google Drive по каждому преподавателю с разбивкой по категориям.
        </p>

        {error && (
          <div className="storage-error">
            {error}
            <button className="storage-link-button" onClick={loadData}>Повторить</button>
          </div>
        )}

        {renderSummary()}

        <div className="storage-controls">
          <div className="storage-search-wrapper">
            <svg className="storage-search-icon" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <circle cx="11" cy="11" r="8"/>
              <path d="M21 21l-4.35-4.35"/>
            </svg>
            <input
              type="text"
              placeholder="Поиск преподавателя..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
            />
          </div>
          {renderLegend()}
          <button className="storage-refresh-btn" onClick={loadData} disabled={loading}>
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <path d="M23 4v6h-6M1 20v-6h6"/>
              <path d="M3.51 9a9 9 0 0 1 14.85-3.36L23 10M1 14l4.64 4.36A9 9 0 0 0 20.49 15"/>
            </svg>
            Обновить
          </button>
        </div>

        <div className="storage-content">
          <div className="storage-panel storage-panel-left">
            {loading ? (
              <div className="storage-loading">
                <div className="storage-spinner" />
                <span>Загрузка данных из Google Drive...</span>
              </div>
            ) : filteredTeachers.length === 0 ? (
              <div className="storage-empty">
                {search ? 'Преподаватели не найдены' : 'Нет данных о хранилище'}
              </div>
            ) : (
              <table className="storage-table">
                <thead>
                  <tr>
                    <th 
                      className="sortable" 
                      onClick={() => handleSort('name')}
                    >
                      Преподаватель{getSortIcon('name')}
                    </th>
                    <th 
                      className="sortable numeric" 
                      onClick={() => handleSort('total_size')}
                    >
                      Всего{getSortIcon('total_size')}
                    </th>
                    <th 
                      className="sortable numeric" 
                      onClick={() => handleSort('recordings')}
                    >
                      Записи{getSortIcon('recordings')}
                    </th>
                    <th 
                      className="sortable numeric" 
                      onClick={() => handleSort('homework')}
                    >
                      ДЗ{getSortIcon('homework')}
                    </th>
                    <th 
                      className="sortable numeric" 
                      onClick={() => handleSort('materials')}
                    >
                      Материалы{getSortIcon('materials')}
                    </th>
                    <th className="distribution-col">Распределение</th>
                  </tr>
                </thead>
                <tbody>
                  {filteredTeachers.map((teacher) => (
                    <tr
                      key={teacher.teacher_id}
                      className={selectedTeacher?.teacher_id === teacher.teacher_id ? 'selected' : ''}
                      onClick={() => setSelectedTeacher(teacher)}
                    >
                      <td>
                        <div className="teacher-cell">
                          <div className="teacher-name">{teacher.teacher_name}</div>
                          <div className="teacher-email">{teacher.teacher_email}</div>
                        </div>
                      </td>
                      <td className="numeric">
                        <span className="size-value">{formatGB(teacher.total_size_gb)}</span>
                      </td>
                      <td className="numeric">
                        <span className="category-value recordings">
                          {teacher.recordings?.size_mb?.toFixed(0) || 0} МБ
                        </span>
                      </td>
                      <td className="numeric">
                        <span className="category-value homework">
                          {teacher.homework?.size_mb?.toFixed(0) || 0} МБ
                        </span>
                      </td>
                      <td className="numeric">
                        <span className="category-value materials">
                          {teacher.materials?.size_mb?.toFixed(0) || 0} МБ
                        </span>
                      </td>
                      <td className="distribution-col">
                        {renderStorageBar(teacher)}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </div>

          <div className="storage-panel storage-panel-right">
            {renderTeacherDetails()}
          </div>
        </div>
      </div>

      <Notification
        isOpen={notification.isOpen}
        onClose={closeNotification}
        type={notification.type}
        title={notification.title}
        message={notification.message}
      />

      <ConfirmModal
        isOpen={confirm.isOpen}
        onClose={closeConfirm}
        onConfirm={confirm.onConfirm}
        title={confirm.title}
        message={confirm.message}
        variant={confirm.variant}
        confirmText={confirm.confirmText}
        cancelText={confirm.cancelText}
      />
    </div>
  );
};

export default StorageQuotaModal;
