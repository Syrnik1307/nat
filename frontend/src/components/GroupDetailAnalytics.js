import React, { useState, useEffect, useCallback } from 'react';
import { apiClient } from '../apiService';
import GroupRatingTab from './tabs/GroupRatingTab';
import './GroupDetailAnalytics.css';

// SVG Icons
const IconCalendar = () => (
    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
        <rect x="3" y="4" width="18" height="18" rx="2" ry="2"/>
        <line x1="16" y1="2" x2="16" y2="6"/>
        <line x1="8" y1="2" x2="8" y2="6"/>
        <line x1="3" y1="10" x2="21" y2="10"/>
    </svg>
);

const IconBook = () => (
    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
        <path d="M4 19.5A2.5 2.5 0 0 1 6.5 17H20"/>
        <path d="M6.5 2H20v20H6.5A2.5 2.5 0 0 1 4 19.5v-15A2.5 2.5 0 0 1 6.5 2z"/>
    </svg>
);

const IconAlert = () => (
    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
        <circle cx="12" cy="12" r="10"/>
        <line x1="12" y1="8" x2="12" y2="12"/>
        <line x1="12" y1="16" x2="12.01" y2="16"/>
    </svg>
);

const IconUsers = () => (
    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
        <path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"/>
        <circle cx="9" cy="7" r="4"/>
        <path d="M23 21v-2a4 4 0 0 0-3-3.87"/>
        <path d="M16 3.13a4 4 0 0 1 0 7.75"/>
    </svg>
);

const IconOverview = () => (
    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
        <rect x="3" y="3" width="7" height="7" rx="1" />
        <rect x="14" y="3" width="7" height="7" rx="1" />
        <rect x="3" y="14" width="7" height="7" rx="1" />
        <rect x="14" y="14" width="7" height="7" rx="1" />
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

const IconClock = () => (
    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
        <circle cx="12" cy="12" r="10"/>
        <polyline points="12 6 12 12 16 14"/>
    </svg>
);

const TABS = [
    { id: 'overview', label: 'Обзор', Icon: IconOverview },
    { id: 'homework', label: 'Домашние задания', Icon: IconBook },
    { id: 'students', label: 'Ученики', Icon: IconUsers },
    { id: 'rating', label: 'Рейтинг', Icon: IconTrophy },
];

function StatCard({ title, value, subtitle, icon: Icon, color, variant }) {
    return (
        <div className={`gd-stat-card ${variant ? `gd-stat-card--${variant}` : ''}`} style={{ borderLeftColor: color }}>
            <div className="gd-stat-header">
                {Icon && <span className="gd-stat-icon" style={{ color }}><Icon /></span>}
                <span className="gd-stat-title">{title}</span>
            </div>
            <div className="gd-stat-value">{value}</div>
            {subtitle && <div className="gd-stat-subtitle">{subtitle}</div>}
        </div>
    );
}

function ProgressBar({ percent, color }) {
    return (
        <div className="gd-progress-bar">
            <div 
                className="gd-progress-fill" 
                style={{ width: `${percent || 0}%`, backgroundColor: color }}
            />
        </div>
    );
}

function GroupDetailAnalytics({ groupId }) {
    const [activeTab, setActiveTab] = useState('overview');
    const [summary, setSummary] = useState(null);
    const [homeworkData, setHomeworkData] = useState(null);
    const [studentsData, setStudentsData] = useState(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);

    const loadSummary = useCallback(async () => {
        try {
            const res = await apiClient.get(`/group-detail/${groupId}/`);
            setSummary(res.data);
        } catch (err) {
            console.error('Failed to load group summary:', err);
            setError(err.response?.data?.detail || 'Ошибка загрузки данных');
        }
    }, [groupId]);

    const loadHomework = useCallback(async () => {
        try {
            const res = await apiClient.get(`/group-detail/${groupId}/homework/`);
            setHomeworkData(res.data);
        } catch (err) {
            console.error('Failed to load homework data:', err);
        }
    }, [groupId]);

    const loadStudents = useCallback(async () => {
        try {
            const res = await apiClient.get(`/group-detail/${groupId}/students/`);
            setStudentsData(res.data);
        } catch (err) {
            console.error('Failed to load students data:', err);
        }
    }, [groupId]);

    useEffect(() => {
        const loadAll = async () => {
            setLoading(true);
            setError(null);
            await Promise.all([
                loadSummary(),
                loadHomework(),
                loadStudents(),
            ]);
            setLoading(false);
        };
        loadAll();
    }, [loadSummary, loadHomework, loadStudents]);

    if (loading) {
        return (
            <div className="gd-loading">
                <div className="gd-spinner"></div>
                <span>Загрузка аналитики группы...</span>
            </div>
        );
    }

    if (error) {
        return (
            <div className="gd-error">
                <span>{error}</span>
                <button onClick={() => window.location.reload()}>Повторить</button>
            </div>
        );
    }

    if (!summary) {
        return <div className="gd-empty">Нет данных</div>;
    }

    const getPercentColor = (percent) => {
        if (percent == null) return '#94a3b8';
        if (percent >= 80) return '#16a34a';
        if (percent >= 60) return '#ca8a04';
        return '#dc2626';
    };

    const renderOverview = () => (
        <div className="gd-overview">
            <div className="gd-group-header">
                <h2>{summary.group_name}</h2>
                {summary.teacher_name && (
                    <span className="gd-teacher">Преподаватель: {summary.teacher_name}</span>
                )}
            </div>

            <div className="gd-stats-grid">
                <StatCard
                    title="Учеников"
                    value={summary.students_count}
                    icon={IconUsers}
                    color="#4f46e5"
                />
                <StatCard
                    title="Посещаемость"
                    value={summary.attendance?.percent != null ? `${summary.attendance.percent}%` : '—'}
                    subtitle={`${summary.attendance?.present || 0} из ${summary.attendance?.total || 0} отметок`}
                    icon={IconCalendar}
                    color={getPercentColor(summary.attendance?.percent)}
                />
                <StatCard
                    title="Выполнение ДЗ"
                    value={summary.homework?.percent != null ? `${summary.homework.percent}%` : '—'}
                    subtitle={`${summary.homework?.completed || 0} из ${summary.homework?.total || 0} сдач`}
                    icon={IconBook}
                    color={getPercentColor(summary.homework?.percent)}
                />
                <StatCard
                    title="Ошибки в ДЗ"
                    value={summary.errors?.error_rate != null ? `${summary.errors.error_rate}%` : '—'}
                    subtitle={`${summary.errors?.total_incorrect || 0} ошибок из ${summary.errors?.total_answers || 0} ответов`}
                    icon={IconAlert}
                    color={summary.errors?.error_rate > 30 ? '#dc2626' : summary.errors?.error_rate > 15 ? '#ca8a04' : '#16a34a'}
                />
            </div>

            {/* Быстрая сводка по ДЗ */}
            {homeworkData?.homeworks?.length > 0 && (
                <div className="gd-section">
                    <h3>Последние домашние задания</h3>
                    <div className="gd-hw-list">
                        {homeworkData.homeworks.slice(0, 5).map(hw => (
                            <div key={hw.homework_id} className="gd-hw-item">
                                <div className="gd-hw-info">
                                    <span className="gd-hw-title">{hw.title}</span>
                                    <span className="gd-hw-date">{hw.created_at}</span>
                                </div>
                                <div className="gd-hw-stats">
                                    <span className="gd-hw-stat">
                                        <strong>{hw.submission_rate || 0}%</strong> сдали
                                    </span>
                                    {hw.error_rate != null && (
                                        <span className={`gd-hw-stat ${hw.error_rate > 30 ? 'gd-hw-stat--bad' : ''}`}>
                                            <strong>{hw.error_rate}%</strong> ошибок
                                        </span>
                                    )}
                                </div>
                            </div>
                        ))}
                    </div>
                </div>
            )}
        </div>
    );

    const renderHomework = () => (
        <div className="gd-homework">
            <div className="gd-section-header">
                <h3>Статистика по домашним заданиям</h3>
            </div>

            {homeworkData?.homeworks?.length > 0 ? (
                <div className="gd-table-wrapper">
                    <table className="gd-table">
                        <thead>
                            <tr>
                                <th>Название</th>
                                <th>Дата</th>
                                <th>Дедлайн</th>
                                <th>Сдали</th>
                                <th>Правильно</th>
                                <th>Ошибки</th>
                                <th>Ср. время</th>
                            </tr>
                        </thead>
                        <tbody>
                            {homeworkData.homeworks.map(hw => (
                                <tr key={hw.homework_id}>
                                    <td className="gd-cell-title">{hw.title}</td>
                                    <td className="gd-cell-date">{hw.created_at}</td>
                                    <td className="gd-cell-date">{hw.deadline || '—'}</td>
                                    <td>
                                        <div className="gd-cell-progress">
                                            <span>{hw.submitted_count}/{hw.students_count}</span>
                                            <ProgressBar 
                                                percent={hw.submission_rate} 
                                                color={getPercentColor(hw.submission_rate)}
                                            />
                                        </div>
                                    </td>
                                    <td className="gd-cell-number gd-cell-correct">{hw.correct_count}</td>
                                    <td className={`gd-cell-number ${hw.error_rate > 30 ? 'gd-cell-error' : ''}`}>
                                        {hw.incorrect_count} ({hw.error_rate || 0}%)
                                    </td>
                                    <td className="gd-cell-number">
                                        {hw.avg_time_minutes ? `${hw.avg_time_minutes} мин` : '—'}
                                    </td>
                                </tr>
                            ))}
                        </tbody>
                    </table>
                </div>
            ) : (
                <div className="gd-empty-state">Нет домашних заданий</div>
            )}
        </div>
    );

    const renderStudents = () => (
        <div className="gd-students">
            <div className="gd-section-header">
                <h3>Статистика по ученикам</h3>
            </div>

            {studentsData?.students?.length > 0 ? (
                <div className="gd-table-wrapper">
                    <table className="gd-table">
                        <thead>
                            <tr>
                                <th>Ученик</th>
                                <th>Посещаемость</th>
                                <th>Выполнение ДЗ</th>
                                <th>Правильно</th>
                                <th>Ошибки</th>
                                <th>% ошибок</th>
                            </tr>
                        </thead>
                        <tbody>
                            {studentsData.students.map(st => (
                                <tr key={st.student_id}>
                                    <td>
                                        <div className="gd-cell-student">
                                            <span className="gd-avatar">
                                                {(st.student_name?.[0] || '?').toUpperCase()}
                                            </span>
                                            <div className="gd-student-info">
                                                <span className="gd-student-name">{st.student_name}</span>
                                                <span className="gd-student-email">{st.email}</span>
                                            </div>
                                        </div>
                                    </td>
                                    <td>
                                        <div className="gd-cell-progress">
                                            <span style={{ color: getPercentColor(st.attendance_percent) }}>
                                                {st.attendance_percent != null ? `${st.attendance_percent}%` : '—'}
                                            </span>
                                            <ProgressBar 
                                                percent={st.attendance_percent} 
                                                color={getPercentColor(st.attendance_percent)}
                                            />
                                        </div>
                                    </td>
                                    <td>
                                        <div className="gd-cell-progress">
                                            <span style={{ color: getPercentColor(st.homework_percent) }}>
                                                {st.homework_percent != null ? `${st.homework_percent}%` : '—'}
                                            </span>
                                            <ProgressBar 
                                                percent={st.homework_percent} 
                                                color={getPercentColor(st.homework_percent)}
                                            />
                                        </div>
                                    </td>
                                    <td className="gd-cell-number gd-cell-correct">{st.correct_count}</td>
                                    <td className="gd-cell-number">{st.incorrect_count}</td>
                                    <td className={`gd-cell-number ${st.error_rate > 30 ? 'gd-cell-error' : ''}`}>
                                        {st.error_rate != null ? `${st.error_rate}%` : '—'}
                                    </td>
                                </tr>
                            ))}
                        </tbody>
                    </table>
                </div>
            ) : (
                <div className="gd-empty-state">Нет учеников в группе</div>
            )}
        </div>
    );

    return (
        <div className="group-detail-analytics">
            <div className="gd-header">
                <h1>{summary.group_name}</h1>
                <span className="gd-subtitle">Аналитика группы</span>
            </div>

            <div className="gd-tabs">
                {TABS.map(tab => (
                    <button
                        key={tab.id}
                        className={`gd-tab ${activeTab === tab.id ? 'gd-tab--active' : ''}`}
                        onClick={() => setActiveTab(tab.id)}
                    >
                        <tab.Icon />
                        <span>{tab.label}</span>
                    </button>
                ))}
            </div>

            <div className="gd-content">
                {activeTab === 'overview' && renderOverview()}
                {activeTab === 'homework' && renderHomework()}
                {activeTab === 'students' && renderStudents()}
                {activeTab === 'rating' && (
                    <GroupRatingTab groupId={groupId} />
                )}
            </div>
        </div>
    );
}

export default GroupDetailAnalytics;
