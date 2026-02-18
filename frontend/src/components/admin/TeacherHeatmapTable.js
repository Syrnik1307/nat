import React, { useState, useEffect, useCallback } from 'react';
import { apiClient } from '../../apiService';
import './TeacherHeatmapTable.css';

/**
 * TeacherHeatmapTable - Сравнительная таблица активности учителей
 * 
 * Отображает всех учителей с мини-heatmap по неделям.
 * Оптимизирован для 1000+ учителей с пагинацией.
 * 
 * Цветовая шкала: белый (0) -> бледно-красный -> ярко-красный
 */
const TeacherHeatmapTable = () => {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  
  // Фильтры и пагинация
  const [period, setPeriod] = useState(30);
  const [page, setPage] = useState(1);
  const [pageSize] = useState(50);
  const [search, setSearch] = useState('');
  const [searchInput, setSearchInput] = useState('');
  const [sortBy, setSortBy] = useState('total_score');
  const [sortOrder, setSortOrder] = useState('desc');
  
  // Дебаунс для поиска
  useEffect(() => {
    const timer = setTimeout(() => {
      setSearch(searchInput);
      setPage(1);
    }, 300);
    return () => clearTimeout(timer);
  }, [searchInput]);
  
  const fetchData = useCallback(async () => {
    setLoading(true);
    setError(null);
    
    try {
      const params = new URLSearchParams({
        period: period.toString(),
        page: page.toString(),
        page_size: pageSize.toString(),
        sort: sortBy,
        order: sortOrder,
      });
      
      if (search) {
        params.append('search', search);
      }
      
      const response = await apiClient.get(`/analytics/teacher-heatmap/teachers/?${params}`);
      setData(response.data);
    } catch (err) {
      console.error('Error fetching teacher heatmap:', err);
      setError('Не удалось загрузить данные');
    } finally {
      setLoading(false);
    }
  }, [period, page, pageSize, search, sortBy, sortOrder]);
  
  useEffect(() => {
    fetchData();
  }, [fetchData]);
  
  const handleSort = (column) => {
    if (sortBy === column) {
      setSortOrder(sortOrder === 'desc' ? 'asc' : 'desc');
    } else {
      setSortBy(column);
      setSortOrder('desc');
    }
    setPage(1);
  };
  
  const getWeekColor = (score, maxScore) => {
    if (score === 0) return 'var(--th-level-0)';
    
    const intensity = Math.min(score / (maxScore * 0.6), 1);
    
    if (intensity <= 0.25) return 'var(--th-level-1)';
    if (intensity <= 0.5) return 'var(--th-level-2)';
    if (intensity <= 0.75) return 'var(--th-level-3)';
    return 'var(--th-level-4)';
  };
  
  const getSortIcon = (column) => {
    if (sortBy !== column) return null;
    return sortOrder === 'desc' ? ' ↓' : ' ↑';
  };
  
  if (loading && !data) {
    return (
      <div className="th-container">
        <div className="th-header">
          <h2>Активность преподавателей</h2>
        </div>
        <div className="th-skeleton">
          {[...Array(10)].map((_, i) => (
            <div key={i} className="th-skeleton-row" />
          ))}
        </div>
      </div>
    );
  }
  
  if (error) {
    return (
      <div className="th-container">
        <div className="th-error">
          <span>{error}</span>
          <button onClick={fetchData}>Повторить</button>
        </div>
      </div>
    );
  }
  
  return (
    <div className="th-container">
      <div className="th-header">
        <h2>Активность преподавателей</h2>
        
        <div className="th-controls">
          <div className="th-search">
            <input
              type="text"
              placeholder="Поиск по имени или email..."
              value={searchInput}
              onChange={(e) => setSearchInput(e.target.value)}
            />
          </div>
          
          <div className="th-period-toggle">
            <button
              className={period === 30 ? 'active' : ''}
              onClick={() => { setPeriod(30); setPage(1); }}
            >
              1 месяц
            </button>
            <button
              className={period === 90 ? 'active' : ''}
              onClick={() => { setPeriod(90); setPage(1); }}
            >
              3 месяца
            </button>
          </div>
        </div>
      </div>
      
      <div className="th-legend">
        <span className="th-legend-label">Меньше</span>
        <div className="th-legend-scale">
          <span className="th-legend-cell" style={{ backgroundColor: 'var(--th-level-0)' }} />
          <span className="th-legend-cell" style={{ backgroundColor: 'var(--th-level-1)' }} />
          <span className="th-legend-cell" style={{ backgroundColor: 'var(--th-level-2)' }} />
          <span className="th-legend-cell" style={{ backgroundColor: 'var(--th-level-3)' }} />
          <span className="th-legend-cell" style={{ backgroundColor: 'var(--th-level-4)' }} />
        </div>
        <span className="th-legend-label">Больше</span>
      </div>
      
      <div className="th-table-wrapper">
        <table className="th-table">
          <thead>
            <tr>
              <th 
                className="th-col-name sortable" 
                onClick={() => handleSort('name')}
              >
                Преподаватель{getSortIcon('name')}
              </th>
              <th 
                className="th-col-score sortable" 
                onClick={() => handleSort('total_score')}
              >
                Баллы{getSortIcon('total_score')}
              </th>
              <th 
                className="th-col-lessons sortable" 
                onClick={() => handleSort('lessons')}
              >
                Занятия{getSortIcon('lessons')}
              </th>
              <th 
                className="th-col-hw sortable" 
                onClick={() => handleSort('homeworks')}
              >
                ДЗ{getSortIcon('homeworks')}
              </th>
              <th className="th-col-heatmap">
                Активность по неделям
              </th>
            </tr>
          </thead>
          <tbody>
            {data?.teachers?.map((teacher) => (
              <tr key={teacher.id}>
                <td className="th-col-name">
                  <a href={`/admin/teacher-heatmap/${teacher.id}`} className="th-teacher-link">
                    <span className="th-teacher-name">{teacher.name}</span>
                    <span className="th-teacher-email">{teacher.email}</span>
                  </a>
                </td>
                <td className="th-col-score">
                  <span className="th-score-value">{teacher.stats.total_score}</span>
                </td>
                <td className="th-col-lessons">{teacher.stats.lessons}</td>
                <td className="th-col-hw">{teacher.stats.homeworks_graded}</td>
                <td className="th-col-heatmap">
                  <div className="th-mini-heatmap">
                    {data.weeks?.map((week) => (
                      <div
                        key={week.date}
                        className="th-week-cell"
                        style={{
                          backgroundColor: getWeekColor(
                            teacher.weekly_scores[week.date] || 0,
                            data.max_weekly_score
                          ),
                        }}
                        title={`${week.label}: ${teacher.weekly_scores[week.date] || 0} баллов`}
                      />
                    ))}
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      
      {data?.pagination && data.pagination.total_pages > 1 && (
        <div className="th-pagination">
          <button
            disabled={page === 1}
            onClick={() => setPage(p => p - 1)}
          >
            Назад
          </button>
          <span className="th-page-info">
            Страница {page} из {data.pagination.total_pages}
            {' '}({data.pagination.total_count} учителей)
          </span>
          <button
            disabled={page === data.pagination.total_pages}
            onClick={() => setPage(p => p + 1)}
          >
            Вперед
          </button>
        </div>
      )}
      
      {loading && <div className="th-loading-overlay">Загрузка...</div>}
    </div>
  );
};

export default TeacherHeatmapTable;
