import React, { useState, useEffect, useCallback } from 'react';
import { useAuth } from '../auth';
import { apiClient } from '../apiService';
import { Link, useSearchParams } from 'react-router-dom';
import StudentDetailAnalytics from './StudentDetailAnalytics';
import GroupSocialDynamics from './GroupSocialDynamics';
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
    const [summary, setSummary] = useState(null);
    const [groups, setGroups] = useState([]);
    const [students, setStudents] = useState([]);
    const [selectedStudent, setSelectedStudent] = useState(null);
    const [selectedGroup, setSelectedGroup] = useState(null);
    const [alerts, setAlerts] = useState([]);
    const [loading, setLoading] = useState(true);
    const [searchQuery, setSearchQuery] = useState('');

    const loadData = useCallback(async () => {
        try {
            setLoading(true);
            const [summaryRes, groupsRes] = await Promise.all([
                apiClient.get('/dashboard/summary/').catch(() => ({ data: {} })),
                apiClient.get('/groups/')
            ]);
            setSummary(summaryRes.data);
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
                    <div className="stat-card-value">{summary?.groups_count || groups.length}</div>
                </div>
                <div className="stat-card">
                    <div className="stat-card-header">
                        <span className="stat-card-icon stat-card-icon--success">
                            <IconStudents />
                        </span>
                        <span className="stat-card-label">Ученики</span>
                    </div>
                    <div className="stat-card-value">{summary?.students_count || students.length}</div>
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
                    <GroupSocialDynamics groupId={selectedGroup.id} />
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
