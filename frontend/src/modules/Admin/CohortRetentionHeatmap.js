import React, { useState, useEffect } from 'react';
import { getAccessToken } from '../../apiService';
import './CohortRetentionHeatmap.css';

/**
 * Cohort Retention Heatmap
 * 
 * Displays a heatmap showing teacher retention by registration week.
 * Y-axis: Registration cohort weeks
 * X-axis: Weeks since registration (W0, W+1, W+2, ...)
 * Cells: Percentage of cohort that conducted at least one lesson
 */
const CohortRetentionHeatmap = ({ onClose }) => {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [weeks, setWeeks] = useState(12);
  const [retentionWeeks, setRetentionWeeks] = useState(8);

  useEffect(() => {
    loadData();
  }, [weeks, retentionWeeks]);

  const loadData = async () => {
    setLoading(true);
    setError(null);
    try {
      const token = getAccessToken();
      const response = await fetch(
        `/api/accounts/api/admin/cohort-retention/?weeks=${weeks}&retention_weeks=${retentionWeeks}`,
        {
          headers: {
            'Authorization': `Bearer ${token}`,
            'Content-Type': 'application/json',
          },
        }
      );
      
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }
      
      const result = await response.json();
      setData(result);
    } catch (err) {
      console.error('Error loading cohort retention data:', err);
      setError(err.message || 'Ошибка загрузки данных');
    } finally {
      setLoading(false);
    }
  };

  // Get color based on retention percentage
  const getHeatmapColor = (percent) => {
    if (percent === null || percent === undefined) return '#f3f4f6'; // Gray for future weeks
    if (percent >= 70) return '#10b981'; // Green
    if (percent >= 50) return '#34d399'; // Light green
    if (percent >= 30) return '#fbbf24'; // Yellow
    if (percent >= 15) return '#f97316'; // Orange
    if (percent > 0) return '#ef4444'; // Red
    return '#fee2e2'; // Very light red for 0%
  };

  const getTextColor = (percent) => {
    if (percent === null || percent === undefined) return '#9ca3af';
    if (percent >= 50) return '#ffffff';
    if (percent >= 30) return '#1f2937';
    return '#1f2937';
  };

  if (loading) {
    return (
      <div className="cohort-modal-overlay" onClick={onClose}>
        <div className="cohort-modal" onClick={(e) => e.stopPropagation()}>
          <div className="cohort-loading">
            <div className="cohort-spinner" />
            <span>Загрузка данных удержания...</span>
          </div>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="cohort-modal-overlay" onClick={onClose}>
        <div className="cohort-modal" onClick={(e) => e.stopPropagation()}>
          <div className="cohort-header">
            <h2>Cohort Retention</h2>
            <button className="cohort-close" onClick={onClose}>
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" width="20" height="20">
                <path d="M18 6L6 18M6 6l12 12" />
              </svg>
            </button>
          </div>
          <div className="cohort-error">
            <span>{error}</span>
            <button onClick={loadData} className="cohort-retry-btn">
              Повторить
            </button>
          </div>
        </div>
      </div>
    );
  }

  const cohorts = data?.cohorts || [];
  const summary = data?.summary || {};
  const avgRetention = summary.avg_retention_by_week || [];

  return (
    <div className="cohort-modal-overlay" onClick={onClose}>
      <div className="cohort-modal cohort-modal-wide" onClick={(e) => e.stopPropagation()}>
        {/* Header */}
        <div className="cohort-header">
          <div className="cohort-title-section">
            <h2>Cohort Retention</h2>
            <span className="cohort-subtitle">
              Удержание учителей по неделям регистрации
            </span>
          </div>
          <button className="cohort-close" onClick={onClose}>
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" width="20" height="20">
              <path d="M18 6L6 18M6 6l12 12" />
            </svg>
          </button>
        </div>

        {/* Controls */}
        <div className="cohort-controls">
          <div className="cohort-control-group">
            <label>Недели когорт:</label>
            <select value={weeks} onChange={(e) => setWeeks(parseInt(e.target.value))}>
              <option value="8">8 недель</option>
              <option value="12">12 недель</option>
              <option value="16">16 недель</option>
              <option value="24">24 недели</option>
            </select>
          </div>
          <div className="cohort-control-group">
            <label>Глубина удержания:</label>
            <select value={retentionWeeks} onChange={(e) => setRetentionWeeks(parseInt(e.target.value))}>
              <option value="4">4 недели</option>
              <option value="6">6 недель</option>
              <option value="8">8 недель</option>
              <option value="12">12 недель</option>
            </select>
          </div>
        </div>

        {/* Summary Cards */}
        <div className="cohort-summary">
          <div className="summary-card">
            <div className="summary-value">{summary.total_cohorts || 0}</div>
            <div className="summary-label">Когорт</div>
          </div>
          {avgRetention.slice(0, 4).map((week, idx) => (
            <div key={idx} className={`summary-card ${idx === 0 ? 'highlight' : ''}`}>
              <div className="summary-value">{week.avg_percent}%</div>
              <div className="summary-label">{week.label} средняя</div>
            </div>
          ))}
        </div>

        {/* Heatmap */}
        <div className="cohort-heatmap-container">
          {cohorts.length === 0 ? (
            <div className="cohort-empty">
              Нет данных для отображения. Попробуйте увеличить период анализа.
            </div>
          ) : (
            <table className="cohort-heatmap">
              <thead>
                <tr>
                  <th className="cohort-header-cell">Когорта</th>
                  <th className="cohort-header-cell size">Размер</th>
                  {Array.from({ length: retentionWeeks }, (_, i) => (
                    <th key={i} className="cohort-header-cell week">
                      {i === 0 ? 'W0' : `W+${i}`}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {cohorts.map((cohort, cohortIdx) => (
                  <tr key={cohort.cohort_week}>
                    <td className="cohort-label-cell">{cohort.label}</td>
                    <td className="cohort-size-cell">{cohort.cohort_size}</td>
                    {cohort.retention.map((week, weekIdx) => (
                      <td
                        key={weekIdx}
                        className="cohort-data-cell"
                        style={{
                          backgroundColor: getHeatmapColor(week?.percent),
                          color: getTextColor(week?.percent),
                        }}
                        title={week ? `${week.active} из ${cohort.cohort_size} (${week.percent}%)` : 'Будущая неделя'}
                      >
                        {week?.percent !== null && week?.percent !== undefined
                          ? `${week.percent}%`
                          : '-'}
                      </td>
                    ))}
                  </tr>
                ))}
              </tbody>
              {/* Footer with averages */}
              <tfoot>
                <tr className="cohort-avg-row">
                  <td className="cohort-label-cell">Среднее</td>
                  <td className="cohort-size-cell">-</td>
                  {avgRetention.map((week, idx) => (
                    <td
                      key={idx}
                      className="cohort-data-cell avg"
                      style={{
                        backgroundColor: getHeatmapColor(week.avg_percent),
                        color: getTextColor(week.avg_percent),
                      }}
                    >
                      {week.avg_percent}%
                    </td>
                  ))}
                </tr>
              </tfoot>
            </table>
          )}
        </div>

        {/* Legend */}
        <div className="cohort-legend">
          <span className="legend-title">Шкала:</span>
          <div className="legend-item">
            <span className="legend-color" style={{ backgroundColor: '#10b981' }}></span>
            <span>70%+</span>
          </div>
          <div className="legend-item">
            <span className="legend-color" style={{ backgroundColor: '#34d399' }}></span>
            <span>50-70%</span>
          </div>
          <div className="legend-item">
            <span className="legend-color" style={{ backgroundColor: '#fbbf24' }}></span>
            <span>30-50%</span>
          </div>
          <div className="legend-item">
            <span className="legend-color" style={{ backgroundColor: '#f97316' }}></span>
            <span>15-30%</span>
          </div>
          <div className="legend-item">
            <span className="legend-color" style={{ backgroundColor: '#ef4444' }}></span>
            <span>1-15%</span>
          </div>
          <div className="legend-item">
            <span className="legend-color" style={{ backgroundColor: '#fee2e2' }}></span>
            <span>0%</span>
          </div>
        </div>

        {/* Info */}
        <div className="cohort-info">
          <p>
            <strong>W0</strong> - неделя регистрации. <strong>W+1, W+2...</strong> - следующие недели после регистрации.
          </p>
          <p>
            Процент показывает долю учителей из когорты, которые провели хотя бы один урок в указанную неделю.
          </p>
        </div>
      </div>
    </div>
  );
};

export default CohortRetentionHeatmap;
