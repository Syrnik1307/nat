import React, { useState, useEffect, useCallback } from 'react';
import { isKnowledgeMapEnabled, getStudentSummary, getMyProgress } from '../knowledgeMapService';
import KnowledgeRadarChart from './KnowledgeRadarChart';
import './KnowledgeMapPanel.css';

/**
 * Student's own Knowledge Map page - /student/knowledge-map
 * Feature-flagged: renders placeholder if module is disabled.
 */
const StudentKnowledgeMapPage = () => {
    const [summary, setSummary] = useState([]);
    const [selectedSubject, setSelectedSubject] = useState(null);
    const [progress, setProgress] = useState(null);
    const [loading, setLoading] = useState(true);
    const [progressLoading, setProgressLoading] = useState(false);

    const fetchSummary = useCallback(async () => {
        if (!isKnowledgeMapEnabled()) {
            setLoading(false);
            return;
        }
        try {
            const res = await getStudentSummary();
            const data = res?.data || [];
            setSummary(data);
            if (data.length > 0) {
                setSelectedSubject(data[0].subject_id);
            }
        } catch (err) {
            console.error('Knowledge map summary error:', err);
        } finally {
            setLoading(false);
        }
    }, []);

    const fetchProgress = useCallback(async (subjectId) => {
        if (!subjectId) return;
        try {
            setProgressLoading(true);
            const res = await getMyProgress(subjectId);
            setProgress(res?.data || null);
        } catch (err) {
            console.error('Knowledge map progress error:', err);
        } finally {
            setProgressLoading(false);
        }
    }, []);

    useEffect(() => { fetchSummary(); }, [fetchSummary]);
    useEffect(() => { if (selectedSubject) fetchProgress(selectedSubject); }, [selectedSubject, fetchProgress]);

    if (!isKnowledgeMapEnabled()) {
        return (
            <div style={{ padding: '2rem', textAlign: 'center', color: '#94a3b8' }}>
                Карта знаний пока недоступна
            </div>
        );
    }

    if (loading) {
        return (
            <div style={{ padding: '2rem' }}>
                <div className="km-loading">Загрузка карты знаний...</div>
            </div>
        );
    }

    const getScoreColor = (pct) => {
        if (pct >= 70) return '#16a34a';
        if (pct >= 40) return '#d97706';
        return '#dc2626';
    };

    return (
        <div style={{ padding: '1.5rem', maxWidth: 900, margin: '0 auto' }}>
            <h1 style={{ fontSize: 22, fontWeight: 700, color: '#1e293b', marginBottom: 8 }}>
                Карта знаний
            </h1>
            <p style={{ color: '#64748b', fontSize: 14, marginBottom: 24 }}>
                Отслеживайте свой прогресс по темам экзамена
            </p>

            {summary.length === 0 ? (
                <div className="km-empty">
                    <div className="km-empty-icon">
                        <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="#94a3b8" strokeWidth="1.5">
                            <path d="M2 3h6a4 4 0 0 1 4 4v14a3 3 0 0 0-3-3H2z"/>
                            <path d="M22 3h-6a4 4 0 0 0-4 4v14a3 3 0 0 1 3-3h7z"/>
                        </svg>
                    </div>
                    <p className="km-empty-title">Нет назначенных экзаменов</p>
                    <p className="km-empty-subtitle">
                        Когда учитель назначит предметы, здесь появится ваша карта знаний
                    </p>
                </div>
            ) : (
                <>
                    {/* Subject cards overview */}
                    <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(200px, 1fr))', gap: 12, marginBottom: 24 }}>
                        {summary.map(s => (
                            <button
                                key={s.subject_id}
                                onClick={() => setSelectedSubject(s.subject_id)}
                                style={{
                                    padding: '16px',
                                    border: selectedSubject === s.subject_id ? '2px solid #4F46E5' : '1px solid #e2e8f0',
                                    borderRadius: 12,
                                    background: selectedSubject === s.subject_id ? '#EEF2FF' : '#fff',
                                    cursor: 'pointer',
                                    textAlign: 'left',
                                    transition: 'all 180ms cubic-bezier(0.4, 0, 0.2, 1)',
                                }}
                            >
                                <div style={{ fontSize: 14, fontWeight: 600, color: '#1e293b', marginBottom: 4 }}>
                                    {s.subject_name}
                                </div>
                                <div style={{ fontSize: 12, color: '#64748b', marginBottom: 8 }}>
                                    {s.exam_type_name}
                                </div>
                                <div style={{
                                    fontSize: 28, fontWeight: 700,
                                    color: getScoreColor(s.overall_percent),
                                }}>
                                    {Math.round(s.overall_percent)}%
                                </div>
                                <div style={{ fontSize: 11, color: '#94a3b8', marginTop: 4 }}>
                                    {s.topics_with_data} / {s.topics_count} тем с данными
                                </div>
                            </button>
                        ))}
                    </div>

                    {/* Selected subject detail */}
                    {progressLoading ? (
                        <div className="km-loading">Загрузка...</div>
                    ) : progress ? (
                        <div className="km-panel">
                            <div className="km-chart-wrapper">
                                <KnowledgeRadarChart topics={progress.scores} size={400} />
                            </div>
                            <div className="km-topics-table">
                                <table>
                                    <thead>
                                        <tr>
                                            <th>#</th>
                                            <th>Тема</th>
                                            <th>Освоение</th>
                                            <th>Тренд</th>
                                            <th>Попытки</th>
                                        </tr>
                                    </thead>
                                    <tbody>
                                        {progress.scores.map(score => (
                                            <tr key={score.topic_number}>
                                                <td className="km-topic-num">{score.topic_number}</td>
                                                <td className="km-topic-title">{score.topic_title}</td>
                                                <td>
                                                    <div className="km-progress-cell">
                                                        <div className="km-progress-bar-wrapper">
                                                            <div
                                                                className="km-progress-bar"
                                                                style={{
                                                                    width: `${Math.min(score.score_percent, 100)}%`,
                                                                    backgroundColor: score.score_percent >= 70 ? '#16a34a' : score.score_percent >= 40 ? '#d97706' : '#dc2626',
                                                                }}
                                                            />
                                                        </div>
                                                        <span className="km-progress-text">
                                                            {Math.round(score.score_percent)}%
                                                        </span>
                                                    </div>
                                                </td>
                                                <td>
                                                    {score.trend === 'up' && (
                                                        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="#16a34a" strokeWidth="2">
                                                            <polyline points="23 6 13.5 15.5 8.5 10.5 1 18" /><polyline points="17 6 23 6 23 12" />
                                                        </svg>
                                                    )}
                                                    {score.trend === 'down' && (
                                                        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="#dc2626" strokeWidth="2">
                                                            <polyline points="23 18 13.5 8.5 8.5 13.5 1 6" /><polyline points="17 18 23 18 23 12" />
                                                        </svg>
                                                    )}
                                                    {score.trend === 'stable' && (
                                                        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="#94a3b8" strokeWidth="2">
                                                            <line x1="5" y1="12" x2="19" y2="12" />
                                                        </svg>
                                                    )}
                                                </td>
                                                <td className="km-attempts">{score.attempts_count}</td>
                                            </tr>
                                        ))}
                                    </tbody>
                                </table>
                            </div>
                        </div>
                    ) : null}
                </>
            )}
        </div>
    );
};

export default StudentKnowledgeMapPage;
