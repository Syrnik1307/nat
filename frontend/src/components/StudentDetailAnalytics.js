import React, { useState, useEffect, useCallback } from 'react';
import { apiClient } from '../apiService';
import { getSubjects, getStudentProgress } from '../knowledgeMapService';
import './StudentDetailAnalytics.css';
import ActivityHeatmap from './ActivityHeatmap';

// SVG Icons - чистые иконки без эмодзи
const IconCalendar = () => (
    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
        <rect x="3" y="4" width="18" height="18" rx="2" ry="2"/>
        <line x1="16" y1="2" x2="16" y2="6"/>
        <line x1="8" y1="2" x2="8" y2="6"/>
        <line x1="3" y1="10" x2="21" y2="10"/>
    </svg>
);

const IconMic = () => (
    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
        <path d="M12 1a3 3 0 0 0-3 3v8a3 3 0 0 0 6 0V4a3 3 0 0 0-3-3z"/>
        <path d="M19 10v2a7 7 0 0 1-14 0v-2"/>
        <line x1="12" y1="19" x2="12" y2="23"/>
        <line x1="8" y1="23" x2="16" y2="23"/>
    </svg>
);

const IconBook = () => (
    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
        <path d="M4 19.5A2.5 2.5 0 0 1 6.5 17H20"/>
        <path d="M6.5 2H20v20H6.5A2.5 2.5 0 0 1 4 19.5v-15A2.5 2.5 0 0 1 6.5 2z"/>
    </svg>
);

const IconCheck = () => (
    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="3">
        <polyline points="20 6 9 17 4 12"/>
    </svg>
);

const IconX = () => (
    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="3">
        <line x1="18" y1="6" x2="6" y2="18"/>
        <line x1="6" y1="6" x2="18" y2="18"/>
    </svg>
);

const IconUser = () => (
    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
        <path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"/>
        <circle cx="12" cy="7" r="4"/>
    </svg>
);

const IconTrendUp = () => (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
        <polyline points="23 6 13.5 15.5 8.5 10.5 1 18"/>
        <polyline points="17 6 23 6 23 12"/>
    </svg>
);

const IconMail = () => (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
        <path d="M4 4h16c1.1 0 2 .9 2 2v12c0 1.1-.9 2-2 2H4c-1.1 0-2-.9-2-2V6c0-1.1.9-2 2-2z"/>
        <polyline points="22,6 12,13 2,6"/>
    </svg>
);

const IconActivity = () => (
    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
        <rect x="3" y="3" width="7" height="7" rx="1"/>
        <rect x="14" y="3" width="7" height="7" rx="1"/>
        <rect x="3" y="14" width="7" height="7" rx="1"/>
        <rect x="14" y="14" width="7" height="7" rx="1"/>
    </svg>
);

const IconBrain = () => (
    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
        <path d="M12 2a4 4 0 0 0-4 4v1H6a4 4 0 0 0-1 7.9V16a4 4 0 0 0 4 4h6a4 4 0 0 0 4-4v-1.1A4 4 0 0 0 18 7h-2V6a4 4 0 0 0-4-4z"/>
        <path d="M12 2v20"/>
        <path d="M8 10h0"/>
        <path d="M16 10h0"/>
    </svg>
);

const IconChevronRight = () => (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
        <polyline points="9 18 15 12 9 6"/>
    </svg>
);

const IconChevronDown = () => (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
        <polyline points="6 9 12 15 18 9"/>
    </svg>
);

const TABS = [
    { id: 'overview', label: 'Обзор', Icon: IconUser },
    { id: 'attendance', label: 'Посещаемость', Icon: IconCalendar },
    { id: 'participation', label: 'Участие', Icon: IconMic },
    { id: 'homework', label: 'Домашние задания', Icon: IconBook },
    { id: 'activity', label: 'Карта активности', Icon: IconActivity },
    { id: 'knowledge', label: 'Карта знаний', Icon: IconBrain },
];

function StatCard({ title, value, subtitle, icon: Icon, color, trend }) {
    return (
        <div className="sd-stat-card" style={{ borderLeftColor: color }}>
            <div className="sd-stat-header">
                {Icon && <span className="sd-stat-icon" style={{ color }}><Icon /></span>}
                <span className="sd-stat-title">{title}</span>
            </div>
            <div className="sd-stat-value">
                {value}
                {trend && <span className="sd-stat-trend"><IconTrendUp /></span>}
            </div>
            {subtitle && <div className="sd-stat-subtitle">{subtitle}</div>}
        </div>
    );
}

function StatusBadge({ status, label }) {
    const statusColors = {
        present: { bg: '#dcfce7', color: '#166534' },
        absent: { bg: '#fee2e2', color: '#991b1b' },
        excused: { bg: '#fef3c7', color: '#92400e' },
        not_marked: { bg: '#f1f5f9', color: '#64748b' },
        submitted: { bg: '#dbeafe', color: '#1e40af' },
        graded: { bg: '#dcfce7', color: '#166534' },
        in_progress: { bg: '#fef3c7', color: '#92400e' },
        not_started: { bg: '#f1f5f9', color: '#64748b' },
    };
    
    const style = statusColors[status] || statusColors.not_marked;
    
    return (
        <span 
            className="sd-status-badge" 
            style={{ backgroundColor: style.bg, color: style.color }}
        >
            {label}
        </span>
    );
}

function StudentDetailAnalytics({ studentId, groupId, onBack }) {
    const [activeTab, setActiveTab] = useState('overview');
    const [summary, setSummary] = useState(null);
    const [attendance, setAttendance] = useState(null);
    const [participation, setParticipation] = useState(null);
    const [homework, setHomework] = useState(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);

    // Knowledge map state
    const [knowledgeSubjects, setKnowledgeSubjects] = useState([]);
    const [selectedKnowledgeSubject, setSelectedKnowledgeSubject] = useState(null);
    const [knowledgeProgress, setKnowledgeProgress] = useState(null);
    const [knowledgeLoading, setKnowledgeLoading] = useState(false);
    const [expandedSections, setExpandedSections] = useState({});

    const loadSummary = useCallback(async () => {
        try {
            const params = groupId ? `?group_id=${groupId}` : '';
            const res = await apiClient.get(`/student-detail/${studentId}/${params}`);
            setSummary(res.data);
        } catch (err) {
            console.error('Failed to load summary:', err);
            setError(err.response?.data?.detail || 'Ошибка загрузки данных');
        }
    }, [studentId, groupId]);

    const loadAttendance = useCallback(async () => {
        try {
            const params = groupId ? `?group_id=${groupId}` : '';
            const res = await apiClient.get(`/student-detail/${studentId}/attendance/${params}`);
            setAttendance(res.data);
        } catch (err) {
            console.error('Failed to load attendance:', err);
        }
    }, [studentId, groupId]);

    const loadParticipation = useCallback(async () => {
        try {
            const params = groupId ? `?group_id=${groupId}` : '';
            const res = await apiClient.get(`/student-detail/${studentId}/participation/${params}`);
            setParticipation(res.data);
        } catch (err) {
            console.error('Failed to load participation:', err);
        }
    }, [studentId, groupId]);

    const loadHomework = useCallback(async () => {
        try {
            const params = groupId ? `?group_id=${groupId}` : '';
            const res = await apiClient.get(`/student-detail/${studentId}/homework/${params}`);
            setHomework(res.data);
        } catch (err) {
            console.error('Failed to load homework:', err);
        }
    }, [studentId, groupId]);

    useEffect(() => {
        const loadAll = async () => {
            setLoading(true);
            setError(null);
            await Promise.all([
                loadSummary(),
                loadAttendance(),
                loadParticipation(),
                loadHomework(),
            ]);
            setLoading(false);
        };
        loadAll();
    }, [loadSummary, loadAttendance, loadParticipation, loadHomework]);

    if (loading) {
        return (
            <div className="sd-loading">
                <div className="sd-spinner"></div>
                <span>Загрузка аналитики...</span>
            </div>
        );
    }

    if (error) {
        return (
            <div className="sd-error">
                <span>{error}</span>
                <button onClick={() => window.location.reload()}>Повторить</button>
            </div>
        );
    }

    if (!summary) {
        return <div className="sd-empty">Нет данных</div>;
    }

    const renderOverview = () => (
        <div className="sd-overview">
            <div className="sd-student-info">
                <div className="sd-avatar">
                    {(summary.student_name?.[0] || '?').toUpperCase()}
                </div>
                <div className="sd-info">
                    <h2>{summary.student_name}</h2>
                    <div className="sd-email">
                        <IconMail />
                        <span>{summary.email}</span>
                    </div>
                    {summary.groups?.length > 0 && (
                        <div className="sd-groups">
                            {summary.groups.map(g => (
                                <span key={g.id} className="sd-group-tag">{g.name}</span>
                            ))}
                        </div>
                    )}
                </div>
            </div>

            <div className="sd-stats-grid">
                <StatCard
                    title="Посещаемость"
                    value={summary.attendance?.percent != null ? `${summary.attendance.percent}%` : '—'}
                    subtitle={`${summary.attendance?.present || 0} из ${summary.attendance?.total || 0} занятий`}
                    icon={IconCalendar}
                    color={
                        (summary.attendance?.percent || 0) >= 80 ? '#16a34a' :
                        (summary.attendance?.percent || 0) >= 60 ? '#ca8a04' : '#dc2626'
                    }
                />
                <StatCard
                    title="Домашние задания"
                    value={summary.homework?.percent != null ? `${summary.homework.percent}%` : '—'}
                    subtitle={`${summary.homework?.completed || 0} из ${summary.homework?.total || 0} выполнено`}
                    icon={IconBook}
                    color={
                        (summary.homework?.percent || 0) >= 80 ? '#16a34a' :
                        (summary.homework?.percent || 0) >= 60 ? '#ca8a04' : '#dc2626'
                    }
                />
                <StatCard
                    title="Упоминания на уроках"
                    value={summary.participation?.mentions || 0}
                    subtitle="раз вызывали на уроках"
                    icon={IconMic}
                    color="#4f46e5"
                />
                <StatCard
                    title="Время речи"
                    value={`${summary.participation?.talk_time_minutes || 0} мин`}
                    subtitle="общее время выступлений"
                    icon={IconTrendUp}
                    color="#0891b2"
                />
            </div>

            {/* Быстрая сводка по посещаемости */}
            {attendance?.lessons?.length > 0 && (
                <div className="sd-quick-section">
                    <h3>Последние занятия</h3>
                    <div className="sd-quick-list">
                        {attendance.lessons.slice(0, 5).map(lesson => (
                            <div key={lesson.lesson_id} className="sd-quick-item">
                                <span className="sd-quick-date">{lesson.date}</span>
                                <span className="sd-quick-title">{lesson.title}</span>
                                <StatusBadge status={lesson.status} label={lesson.status_display} />
                            </div>
                        ))}
                    </div>
                </div>
            )}
        </div>
    );

    const renderAttendance = () => (
        <div className="sd-attendance">
            <div className="sd-section-header">
                <h3>Посещаемость занятий</h3>
                <div className="sd-legend">
                    <span className="sd-legend-item">
                        <span className="sd-legend-dot sd-legend-present"></span>
                        Присутствовал
                    </span>
                    <span className="sd-legend-item">
                        <span className="sd-legend-dot sd-legend-absent"></span>
                        Отсутствовал
                    </span>
                    <span className="sd-legend-item">
                        <span className="sd-legend-dot sd-legend-excused"></span>
                        Уважительная причина
                    </span>
                </div>
            </div>

            {attendance?.lessons?.length > 0 ? (
                <div className="sd-table-wrapper">
                    <table className="sd-table">
                        <thead>
                            <tr>
                                <th>Дата</th>
                                <th>Занятие</th>
                                <th>Группа</th>
                                <th>Статус</th>
                            </tr>
                        </thead>
                        <tbody>
                            {attendance.lessons.map(lesson => (
                                <tr key={lesson.lesson_id}>
                                    <td className="sd-cell-date">
                                        <span className="sd-date">{lesson.date}</span>
                                        <span className="sd-time">{lesson.time}</span>
                                    </td>
                                    <td className="sd-cell-title">{lesson.title}</td>
                                    <td className="sd-cell-group">{lesson.group_name}</td>
                                    <td>
                                        <StatusBadge status={lesson.status} label={lesson.status_display} />
                                    </td>
                                </tr>
                            ))}
                        </tbody>
                    </table>
                </div>
            ) : (
                <div className="sd-empty-state">Нет данных о посещаемости</div>
            )}
        </div>
    );

    const renderParticipation = () => (
        <div className="sd-participation">
            <div className="sd-section-header">
                <h3>Участие на уроках</h3>
                <div className="sd-summary-row">
                    <div className="sd-summary-item">
                        <span className="sd-summary-value">{participation?.total_mentions || 0}</span>
                        <span className="sd-summary-label">упоминаний</span>
                    </div>
                    <div className="sd-summary-item">
                        <span className="sd-summary-value">{participation?.total_talk_time_minutes || 0}</span>
                        <span className="sd-summary-label">минут речи</span>
                    </div>
                </div>
            </div>

            {participation?.lessons?.length > 0 ? (
                <div className="sd-table-wrapper">
                    <table className="sd-table">
                        <thead>
                            <tr>
                                <th>Дата</th>
                                <th>Занятие</th>
                                <th>Упоминаний</th>
                                <th>Время речи</th>
                                <th>Участие</th>
                            </tr>
                        </thead>
                        <tbody>
                            {participation.lessons.map(lesson => (
                                <tr key={lesson.lesson_id}>
                                    <td className="sd-cell-date">{lesson.date}</td>
                                    <td className="sd-cell-title">{lesson.title}</td>
                                    <td className="sd-cell-number">{lesson.mentions_count}</td>
                                    <td className="sd-cell-number">{lesson.talk_time_minutes} мин</td>
                                    <td>
                                        {lesson.participated ? (
                                            <span className="sd-participated">
                                                <IconCheck /> Да
                                            </span>
                                        ) : (
                                            <span className="sd-not-participated">
                                                <IconX /> Нет
                                            </span>
                                        )}
                                    </td>
                                </tr>
                            ))}
                        </tbody>
                    </table>
                </div>
            ) : (
                <div className="sd-empty-state">Нет данных об участии. Возможно, транскрипции уроков еще не проанализированы.</div>
            )}
        </div>
    );

    const renderHomework = () => (
        <div className="sd-homework">
            <div className="sd-section-header">
                <h3>Домашние задания</h3>
                <div className="sd-summary-row">
                    <div className="sd-summary-item">
                        <span className="sd-summary-value">{homework?.stats?.completed || summary.homework?.completed || 0}</span>
                        <span className="sd-summary-label">выполнено</span>
                    </div>
                    <div className="sd-summary-item">
                        <span className="sd-summary-value">{homework?.stats?.on_time || 0}</span>
                        <span className="sd-summary-label">в срок</span>
                    </div>
                    <div className="sd-summary-item">
                        <span className="sd-summary-value sd-summary-value--warning">{homework?.stats?.late || 0}</span>
                        <span className="sd-summary-label">с опозданием</span>
                    </div>
                    <div className="sd-summary-item">
                        <span className="sd-summary-value">{homework?.stats?.error_rate != null ? `${homework.stats.error_rate}%` : '—'}</span>
                        <span className="sd-summary-label">ошибок</span>
                    </div>
                    <div className="sd-summary-item">
                        <span className="sd-summary-value">{homework?.stats?.avg_time_minutes ? `${homework.stats.avg_time_minutes} мин` : '—'}</span>
                        <span className="sd-summary-label">ср. время</span>
                    </div>
                </div>
            </div>

            {homework?.homeworks?.length > 0 ? (
                <div className="sd-table-wrapper">
                    <table className="sd-table">
                        <thead>
                            <tr>
                                <th>Название</th>
                                <th>Группа</th>
                                <th>Дедлайн</th>
                                <th>Статус</th>
                                <th>Правильно</th>
                                <th>Ошибки</th>
                                <th>Время</th>
                                <th>Балл</th>
                            </tr>
                        </thead>
                        <tbody>
                            {homework.homeworks.map(hw => (
                                <tr key={hw.homework_id} className={hw.is_overdue ? 'sd-row-overdue' : ''}>
                                    <td className="sd-cell-title">
                                        {hw.title}
                                        {hw.is_overdue && (
                                            <span className="sd-overdue-badge">Просрочено</span>
                                        )}
                                        {hw.on_time === false && hw.status !== 'not_started' && (
                                            <span className="sd-late-badge">Сдано поздно</span>
                                        )}
                                    </td>
                                    <td className="sd-cell-group">{hw.group_name}</td>
                                    <td className="sd-cell-date">
                                        {hw.deadline || '—'}
                                    </td>
                                    <td>
                                        <StatusBadge status={hw.status} label={hw.status_display} />
                                    </td>
                                    <td className="sd-cell-correct">
                                        {hw.total_answers > 0 ? (
                                            <span>{hw.correct_count}/{hw.total_answers}</span>
                                        ) : '—'}
                                    </td>
                                    <td className={`sd-cell-error ${hw.incorrect_count > 0 ? 'sd-cell-error--bad' : ''}`}>
                                        {hw.total_answers > 0 ? (
                                            <>
                                                <span>{hw.incorrect_count}</span>
                                                {hw.correct_rate != null && (
                                                    <span className="sd-rate-badge" style={{
                                                        backgroundColor: hw.correct_rate >= 80 ? '#dcfce7' : hw.correct_rate >= 60 ? '#fef3c7' : '#fee2e2',
                                                        color: hw.correct_rate >= 80 ? '#166534' : hw.correct_rate >= 60 ? '#92400e' : '#991b1b'
                                                    }}>
                                                        {hw.correct_rate}%
                                                    </span>
                                                )}
                                            </>
                                        ) : '—'}
                                    </td>
                                    <td className="sd-cell-time">
                                        {hw.time_spent_minutes ? `${hw.time_spent_minutes} мин` : '—'}
                                    </td>
                                    <td className="sd-cell-score">
                                        {hw.total_score != null ? hw.total_score : '—'}
                                    </td>
                                </tr>
                            ))}
                        </tbody>
                    </table>
                </div>
            ) : (
                <div className="sd-empty-state">Нет домашних заданий</div>
            )}
        </div>
    );

    return (
        <div className="student-detail-analytics">
            <div className="sd-header">
                <div className="sd-header-left">
                    <h1>{summary.student_name}</h1>
                    <span className="sd-subtitle">Детальная аналитика</span>
                </div>
            </div>

            <div className="sd-tabs">
                {TABS.map(tab => (
                    <button
                        key={tab.id}
                        className={`sd-tab ${activeTab === tab.id ? 'sd-tab--active' : ''}`}
                        onClick={() => setActiveTab(tab.id)}
                    >
                        <tab.Icon />
                        <span>{tab.label}</span>
                    </button>
                ))}
            </div>

            <div className="sd-content">
                {activeTab === 'overview' && renderOverview()}
                {activeTab === 'attendance' && renderAttendance()}
                {activeTab === 'participation' && renderParticipation()}
                {activeTab === 'homework' && renderHomework()}
                {activeTab === 'activity' && (
                    <ActivityHeatmap studentId={studentId} />
                )}
                {activeTab === 'knowledge' && (
                    <KnowledgeTreeTab
                        studentId={studentId}
                        subjects={knowledgeSubjects}
                        setSubjects={setKnowledgeSubjects}
                        selectedSubject={selectedKnowledgeSubject}
                        setSelectedSubject={setSelectedKnowledgeSubject}
                        progress={knowledgeProgress}
                        setProgress={setKnowledgeProgress}
                        loading={knowledgeLoading}
                        setLoading={setKnowledgeLoading}
                        expandedSections={expandedSections}
                        setExpandedSections={setExpandedSections}
                    />
                )}
            </div>
        </div>
    );
}

/* ===== Knowledge Tree Tab ===== */

function KnowledgeTreeTab({
    studentId, subjects, setSubjects,
    selectedSubject, setSelectedSubject,
    progress, setProgress,
    loading, setLoading,
    expandedSections, setExpandedSections,
}) {
    // Load subjects on mount
    useEffect(() => {
        if (subjects.length > 0) return;
        let cancelled = false;
        (async () => {
            try {
                const res = await getSubjects();
                const data = res.data?.results || res.data || [];
                if (!cancelled) setSubjects(data);
            } catch (err) {
                console.error('Failed to load subjects:', err);
            }
        })();
        return () => { cancelled = true; };
    }, [subjects.length, setSubjects]);

    // Load progress when subject changes
    useEffect(() => {
        if (!selectedSubject) { setProgress(null); return; }
        let cancelled = false;
        (async () => {
            setLoading(true);
            try {
                const res = await getStudentProgress(studentId, selectedSubject);
                if (!cancelled) {
                    setProgress(res.data);
                    // Auto-expand all sections
                    const expanded = {};
                    (res.data.sections || []).forEach(s => { expanded[s.id] = true; });
                    setExpandedSections(expanded);
                }
            } catch (err) {
                console.error('Failed to load knowledge progress:', err);
                if (!cancelled) setProgress(null);
            } finally {
                if (!cancelled) setLoading(false);
            }
        })();
        return () => { cancelled = true; };
    }, [studentId, selectedSubject, setProgress, setLoading, setExpandedSections]);

    const toggleSection = (sectionId) => {
        setExpandedSections(prev => ({ ...prev, [sectionId]: !prev[sectionId] }));
    };

    const getMasteryColor = (level) => {
        if (level >= 80) return '#16a34a';
        if (level >= 60) return '#ca8a04';
        if (level >= 40) return '#f97316';
        if (level > 0) return '#dc2626';
        return '#e2e8f0';
    };

    const getStatusLabel = (mastery) => {
        if (!mastery) return { text: 'Не начато', className: 'km-status--not-started' };
        const s = mastery.status;
        if (s === 'mastered') return { text: 'Освоено', className: 'km-status--mastered' };
        if (s === 'confident') return { text: 'Уверенно', className: 'km-status--confident' };
        if (s === 'in_progress') return { text: 'В процессе', className: 'km-status--in-progress' };
        if (s === 'needs_review') return { text: 'Повторить', className: 'km-status--needs-review' };
        if (s === 'weak') return { text: 'Слабо', className: 'km-status--weak' };
        return { text: 'Не начато', className: 'km-status--not-started' };
    };

    const getTrendLabel = (mastery) => {
        if (!mastery || mastery.trend == null) return null;
        if (mastery.trend > 5) return { text: 'Рост', className: 'km-trend--up' };
        if (mastery.trend < -5) return { text: 'Спад', className: 'km-trend--down' };
        return { text: 'Стабильно', className: 'km-trend--stable' };
    };

    // Group subjects by exam type
    const examGroups = subjects.reduce((acc, subj) => {
        const examName = subj.exam_type_name || subj.exam_type?.name || 'Другое';
        if (!acc[examName]) acc[examName] = [];
        acc[examName].push(subj);
        return acc;
    }, {});

    return (
        <div className="sd-knowledge">
            <div className="sd-section-header">
                <h3>Карта знаний по экзамену</h3>
            </div>

            {/* Subject selector */}
            <div className="km-subject-selector">
                {Object.entries(examGroups).map(([examName, subjs]) => (
                    <div key={examName} className="km-exam-group">
                        <span className="km-exam-label">{examName}</span>
                        <div className="km-subject-chips">
                            {subjs.map(subj => (
                                <button
                                    key={subj.id}
                                    className={`km-subject-chip ${selectedSubject === subj.id ? 'km-subject-chip--active' : ''}`}
                                    onClick={() => setSelectedSubject(subj.id)}
                                >
                                    {subj.name}
                                </button>
                            ))}
                        </div>
                    </div>
                ))}
            </div>

            {!selectedSubject && (
                <div className="sd-empty-state">Выберите предмет для просмотра карты знаний</div>
            )}

            {loading && selectedSubject && (
                <div className="sd-loading km-loading">
                    <div className="sd-spinner"></div>
                    <span>Загрузка карты знаний...</span>
                </div>
            )}

            {!loading && progress && selectedSubject && (
                <>
                    {/* Summary cards */}
                    <div className="km-summary">
                        <div className="km-summary-card km-summary-card--mastery">
                            <div className="km-summary-value">{progress.overall_mastery}%</div>
                            <div className="km-summary-label">Общее владение</div>
                            <div className="km-summary-bar">
                                <div
                                    className="km-summary-bar-fill"
                                    style={{
                                        width: `${progress.overall_mastery}%`,
                                        backgroundColor: getMasteryColor(progress.overall_mastery),
                                    }}
                                />
                            </div>
                        </div>
                        <div className="km-summary-card km-summary-card--mastered">
                            <div className="km-summary-value">{progress.topics_mastered}</div>
                            <div className="km-summary-label">Освоено</div>
                        </div>
                        <div className="km-summary-card km-summary-card--progress">
                            <div className="km-summary-value">{progress.topics_in_progress}</div>
                            <div className="km-summary-label">В процессе</div>
                        </div>
                        <div className="km-summary-card km-summary-card--review">
                            <div className="km-summary-value">{progress.topics_needs_review}</div>
                            <div className="km-summary-label">Повторить</div>
                        </div>
                        <div className="km-summary-card km-summary-card--not-started">
                            <div className="km-summary-value">{progress.topics_not_started}</div>
                            <div className="km-summary-label">Не начато</div>
                        </div>
                    </div>

                    {/* Section tree */}
                    <div className="km-tree">
                        {(progress.sections || []).map(section => (
                            <div key={section.id} className="km-section">
                                <button
                                    className="km-section-header"
                                    onClick={() => toggleSection(section.id)}
                                >
                                    <span className="km-section-chevron">
                                        {expandedSections[section.id] ? <IconChevronDown /> : <IconChevronRight />}
                                    </span>
                                    <span className="km-section-name">{section.name}</span>
                                    <span className="km-section-meta">
                                        {section.topics_with_data}/{section.topics_count} тем
                                    </span>
                                    <div className="km-section-bar">
                                        <div
                                            className="km-section-bar-fill"
                                            style={{
                                                width: `${section.avg_mastery}%`,
                                                backgroundColor: getMasteryColor(section.avg_mastery),
                                            }}
                                        />
                                    </div>
                                    <span className="km-section-percent">{section.avg_mastery}%</span>
                                </button>

                                {expandedSections[section.id] && (
                                    <div className="km-topics">
                                        {section.topics.map(topic => {
                                            const statusInfo = getStatusLabel(topic.mastery);
                                            const trendInfo = getTrendLabel(topic.mastery);
                                            return (
                                                <div key={topic.id} className="km-topic-row">
                                                    <span className="km-topic-task">
                                                        {topic.task_number ? `Задание ${topic.task_number}` : topic.code}
                                                    </span>
                                                    <span className="km-topic-name">{topic.name}</span>
                                                    <span className={`km-topic-status ${statusInfo.className}`}>
                                                        {statusInfo.text}
                                                    </span>
                                                    {topic.mastery && (
                                                        <div className="km-topic-bar">
                                                            <div
                                                                className="km-topic-bar-fill"
                                                                style={{
                                                                    width: `${topic.mastery.mastery_level}%`,
                                                                    backgroundColor: getMasteryColor(topic.mastery.mastery_level),
                                                                }}
                                                            />
                                                        </div>
                                                    )}
                                                    {!topic.mastery && <div className="km-topic-bar km-topic-bar--empty" />}
                                                    <span className="km-topic-percent">
                                                        {topic.mastery ? `${topic.mastery.mastery_level}%` : '—'}
                                                    </span>
                                                    {trendInfo && (
                                                        <span className={`km-topic-trend ${trendInfo.className}`}>
                                                            {trendInfo.text}
                                                        </span>
                                                    )}
                                                </div>
                                            );
                                        })}
                                    </div>
                                )}
                            </div>
                        ))}
                    </div>
                </>
            )}
        </div>
    );
}

export default StudentDetailAnalytics;
