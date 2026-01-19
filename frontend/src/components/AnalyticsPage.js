import React, { useState, useEffect, useCallback } from 'react';
import { useAuth } from '../auth';
import { apiClient, getTeacherEarlyWarnings, getTeacherMonthlyDynamics, getTeacherSlaDetails, getTeacherStudentRisks, getTeacherWeeklyDynamics } from '../apiService';
import { Link, useSearchParams } from 'react-router-dom';
import StudentDetailAnalytics from './StudentDetailAnalytics';
import GroupDetailAnalytics from './GroupDetailAnalytics';
import './AnalyticsPage.css';

// SVG Icons - чистые иконки без эмодзи
const IconOverview = () => (
    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
        <rect x="3" y="3" width="7" height="7" rx="1"/>
        <rect x="14" y="3" width="7" height="7" rx="1"/>
        <rect x="3" y="14" width="7" height="7" rx="1"/>
        <rect x="14" y="14" width="7" height="7" rx="1"/>
    </svg>
);

const IconStudents = () => (
    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
        <path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"/>
        <circle cx="9" cy="7" r="4"/>
        <path d="M23 21v-2a4 4 0 0 0-3-3.87"/>
        <path d="M16 3.13a4 4 0 0 1 0 7.75"/>
    </svg>
);

const IconGroups = () => (
    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
        <path d="M12 2L2 7l10 5 10-5-10-5z"/>
        <path d="M2 17l10 5 10-5"/>
        <path d="M2 12l10 5 10-5"/>
    </svg>
);

const IconAlerts = () => (
    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
        <path d="M18 8A6 6 0 0 0 6 8c0 7-3 9-3 9h18s-3-2-3-9"/>
        <path d="M13.73 21a2 2 0 0 1-3.46 0"/>
    </svg>
);

const IconCheck = () => (
    <svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
        <path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"/>
        <polyline points="22 4 12 14.01 9 11.01"/>
    </svg>
);

const IconWarning = () => (
    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
        <path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"/>
        <line x1="12" y1="9" x2="12" y2="13"/>
        <line x1="12" y1="17" x2="12.01" y2="17"/>
    </svg>
);

const IconCritical = () => (
    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
        <circle cx="12" cy="12" r="10"/>
        <line x1="12" y1="8" x2="12" y2="12"/>
        <line x1="12" y1="16" x2="12.01" y2="16"/>
    </svg>
);

const IconArrowRight = () => (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
        <line x1="5" y1="12" x2="19" y2="12"/>
        <polyline points="12 5 19 12 12 19"/>
    </svg>
);

const IconArrowLeft = () => (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
        <line x1="19" y1="12" x2="5" y2="12"/>
        <polyline points="12 19 5 12 12 5"/>
    </svg>
);

const IconSearch = () => (
    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
        <circle cx="11" cy="11" r="8"/>
        <line x1="21" y1="21" x2="16.65" y2="16.65"/>
    </svg>
);

const TABS = [
    { id: 'overview', label: 'Обзор', Icon: IconOverview },
    { id: 'students', label: 'Ученики', Icon: IconStudents },
    { id: 'groups', label: 'Группы', Icon: IconGroups },
    { id: 'alerts', label: 'Оповещения', Icon: IconAlerts },
];

const AnalyticsPage = () => {
    const { role } = useAuth();
    const [searchParams, setSearchParams] = useSearchParams();
    const [activeTab, setActiveTab] = useState(searchParams.get('tab') || 'overview');
    const [groups, setGroups] = useState([]);
    const [students, setStudents] = useState([]);
    const [selectedStudent, setSelectedStudent] = useState(null);
    const [selectedGroup, setSelectedGroup] = useState(null);
    const [alerts, setAlerts] = useState([]);
    const [loading, setLoading] = useState(true);
    const [searchQuery, setSearchQuery] = useState('');
    const [slaDetails, setSlaDetails] = useState(null);
    const [studentRisks, setStudentRisks] = useState(null);
    const [earlyWarnings, setEarlyWarnings] = useState(null);
    const [monthlyDynamics, setMonthlyDynamics] = useState(null);
    const [weeklyDynamics, setWeeklyDynamics] = useState(null);

    const loadData = useCallback(async () => {
        try {
            setLoading(true);
            const [groupsRes, slaRes, risksRes, ewsRes] = await Promise.all([
                apiClient.get('/groups/'),
                getTeacherSlaDetails().catch(() => ({ data: null })),
                getTeacherStudentRisks().catch(() => ({ data: null })),
                getTeacherEarlyWarnings({ lessons: 5 }).catch(() => ({ data: null })),
            ]);
            setSlaDetails(slaRes.data);
            setStudentRisks(risksRes.data);
            setEarlyWarnings(ewsRes.data);
            // Динамика — не критично, грузим отдельным запросом и не валим весь экран
            getTeacherMonthlyDynamics({ months: 3 })
                .then((res) => setMonthlyDynamics(res.data))
                .catch(() => setMonthlyDynamics(null));

            getTeacherWeeklyDynamics({ weeks: 8 })
                .then((res) => setWeeklyDynamics(res.data))
                .catch(() => setWeeklyDynamics(null));
            const groupsList = groupsRes.data.results || groupsRes.data || [];
            setGroups(groupsList);
            const allStudents = [];
            const seen = new Set();
            groupsList.forEach(g => {
                (g.students || []).forEach(s => {
                    if (!seen.has(s.id)) {
                        seen.add(s.id);
                        allStudents.push({ ...s, groupName: g.name, groupId: g.id });
                    }
                });
            });
            setStudents(allStudents);
            loadAlerts();
        } catch (e) {
            console.error(e);
        } finally {
            setLoading(false);
        }
    }, []);

    useEffect(() => {
        loadData();
    }, [loadData]);

    useEffect(() => {
        setSearchParams({ tab: activeTab });
    }, [activeTab, setSearchParams]);

    const loadAlerts = async () => {
        try {
            const res = await apiClient.get('/attendance-alerts/');
            const data = res.data;
            
            const alertsList = (data.alerts || []).map(alert => ({
                type: 'consecutive_absences',
                severity: alert.severity,
                student: {
                    id: alert.student_id,
                    first_name: alert.student_name?.split(' ')[0] || '',
                    last_name: alert.student_name?.split(' ')[1] || '',
                    email: alert.student_email,
                },
                group: {
                    id: alert.group_id,
                    name: alert.group_name,
                },
                count: alert.consecutive_absences,
                message: `${alert.student_name} пропустил ${alert.consecutive_absences} занятий подряд`
            }));
            
            setAlerts(alertsList);
        } catch (e) {
            console.error('Error loading alerts:', e);
            setAlerts([]);
        }
    };

    if (role !== 'teacher' && role !== 'admin') {
        return (
            <div className="analytics-page" style={{ padding: '20px' }}>Доступ запрещен</div>
        );
    }

    const filteredStudents = students.filter(s => {
        if (!searchQuery) return true;
        const q = searchQuery.toLowerCase();
        return (
            s.first_name?.toLowerCase().includes(q) ||
            s.last_name?.toLowerCase().includes(q) ||
            s.email?.toLowerCase().includes(q) ||
            s.groupName?.toLowerCase().includes(q)
        );
    });

    const isIndividualGroup = (g) => {
        const name = (g?.name || '').trim().toLowerCase();
        const studentsCount = g?.students_count ?? g?.students?.length ?? 0;
        return studentsCount <= 1 || name.startsWith('индивидуально');
    };

    const groupCount = groups.filter(g => !isIndividualGroup(g)).length;
    const individualCount = groups.length - groupCount;

    const renderOverviewTab = () => (
        <div className="analytics-overview">
            <div className="stats-row">
                <div className="stat-card">
                    <div className="stat-card-header">
                        <span className="stat-card-icon stat-card-icon--primary">
                            <IconGroups />
                        </span>
                        <span className="stat-card-label">Группы</span>
                    </div>
                    <div className="stat-card-value">{groupCount}</div>
                    {individualCount > 0 && (
                        <div className="stat-card-subvalue">Индивидуальные: {individualCount}</div>
                    )}
                </div>
                <div className="stat-card">
                    <div className="stat-card-header">
                        <span className="stat-card-icon stat-card-icon--success">
                            <IconStudents />
                        </span>
                        <span className="stat-card-label">Ученики</span>
                    </div>
                    <div className="stat-card-value">{students.length}</div>
                </div>
                <div className={`stat-card ${alerts.length > 0 ? 'stat-card--warning' : ''}`}>
                    <div className="stat-card-header">
                        <span className={`stat-card-icon ${alerts.length > 0 ? 'stat-card-icon--warning' : 'stat-card-icon--muted'}`}>
                            <IconAlerts />
                        </span>
                        <span className="stat-card-label">Требуют внимания</span>
                    </div>
                    <div className="stat-card-value">{alerts.length}</div>
                    {alerts.length > 0 && (
                        <button 
                            className="stat-card-link"
                            onClick={() => setActiveTab('alerts')}
                        >
                            Посмотреть
                        </button>
                    )}
                </div>
            </div>

            <div className="analytics-section">
                <div className="section-header">
                    <h2>Динамика (последние 3 месяца)</h2>
                </div>

                {monthlyDynamics?.months?.length ? (
                    <div className="monthly-dynamics-table">
                        <div className="monthly-dynamics-head">
                            <div className="monthly-dynamics-cell monthly-dynamics-cell--month">Месяц</div>
                            <div className="monthly-dynamics-cell">Уроки</div>
                            <div className="monthly-dynamics-cell">Посещаемость</div>
                            <div className="monthly-dynamics-cell">Сдано ДЗ</div>
                            <div className="monthly-dynamics-cell">Проверено ДЗ</div>
                            <div className="monthly-dynamics-cell">Средний результат</div>
                            <div className="monthly-dynamics-cell">Ниже 60%</div>
                        </div>

                        {monthlyDynamics.months.map((m) => {
                            const [y, mon] = (m.month || '').split('-').map((x) => parseInt(x, 10));
                            const monthLabel = (y && mon)
                                ? new Date(y, mon - 1, 1).toLocaleDateString('ru-RU', { month: 'short', year: 'numeric' })
                                : (m.month || '');

                            const attendance = (m.attendance_percent === null || m.attendance_percent === undefined)
                                ? '—'
                                : `${m.attendance_percent}%`;
                            const avgScore = (m.avg_score_percent === null || m.avg_score_percent === undefined)
                                ? '—'
                                : `${m.avg_score_percent}%`;

                            return (
                                <div key={m.month} className="monthly-dynamics-row">
                                    <div className="monthly-dynamics-cell monthly-dynamics-cell--month">{monthLabel}</div>
                                    <div className="monthly-dynamics-cell">{m.lessons_count ?? 0}</div>
                                    <div className="monthly-dynamics-cell">{attendance}</div>
                                    <div className="monthly-dynamics-cell">{m.homework_submitted_count ?? 0}</div>
                                    <div className="monthly-dynamics-cell">{m.homework_graded_count ?? 0}</div>
                                    <div className="monthly-dynamics-cell">{avgScore}</div>
                                    <div className="monthly-dynamics-cell">{m.below_60_percent_count ?? 0}</div>
                                </div>
                            );
                        })}
                    </div>
                ) : (
                    <div className="empty-state" style={{ padding: '16px' }}>
                        <p style={{ margin: 0 }}>
                            Пока недостаточно данных для динамики.
                        </p>
                    </div>
                )}
            </div>

            <div className="analytics-section">
                <div className="section-header">
                    <h2>Динамика (последние 8 недель)</h2>
                </div>

                {weeklyDynamics?.weeks?.length ? (
                    <div className="monthly-dynamics-table">
                        <div className="monthly-dynamics-head">
                            <div className="monthly-dynamics-cell monthly-dynamics-cell--month">Неделя</div>
                            <div className="monthly-dynamics-cell">Уроки</div>
                            <div className="monthly-dynamics-cell">Посещаемость</div>
                            <div className="monthly-dynamics-cell">Сдано ДЗ</div>
                            <div className="monthly-dynamics-cell">Проверено ДЗ</div>
                            <div className="monthly-dynamics-cell">Средний результат</div>
                            <div className="monthly-dynamics-cell">Ниже 60%</div>
                        </div>

                        {weeklyDynamics.weeks.map((w) => {
                            const start = w.week_start ? new Date(w.week_start) : null;
                            const end = w.week_end ? new Date(w.week_end) : null;
                            const label = (start && end)
                                ? `${start.toLocaleDateString('ru-RU', { day: '2-digit', month: 'short' })} — ${end.toLocaleDateString('ru-RU', { day: '2-digit', month: 'short' })}`
                                : (w.week_start || '');

                            const attendance = (w.attendance_percent === null || w.attendance_percent === undefined)
                                ? '—'
                                : `${w.attendance_percent}%`;
                            const avgScore = (w.avg_score_percent === null || w.avg_score_percent === undefined)
                                ? '—'
                                : `${w.avg_score_percent}%`;

                            return (
                                <div key={w.week_start} className="monthly-dynamics-row">
                                    <div className="monthly-dynamics-cell monthly-dynamics-cell--month">{label}</div>
                                    <div className="monthly-dynamics-cell">{w.lessons_count ?? 0}</div>
                                    <div className="monthly-dynamics-cell">{attendance}</div>
                                    <div className="monthly-dynamics-cell">{w.homework_submitted_count ?? 0}</div>
                                    <div className="monthly-dynamics-cell">{w.homework_graded_count ?? 0}</div>
                                    <div className="monthly-dynamics-cell">{avgScore}</div>
                                    <div className="monthly-dynamics-cell">{w.below_60_percent_count ?? 0}</div>
                                </div>
                            );
                        })}
                    </div>
                ) : (
                    <div className="empty-state" style={{ padding: '16px' }}>
                        <p style={{ margin: 0 }}>
                            Пока недостаточно данных для динамики.
                        </p>
                    </div>
                )}
            </div>

            <section className="analytics-section">
                <div className="section-header">
                    <h2>Группы</h2>
                    <span className="section-count">{groups.length}</span>
                </div>
                <div className="data-table">
                    <table>
                        <thead>
                            <tr>
                                <th>Название</th>
                                <th>Учеников</th>
                                <th>Действия</th>
                            </tr>
                        </thead>
                        <tbody>
                            {groups.map(g => (
                                <tr key={g.id}>
                                    <td className="cell-primary">{g.name}</td>
                                    <td>{g.students_count || g.students?.length || 0}</td>
                                    <td className="cell-actions">
                                        <Link to={`/groups/manage?openGroup=${g.id}`} className="link-action">
                                            Журнал
                                        </Link>
                                        <button 
                                            className="link-action"
                                            onClick={() => {
                                                setSelectedGroup(g);
                                                setActiveTab('groups');
                                            }}
                                        >
                                            Аналитика
                                        </button>
                                    </td>
                                </tr>
                            ))}
                            {groups.length === 0 && (
                                <tr>
                                    <td colSpan={3} className="cell-empty">Нет групп</td>
                                </tr>
                            )}
                        </tbody>
                    </table>
                </div>
            </section>

            {students.length > 0 && (
                <section className="analytics-section">
                    <div className="section-header">
                        <h2>Быстрый доступ</h2>
                    </div>
                    <div className="quick-access">
                        {students.slice(0, 8).map(s => (
                            <button 
                                key={s.id}
                                className="quick-chip"
                                onClick={() => {
                                    setSelectedStudent(s);
                                    setActiveTab('students');
                                }}
                            >
                                <span className="quick-chip-avatar">
                                    {(s.first_name?.[0] || s.email?.[0] || '?').toUpperCase()}
                                </span>
                                <span className="quick-chip-name">{s.first_name} {s.last_name?.[0]}.</span>
                            </button>
                        ))}
                        {students.length > 8 && (
                            <button 
                                className="quick-chip quick-chip--more"
                                onClick={() => setActiveTab('students')}
                            >
                                +{students.length - 8}
                            </button>
                        )}
                    </div>
                </section>
            )}

            <section className="analytics-section">
                <div className="section-header">
                    <h2>Ранние предупреждения (7-14 дней)</h2>
                    {earlyWarnings?.count > 0 && (
                        <span className="section-count section-count--warning">{earlyWarnings.count}</span>
                    )}
                </div>
                {!earlyWarnings ? (
                    <p className="section-empty-text">Загрузка данных...</p>
                ) : earlyWarnings.count === 0 ? (
                    <p className="section-empty-text">Рисков не обнаружено по последним {earlyWarnings.window_lessons} урокам</p>
                ) : (
                    <div className="risk-students-list">
                        {earlyWarnings.students.slice(0, 5).map(w => (
                            <div key={w.student_id} className="risk-student-card">
                                <div className="risk-student-info">
                                    <span className="risk-student-name">{w.student_name}</span>
                                    <span className="risk-student-group">{w.group_name}</span>
                                </div>
                                <div className="risk-factors">
                                    {(w.factors || []).slice(0, 2).map((f, idx) => {
                                        const typeClasses = {
                                            attendance: 'risk-factor--attendance',
                                            homework: 'risk-factor--homework',
                                            grades: 'risk-factor--grade',
                                            activity: 'risk-factor--grade',
                                        };
                                        return (
                                            <span key={idx} className={`risk-factor ${typeClasses[f.type] || ''}`} title={f.message}>
                                                {f.message}
                                            </span>
                                        );
                                    })}
                                </div>
                                <div className="risk-actions">
                                    {(w.actions || []).slice(0, 2).map((a, idx) => (
                                        <div key={idx} className="risk-action-item">{a}</div>
                                    ))}
                                </div>
                                <button
                                    className="risk-student-action"
                                    onClick={() => {
                                        const student = students.find(s => s.id === w.student_id);
                                        if (student) {
                                            setSelectedStudent(student);
                                            setActiveTab('students');
                                        }
                                    }}
                                >
                                    Открыть
                                </button>
                            </div>
                        ))}
                    </div>
                )}
            </section>

            {/* Homework Review Speed Section */}
            <section className="analytics-section">
                <div className="section-header">
                    <h2>Время проверки ДЗ</h2>
                    {slaDetails?.health && (
                        <span className={`sla-health-badge sla-health-badge--${slaDetails.health.status || 'good'}`}>
                            Скорость: {slaDetails.health.score ?? 100}%
                        </span>
                    )}
                </div>
                {!slaDetails ? (
                    <p className="section-empty-text">Загрузка данных по проверке ДЗ...</p>
                ) : slaDetails.total_graded_30d === 0 && (!slaDetails.backlog || slaDetails.backlog.total === 0) ? (
                    <p className="section-empty-text">Нет проверенных работ за последние 30 дней</p>
                ) : (
                    <div className="sla-overview">
                        {(slaDetails.total_graded_30d > 0 && (slaDetails.grading_time_days_median != null || slaDetails.grading_time_days_p90 != null)) && (
                            <div className="sla-summary-line">
                                {slaDetails.grading_time_days_median != null && (
                                    <span>Обычно проверяете за {slaDetails.grading_time_days_median} дн.</span>
                                )}
                                {slaDetails.grading_time_days_p90 != null && (
                                    <span>{slaDetails.grading_time_days_median != null ? ' ' : ''}90% работ — до {slaDetails.grading_time_days_p90} дн.</span>
                                )}
                            </div>
                        )}
                        {slaDetails.total_graded_30d > 0 && (
                            <div className="sla-distribution">
                                {slaDetails.sla_distribution?.ideal > 0 && (
                                    <div className="sla-bar sla-bar--ideal" style={{ flex: slaDetails.sla_distribution.ideal }}>
                                        <span className="sla-bar-label">{slaDetails.sla_distribution.ideal}</span>
                                    </div>
                                )}
                                {slaDetails.sla_distribution?.good > 0 && (
                                    <div className="sla-bar sla-bar--good" style={{ flex: slaDetails.sla_distribution.good }}>
                                        <span className="sla-bar-label">{slaDetails.sla_distribution.good}</span>
                                    </div>
                                )}
                                {slaDetails.sla_distribution?.slow > 0 && (
                                    <div className="sla-bar sla-bar--slow" style={{ flex: slaDetails.sla_distribution.slow }}>
                                        <span className="sla-bar-label">{slaDetails.sla_distribution.slow}</span>
                                    </div>
                                )}
                                {slaDetails.sla_distribution?.critical > 0 && (
                                    <div className="sla-bar sla-bar--critical" style={{ flex: slaDetails.sla_distribution.critical }}>
                                        <span className="sla-bar-label">{slaDetails.sla_distribution.critical}</span>
                                    </div>
                                )}
                            </div>
                        )}
                        <div className="sla-legend">
                            <span className="sla-legend-item"><span className="sla-dot sla-dot--ideal"></span> До 3 дней</span>
                            <span className="sla-legend-item"><span className="sla-dot sla-dot--good"></span> 4-7 дней</span>
                            <span className="sla-legend-item"><span className="sla-dot sla-dot--slow"></span> 8-10 дней</span>
                            <span className="sla-legend-item"><span className="sla-dot sla-dot--critical"></span> 10+ дней</span>
                        </div>
                        {slaDetails.backlog?.total > 0 && (
                            <div className="sla-backlog-warning">
                                <span className="sla-backlog-count">{slaDetails.backlog.total}</span> 
                                {slaDetails.backlog.total === 1 ? 'работа ждёт' : 'работ ждут'} проверки
                                {slaDetails.backlog.counts?.critical > 0 && (
                                    <span className="sla-backlog-critical">
                                        ({slaDetails.backlog.counts.critical} критич.)
                                    </span>
                                )}
                            </div>
                        )}
                    </div>
                )}
            </section>

            {/* At-Risk Students Section */}
            <section className={`analytics-section ${studentRisks?.students?.length > 0 ? 'analytics-section--warning' : ''}`}>
                <div className="section-header">
                    <h2>Ученики в зоне риска</h2>
                    {studentRisks?.at_risk_count > 0 && (
                        <span className="section-count section-count--warning">{studentRisks.at_risk_count}</span>
                    )}
                </div>
                {!studentRisks ? (
                    <p className="section-empty-text">Загрузка данных...</p>
                ) : !studentRisks.students || studentRisks.students.length === 0 ? (
                    <p className="section-empty-text">Нет учеников в зоне риска</p>
                ) : (
                    <div className="risk-students-list">
                        {studentRisks.students.slice(0, 5).map(risk => (
                            <div key={risk.student_id} className="risk-student-card">
                                <div className="risk-student-info">
                                    <span className="risk-student-name">{risk.student_name}</span>
                                    <span className="risk-student-group">{risk.group_name}</span>
                                </div>
                                <div className="risk-factors">
                                    {risk.risk_factors?.map((factor, idx) => {
                                        const typeClasses = {
                                            attendance: 'risk-factor--attendance',
                                            homework: 'risk-factor--homework',
                                            grades: 'risk-factor--grade',
                                        };
                                        return (
                                            <span 
                                                key={idx}
                                                className={`risk-factor ${typeClasses[factor.type] || ''}`}
                                                title={factor.message}
                                            >
                                                {factor.message}
                                            </span>
                                        );
                                    })}
                                </div>
                                <button 
                                    className="risk-student-action"
                                    onClick={() => {
                                        const student = students.find(s => s.id === risk.student_id);
                                        if (student) {
                                            setSelectedStudent(student);
                                            setActiveTab('students');
                                        }
                                    }}
                                >
                                    Подробнее
                                </button>
                            </div>
                        ))}
                        {studentRisks.students.length > 5 && (
                            <button 
                                className="risk-show-all"
                                onClick={() => setActiveTab('alerts')}
                            >
                                Показать всех ({studentRisks.at_risk_count})
                            </button>
                        )}
                    </div>
                )}
            </section>
        </div>
    );

    const renderStudentsTab = () => {
        if (selectedStudent) {
            return (
                <div className="detail-view">
                    <button className="back-button" onClick={() => setSelectedStudent(null)}>
                        <IconArrowLeft />
                        <span>К списку учеников</span>
                    </button>
                    <StudentDetailAnalytics 
                        studentId={selectedStudent.id} 
                        groupId={selectedStudent.groupId}
                    />
                </div>
            );
        }

        return (
            <div className="students-view">
                <div className="view-toolbar">
                    <div className="search-input">
                        <IconSearch />
                        <input 
                            type="text"
                            placeholder="Поиск по имени или группе..."
                            value={searchQuery}
                            onChange={(e) => setSearchQuery(e.target.value)}
                        />
                    </div>
                    <span className="view-count">
                        {filteredStudents.length} из {students.length}
                    </span>
                </div>

                <div className="data-table">
                    <table>
                        <thead>
                            <tr>
                                <th>Ученик</th>
                                <th>Группа</th>
                                <th>Email</th>
                                <th></th>
                            </tr>
                        </thead>
                        <tbody>
                            {filteredStudents.map(s => (
                                <tr 
                                    key={s.id} 
                                    className="row-clickable"
                                    onClick={() => setSelectedStudent(s)}
                                >
                                    <td>
                                        <div className="cell-student">
                                            <span className="cell-avatar">
                                                {(s.first_name?.[0] || s.email?.[0] || '?').toUpperCase()}
                                            </span>
                                            <span className="cell-name">
                                                {s.first_name} {s.last_name}
                                            </span>
                                        </div>
                                    </td>
                                    <td className="cell-muted">{s.groupName}</td>
                                    <td className="cell-muted">{s.email}</td>
                                    <td className="cell-arrow">
                                        <IconArrowRight />
                                    </td>
                                </tr>
                            ))}
                            {filteredStudents.length === 0 && (
                                <tr>
                                    <td colSpan={4} className="cell-empty">
                                        {searchQuery ? 'Ничего не найдено' : 'Нет учеников'}
                                    </td>
                                </tr>
                            )}
                        </tbody>
                    </table>
                </div>
            </div>
        );
    };

    const renderGroupsTab = () => {
        if (selectedGroup) {
            return (
                <div className="detail-view">
                    <button className="back-button" onClick={() => setSelectedGroup(null)}>
                        <IconArrowLeft />
                        <span>К списку групп</span>
                    </button>
                    <GroupDetailAnalytics groupId={selectedGroup.id} />
                </div>
            );
        }

        return (
            <div className="groups-view">
                <div className="section-header">
                    <h2>Выберите группу для анализа</h2>
                </div>
                <div className="data-table">
                    <table>
                        <thead>
                            <tr>
                                <th>Группа</th>
                                <th>Учеников</th>
                                <th></th>
                            </tr>
                        </thead>
                        <tbody>
                            {groups.map(g => (
                                <tr 
                                    key={g.id}
                                    className="row-clickable"
                                    onClick={() => setSelectedGroup(g)}
                                >
                                    <td className="cell-primary">{g.name}</td>
                                    <td>{g.students_count || g.students?.length || 0}</td>
                                    <td className="cell-arrow">
                                        <IconArrowRight />
                                    </td>
                                </tr>
                            ))}
                            {groups.length === 0 && (
                                <tr>
                                    <td colSpan={3} className="cell-empty">Нет групп</td>
                                </tr>
                            )}
                        </tbody>
                    </table>
                </div>
            </div>
        );
    };

    const renderAlertsTab = () => (
        <div className="alerts-view">
            <div className="section-header">
                <h2>Оповещения</h2>
                {alerts.length > 0 && (
                    <span className="section-badge section-badge--warning">{alerts.length}</span>
                )}
            </div>
            
            {alerts.length === 0 ? (
                <div className="empty-state">
                    <div className="empty-state-icon empty-state-icon--success">
                        <IconCheck />
                    </div>
                    <h3>Нет активных оповещений</h3>
                    <p>Все ученики посещают занятия регулярно</p>
                </div>
            ) : (
                <div className="alerts-list">
                    {alerts.map((alert, idx) => (
                        <div 
                            key={idx} 
                            className={`alert-item alert-item--${alert.severity}`}
                        >
                            <div className="alert-item-icon">
                                {alert.severity === 'critical' ? <IconCritical /> : <IconWarning />}
                            </div>
                            <div className="alert-item-content">
                                <div className="alert-item-title">{alert.message}</div>
                                <div className="alert-item-meta">Группа: {alert.group.name}</div>
                            </div>
                            <button 
                                className="alert-item-action"
                                onClick={() => {
                                    setSelectedStudent({
                                        ...alert.student,
                                        groupId: alert.group.id,
                                        groupName: alert.group.name
                                    });
                                    setActiveTab('students');
                                }}
                            >
                                Подробнее
                            </button>
                        </div>
                    ))}
                </div>
            )}
        </div>
    );

    return (
        <div className="analytics-page">
            <div className="analytics-layout">
                <aside className="analytics-sidebar">
                    <div className="sidebar-header">
                        <h1>Аналитика</h1>
                    </div>
                    <nav className="sidebar-nav">
                        {TABS.map(tab => (
                            <button
                                key={tab.id}
                                className={`nav-item ${activeTab === tab.id ? 'nav-item--active' : ''}`}
                                onClick={() => {
                                    setActiveTab(tab.id);
                                    setSelectedStudent(null);
                                    setSelectedGroup(null);
                                    setSearchQuery('');
                                }}
                            >
                                <tab.Icon />
                                <span>{tab.label}</span>
                                {tab.id === 'alerts' && alerts.length > 0 && (
                                    <span className="nav-badge">{alerts.length}</span>
                                )}
                            </button>
                        ))}
                    </nav>
                </aside>

                <main className="analytics-main">
                    {loading ? (
                        <div className="loading-state">
                            <div className="spinner"></div>
                            <p>Загрузка...</p>
                        </div>
                    ) : (
                        <>
                            {activeTab === 'overview' && renderOverviewTab()}
                            {activeTab === 'students' && renderStudentsTab()}
                            {activeTab === 'groups' && renderGroupsTab()}
                            {activeTab === 'alerts' && renderAlertsTab()}
                        </>
                    )}
                </main>
            </div>
        </div>
    );
};

export default AnalyticsPage;
