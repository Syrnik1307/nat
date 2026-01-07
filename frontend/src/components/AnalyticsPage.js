import React, { useState, useEffect } from 'react';
import { useAuth } from '../auth';
import { apiClient } from '../apiService';
import { Link } from 'react-router-dom';
import NavBar from './NavBar';
import './AnalyticsPage.css';

const AnalyticsPage = () => {
    const { role } = useAuth();
    const [summary, setSummary] = useState(null);
    const [groups, setGroups] = useState([]);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        loadData();
    }, []);

    const loadData = async () => {
        try {
            setLoading(true);
            const [summaryRes, groupsRes] = await Promise.all([
                apiClient.get('/analytics/dashboard/summary/').catch(() => ({ data: {} })),
                apiClient.get('/groups/')
            ]);
            setSummary(summaryRes.data);
            setGroups(groupsRes.data.results || groupsRes.data || []);
        } catch (e) {
            console.error(e);
        } finally {
            setLoading(false);
        }
    };

    if (role !== 'teacher' && role !== 'admin') {
        return (
            <div className="analytics-page">
                <NavBar />
                <div className="container" style={{padding: '20px'}}>Доступ запрещен</div>
            </div>
        );
    }

    return (
        <div className="analytics-page-root">
            <NavBar />
            <div className="analytics-container">
                <div className="analytics-header">
                   <h1>Аналитика обучения</h1>
                </div>

                {loading ? <div>Загрузка...</div> : (
                    <>
                        <div className="stats-cards">
                           <div className="stat-card">
                             <h3>Активные группы</h3>
                             <p className="stat-num">{summary?.groups_count || 0}</p>
                           </div>
                           <div className="stat-card">
                             <h3>Всего учеников</h3>
                             <p className="stat-num">{summary?.students_count || 0}</p>
                           </div>
                        </div>

                        <h2>Группы</h2>
                        <div className="groups-grid">
                            {groups.map(g => (
                                <div key={g.id} className="group-card-compact">
                                    <h3>{g.name}</h3>
                                    <p>{g.students_count || 0} учеников</p>
                                    {/* Поскольку модалку мы не можем открыть отсюда легко без рефакторинга роутинга модалок,
                                        мы можем отправить просто на страницу групп или сделать заглушку.
                                        В идеале - открывать GroupDetailModal. Но пока просто ссылка.
                                     */}
                                     <Link to={`/groups/manage?openGroup=${g.id}`} className="view-btn">
                                        Открыть отчеты
                                     </Link>
                                </div>
                            ))}
                        </div>
                    </>
                )}
            </div>
        </div>
    );
};

export default AnalyticsPage;
