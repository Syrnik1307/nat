import React, { useState, useEffect, useCallback, useMemo, useRef } from 'react';
import { apiClient } from '../../apiService';
import HeatmapSkeleton from './HeatmapSkeleton';
import ActivityDayModal from './ActivityDayModal';
import './ActivityHeatmap.css';

// SVG Icons
const IconFlame = () => (
    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
        <path d="M8.5 14.5A2.5 2.5 0 0 0 11 12c0-1.38-.5-2-1-3-1.072-2.143-.224-4.054 2-6 .5 2.5 2 4.9 4 6.5 2 1.6 3 3.5 3 5.5a7 7 0 1 1-14 0c0-1.153.433-2.294 1-3a2.5 2.5 0 0 0 2.5 2.5z"/>
    </svg>
);

const IconTrophy = () => (
    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
        <path d="M6 9H4.5a2.5 2.5 0 0 1 0-5H6"/>
        <path d="M18 9h1.5a2.5 2.5 0 0 0 0-5H18"/>
        <path d="M4 22h16"/>
        <path d="M10 14.66V17c0 .55-.47.98-.97 1.21C7.85 18.75 7 20.24 7 22"/>
        <path d="M14 14.66V17c0 .55.47.98.97 1.21C16.15 18.75 17 20.24 17 22"/>
        <path d="M18 2H6v7a6 6 0 0 0 12 0V2Z"/>
    </svg>
);

const IconCalendarDays = () => (
    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
        <rect x="3" y="4" width="18" height="18" rx="2" ry="2"/>
        <line x1="16" y1="2" x2="16" y2="6"/>
        <line x1="8" y1="2" x2="8" y2="6"/>
        <line x1="3" y1="10" x2="21" y2="10"/>
        <path d="M8 14h.01"/>
        <path d="M12 14h.01"/>
        <path d="M16 14h.01"/>
        <path d="M8 18h.01"/>
        <path d="M12 18h.01"/>
        <path d="M16 18h.01"/>
    </svg>
);

const IconTrendUp = () => (
    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
        <polyline points="23 6 13.5 15.5 8.5 10.5 1 18"/>
        <polyline points="17 6 23 6 23 12"/>
    </svg>
);

const MONTHS_RU = ['Янв', 'Фев', 'Мар', 'Апр', 'Май', 'Июн', 'Июл', 'Авг', 'Сен', 'Окт', 'Ноя', 'Дек'];
const WEEKDAYS_RU = ['Пн', '', 'Ср', '', 'Пт', '', ''];

const PERIOD_OPTIONS = [
    { value: 365, label: 'Год' },
    { value: 180, label: '6 мес' },
    { value: 90, label: '3 мес' },
];

/**
 * ActivityHeatmap - GitHub-style карта активности студента
 * 
 * @param {number} studentId - ID студента (для учителей)
 * @param {boolean} isOwnProfile - Показывать свой профиль (для студентов)
 */
function ActivityHeatmap({ studentId, isOwnProfile = false }) {
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);
    const [data, setData] = useState(null);
    const [period, setPeriod] = useState(365);
    const [selectedDay, setSelectedDay] = useState(null);
    const [dayActivities, setDayActivities] = useState([]);
    const [isAnimated, setIsAnimated] = useState(false);
    const containerRef = useRef(null);
    
    // Загрузка данных
    const loadHeatmapData = useCallback(async () => {
        try {
            setLoading(true);
            setError(null);
            
            let url = '/analytics/heatmap/my/';
            if (studentId && !isOwnProfile) {
                url = `/analytics/heatmap/student/${studentId}/`;
            }
            
            const res = await apiClient.get(url);
            setData(res.data);
            
            // Запускаем анимацию появления после загрузки
            setTimeout(() => setIsAnimated(true), 50);
        } catch (err) {
            console.error('Failed to load heatmap:', err);
            setError(err.response?.data?.detail || 'Не удалось загрузить данные');
        } finally {
            setLoading(false);
        }
    }, [studentId, isOwnProfile]);
    
    useEffect(() => {
        loadHeatmapData();
    }, [loadHeatmapData]);
    
    // Фильтрация данных по периоду
    const filteredData = useMemo(() => {
        if (!data?.heatmap_data) return [];
        
        const today = new Date();
        const startDate = new Date(today);
        startDate.setDate(startDate.getDate() - period);
        
        return data.heatmap_data.filter(day => {
            const dayDate = new Date(day.date);
            return dayDate >= startDate && dayDate <= today;
        });
    }, [data, period]);
    
    // Группировка по неделям для отображения
    const gridData = useMemo(() => {
        if (filteredData.length === 0) return { columns: [], months: [] };
        
        const columns = [];
        const months = [];
        let currentColumn = [];
        let lastMonth = -1;
        
        // Определяем день недели первого дня
        const firstDay = new Date(filteredData[0]?.date);
        const startDayOfWeek = firstDay.getDay() === 0 ? 6 : firstDay.getDay() - 1; // Пн = 0
        
        // Добавляем пустые ячейки в начало
        for (let i = 0; i < startDayOfWeek; i++) {
            currentColumn.push({ empty: true });
        }
        
        filteredData.forEach((day, index) => {
            const date = new Date(day.date);
            const dayOfWeek = date.getDay() === 0 ? 6 : date.getDay() - 1; // Пн = 0
            const month = date.getMonth();
            
            // Отслеживаем смену месяца
            if (month !== lastMonth) {
                months.push({
                    label: MONTHS_RU[month],
                    position: columns.length,
                });
                lastMonth = month;
            }
            
            // Новая колонка каждый понедельник
            if (dayOfWeek === 0 && currentColumn.length > 0) {
                columns.push(currentColumn);
                currentColumn = [];
            }
            
            currentColumn.push({
                ...day,
                isToday: day.date === new Date().toISOString().split('T')[0],
            });
        });
        
        // Добавляем последнюю колонку
        if (currentColumn.length > 0) {
            columns.push(currentColumn);
        }
        
        return { columns, months };
    }, [filteredData]);
    
    // Вычисляем ширину месяца
    const monthPositions = useMemo(() => {
        const { columns, months } = gridData;
        if (months.length === 0) return [];
        
        return months.map((month, idx) => {
            const nextMonth = months[idx + 1];
            const width = nextMonth 
                ? (nextMonth.position - month.position) * 14 // 11px cell + 3px gap
                : (columns.length - month.position) * 14;
            return {
                ...month,
                width: Math.max(width, 28),
            };
        });
    }, [gridData]);
    
    // Клик по ячейке
    const handleCellClick = useCallback(async (day) => {
        if (day.empty || day.count === 0) return;
        
        setSelectedDay(day);
        
        // TODO: Загрузка детальной информации о дне с бекенда
        // Пока используем mock данные на основе breakdown
        const mockActivities = [];
        
        if (data?.event_breakdown) {
            // Создаём примерные активности на основе общей статистики
            data.event_breakdown.forEach(event => {
                if (event.count > 0) {
                    mockActivities.push({
                        action_type: event.action_type,
                        count: 1,
                    });
                }
            });
        }
        
        setDayActivities(mockActivities);
    }, [data]);
    
    // Закрытие модалки
    const handleCloseModal = useCallback(() => {
        setSelectedDay(null);
        setDayActivities([]);
    }, []);
    
    // Рендер статистики
    const renderStats = () => {
        if (!data?.stats) return null;
        
        const { stats } = data;
        
        return (
            <div className="heatmap-stats">
                <div className="heatmap-stat-card">
                    <div className="heatmap-stat-card__icon heatmap-stat-card__icon--streak">
                        <IconFlame />
                    </div>
                    <div className="heatmap-stat-card__value">{stats.current_streak}</div>
                    <div className="heatmap-stat-card__label">Текущая серия</div>
                    <div className="heatmap-stat-card__sublabel">дней подряд</div>
                </div>
                
                <div className="heatmap-stat-card">
                    <div className="heatmap-stat-card__icon heatmap-stat-card__icon--total">
                        <IconTrophy />
                    </div>
                    <div className="heatmap-stat-card__value">{stats.longest_streak}</div>
                    <div className="heatmap-stat-card__label">Рекорд</div>
                    <div className="heatmap-stat-card__sublabel">дней подряд</div>
                </div>
                
                <div className="heatmap-stat-card">
                    <div className="heatmap-stat-card__icon heatmap-stat-card__icon--days">
                        <IconCalendarDays />
                    </div>
                    <div className="heatmap-stat-card__value">{stats.days_active}</div>
                    <div className="heatmap-stat-card__label">Активных дней</div>
                    <div className="heatmap-stat-card__sublabel">за период</div>
                </div>
                
                <div className="heatmap-stat-card">
                    <div className="heatmap-stat-card__icon heatmap-stat-card__icon--avg">
                        <IconTrendUp />
                    </div>
                    <div className="heatmap-stat-card__value">{stats.total_contributions}</div>
                    <div className="heatmap-stat-card__label">Всего баллов</div>
                    <div className="heatmap-stat-card__sublabel">
                        ~{stats.avg_daily_score} в день
                    </div>
                </div>
            </div>
        );
    };
    
    // Рендер breakdown по типам
    const renderBreakdown = () => {
        if (!data?.event_breakdown || data.event_breakdown.length === 0) return null;
        
        const maxScore = Math.max(...data.event_breakdown.map(e => e.total_score || 0));
        
        return (
            <div className="heatmap-breakdown">
                <h3 className="heatmap-breakdown__title">Активность по типам</h3>
                <div className="heatmap-breakdown__list">
                    {data.event_breakdown.map(event => (
                        <div key={event.action_type} className="heatmap-breakdown__item">
                            <div className="heatmap-breakdown__label">{event.label}</div>
                            <div className="heatmap-breakdown__bar-wrapper">
                                <div 
                                    className="heatmap-breakdown__bar"
                                    style={{ 
                                        width: `${maxScore > 0 ? (event.total_score / maxScore) * 100 : 0}%` 
                                    }}
                                />
                            </div>
                            <div className="heatmap-breakdown__value">
                                {event.count} ({event.total_score})
                            </div>
                        </div>
                    ))}
                </div>
            </div>
        );
    };
    
    // Loading state
    if (loading) {
        return (
            <div className="activity-heatmap">
                <div className="activity-heatmap__header">
                    <h2 className="activity-heatmap__title">Карта активности</h2>
                </div>
                <HeatmapSkeleton />
            </div>
        );
    }
    
    // Error state
    if (error) {
        return (
            <div className="activity-heatmap">
                <div className="sd-error">
                    <span>{error}</span>
                    <button onClick={loadHeatmapData}>Повторить</button>
                </div>
            </div>
        );
    }
    
    return (
        <div className="activity-heatmap">
            <div className="activity-heatmap__header">
                <h2 className="activity-heatmap__title">Карта активности</h2>
                
                <div className="activity-heatmap__period-selector">
                    {PERIOD_OPTIONS.map(opt => (
                        <button
                            key={opt.value}
                            className={`activity-heatmap__period-btn ${
                                period === opt.value ? 'activity-heatmap__period-btn--active' : ''
                            }`}
                            onClick={() => setPeriod(opt.value)}
                        >
                            {opt.label}
                        </button>
                    ))}
                </div>
            </div>
            
            {/* Heatmap Grid */}
            <div 
                ref={containerRef}
                className={`heatmap-container ${isAnimated ? 'heatmap-enter-active' : 'heatmap-enter'}`}
            >
                <div className="heatmap-grid-wrapper">
                    {/* Month labels */}
                    <div className="heatmap-months">
                        {monthPositions.map((month, idx) => (
                            <span 
                                key={idx}
                                className="heatmap-month-label"
                                style={{ width: month.width }}
                            >
                                {month.label}
                            </span>
                        ))}
                    </div>
                    
                    <div className="heatmap-body">
                        {/* Weekday labels */}
                        <div className="heatmap-weekdays">
                            {WEEKDAYS_RU.map((day, idx) => (
                                <span key={idx} className="heatmap-weekday-label">{day}</span>
                            ))}
                        </div>
                        
                        {/* Grid columns */}
                        <div className="heatmap-columns">
                            {gridData.columns.map((column, colIdx) => (
                                <div key={colIdx} className="heatmap-column">
                                    {column.map((day, rowIdx) => (
                                        <div
                                            key={rowIdx}
                                            className={`heatmap-cell 
                                                heatmap-cell--level-${day.empty ? 'empty' : day.level}
                                                ${day.empty ? 'heatmap-cell--empty' : ''}
                                                ${day.isToday ? 'heatmap-cell--today' : ''}
                                                ${selectedDay?.date === day.date ? 'heatmap-cell--selected' : ''}
                                            `}
                                            onClick={() => handleCellClick(day)}
                                            title={day.empty ? '' : `${day.date}: ${day.count} баллов`}
                                        />
                                    ))}
                                </div>
                            ))}
                        </div>
                    </div>
                </div>
            </div>
            
            {/* Legend */}
            <div className="heatmap-legend">
                <span className="heatmap-legend-label">Меньше</span>
                <div className="heatmap-legend-cells">
                    {[0, 1, 2, 3, 4].map(level => (
                        <div 
                            key={level} 
                            className={`heatmap-legend-cell heatmap-cell--level-${level}`}
                        />
                    ))}
                </div>
                <span className="heatmap-legend-label">Больше</span>
            </div>
            
            {/* Stats cards */}
            {renderStats()}
            
            {/* Breakdown by event type */}
            {renderBreakdown()}
            
            {/* Day detail modal */}
            <ActivityDayModal
                isOpen={!!selectedDay}
                onClose={handleCloseModal}
                dayData={selectedDay}
                activities={dayActivities}
            />
        </div>
    );
}

export default ActivityHeatmap;
