import React, { useState, useEffect, useCallback } from 'react';
import { useParams, Link } from 'react-router-dom';
import { apiClient } from '../../apiService';
import './TeacherHeatmapDetail.css';

/**
 * TeacherHeatmapDetail - Детальный heatmap конкретного учителя
 * 
 * GitHub-style календарь активности + статистика + разбивка по событиям.
 */
const TeacherHeatmapDetail = () => {
  const { teacherId } = useParams();
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [period, setPeriod] = useState(90);
  const [hoveredDay, setHoveredDay] = useState(null);
  
  const fetchData = useCallback(async () => {
    setLoading(true);
    setError(null);
    
    try {
      const response = await apiClient.get(
        `/analytics/teacher-heatmap/teacher/${teacherId}/?period=${period}`
      );
      setData(response.data);
    } catch (err) {
      console.error('Error fetching teacher detail:', err);
      setError('Не удалось загрузить данные');
    } finally {
      setLoading(false);
    }
  }, [teacherId, period]);
  
  useEffect(() => {
    fetchData();
  }, [fetchData]);
  
  const getLevel = (level) => {
    return `thd-level-${level}`;
  };
  
  const formatDate = (dateStr) => {
    const date = new Date(dateStr);
    return date.toLocaleDateString('ru-RU', {
      weekday: 'short',
      day: 'numeric',
      month: 'short',
    });
  };
  
  const getEventLabel = (eventType) => {
    const labels = {
      'login': 'Вход',
      'lesson_conducted': 'Занятие',
      'homework_created': 'Создано ДЗ',
      'homework_graded': 'Проверено ДЗ',
      'recording_uploaded': 'Запись',
      'student_feedback': 'Комментарий',
      'material_created': 'Материал',
      'session_time': 'Сессия',
    };
    return labels[eventType] || eventType;
  };
  
  if (loading && !data) {
    return (
      <div className="thd-container">
        <div className="thd-skeleton">
          <div className="thd-skeleton-header" />
          <div className="thd-skeleton-grid" />
        </div>
      </div>
    );
  }
  
  if (error) {
    return (
      <div className="thd-container">
        <div className="thd-error">
          <span>{error}</span>
          <button onClick={fetchData}>Повторить</button>
        </div>
      </div>
    );
  }
  
  // Группировка дней по неделям для сетки
  const weeks = [];
  let currentWeek = [];
  
  data?.heatmap_data?.forEach((day, index) => {
    const date = new Date(day.date);
    const dayOfWeek = date.getDay();
    
    // Сдвигаем воскресенье (0) в конец
    const adjustedDay = dayOfWeek === 0 ? 6 : dayOfWeek - 1;
    
    if (index === 0) {
      // Заполняем начало недели пустыми ячейками
      for (let i = 0; i < adjustedDay; i++) {
        currentWeek.push(null);
      }
    }
    
    currentWeek.push(day);
    
    if (adjustedDay === 6 || index === data.heatmap_data.length - 1) {
      weeks.push(currentWeek);
      currentWeek = [];
    }
  });
  
  const daysOfWeek = ['Пн', 'Вт', 'Ср', 'Чт', 'Пт', 'Сб', 'Вс'];
  
  return (
    <div className="thd-container">
      <Link to="/admin/teacher-heatmap" className="thd-back-link">
        Назад к списку
      </Link>
      
      <div className="thd-header">
        <div className="thd-teacher-info">
          <h2>{data?.teacher_name}</h2>
          <span className="thd-email">{data?.teacher_email}</span>
        </div>
        
        <div className="thd-period-toggle">
          <button
            className={period === 30 ? 'active' : ''}
            onClick={() => setPeriod(30)}
          >
            1 месяц
          </button>
          <button
            className={period === 90 ? 'active' : ''}
            onClick={() => setPeriod(90)}
          >
            3 месяца
          </button>
        </div>
      </div>
      
      {/* Stats Cards */}
      <div className="thd-stats-grid">
        <div className="thd-stat-card">
          <span className="thd-stat-value">{data?.stats?.total_contributions || 0}</span>
          <span className="thd-stat-label">Всего баллов</span>
        </div>
        <div className="thd-stat-card">
          <span className="thd-stat-value">{data?.stats?.current_streak || 0}</span>
          <span className="thd-stat-label">Текущая серия</span>
        </div>
        <div className="thd-stat-card">
          <span className="thd-stat-value">{data?.stats?.longest_streak || 0}</span>
          <span className="thd-stat-label">Макс. серия</span>
        </div>
        <div className="thd-stat-card">
          <span className="thd-stat-value">{data?.stats?.days_active || 0}</span>
          <span className="thd-stat-label">Активных дней</span>
        </div>
        <div className="thd-stat-card">
          <span className="thd-stat-value">{data?.stats?.total_session_hours || 0}ч</span>
          <span className="thd-stat-label">На платформе</span>
        </div>
      </div>
      
      {/* Heatmap Grid */}
      <div className="thd-heatmap-section">
        <h3>Календарь активности</h3>
        
        <div className="thd-heatmap-wrapper">
          <div className="thd-day-labels">
            {daysOfWeek.map(day => (
              <span key={day} className="thd-day-label">{day}</span>
            ))}
          </div>
          
          <div className="thd-grid">
            {weeks.map((week, weekIndex) => (
              <div key={weekIndex} className="thd-week">
                {week.map((day, dayIndex) => (
                  day ? (
                    <div
                      key={day.date}
                      className={`thd-cell ${getLevel(day.level)}`}
                      onMouseEnter={() => setHoveredDay(day)}
                      onMouseLeave={() => setHoveredDay(null)}
                    />
                  ) : (
                    <div key={`empty-${dayIndex}`} className="thd-cell thd-empty" />
                  )
                ))}
              </div>
            ))}
          </div>
        </div>
        
        <div className="thd-legend">
          <span>Меньше</span>
          <div className="thd-legend-scale">
            <span className="thd-legend-cell thd-level-0" />
            <span className="thd-legend-cell thd-level-1" />
            <span className="thd-legend-cell thd-level-2" />
            <span className="thd-legend-cell thd-level-3" />
            <span className="thd-legend-cell thd-level-4" />
          </div>
          <span>Больше</span>
        </div>
        
        {/* Tooltip */}
        {hoveredDay && (
          <div className="thd-tooltip">
            <div className="thd-tooltip-date">{formatDate(hoveredDay.date)}</div>
            <div className="thd-tooltip-score">{hoveredDay.count} баллов</div>
            {Object.keys(hoveredDay.events || {}).length > 0 && (
              <div className="thd-tooltip-events">
                {Object.entries(hoveredDay.events).map(([type, count]) => (
                  <div key={type} className="thd-tooltip-event">
                    {getEventLabel(type)}: {count}
                  </div>
                ))}
              </div>
            )}
          </div>
        )}
      </div>
      
      {/* Event Breakdown */}
      <div className="thd-breakdown-section">
        <h3>Разбивка по действиям</h3>
        
        <div className="thd-breakdown-list">
          {data?.event_breakdown?.map((item) => (
            <div key={item.action_type} className="thd-breakdown-item">
              <div className="thd-breakdown-info">
                <span className="thd-breakdown-label">{item.label}</span>
                <span className="thd-breakdown-count">{item.count}</span>
              </div>
              <div className="thd-breakdown-bar-wrapper">
                <div 
                  className="thd-breakdown-bar"
                  style={{
                    width: `${(item.total_score / (data.stats?.total_contributions || 1)) * 100}%`
                  }}
                />
              </div>
              <span className="thd-breakdown-score">+{item.total_score} баллов</span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
};

export default TeacherHeatmapDetail;
