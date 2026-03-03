import React, { useState, useEffect, useCallback } from 'react';
import { isKnowledgeMapEnabled, getStudentProgress, getStudentSummary } from '../knowledgeMapService';
import KnowledgeRadarChart from './KnowledgeRadarChart';
import './KnowledgeMapPanel.css';

/**
 * Panel for Knowledge Map - embeds as a tab in StudentDetailAnalytics
 * or as a standalone block.
 * 
 * @param {number} studentId
 */
const KnowledgeMapPanel = ({ studentId }) => {
    const [summary, setSummary] = useState([]);
    const [selectedSubject, setSelectedSubject] = useState(null);
    const [progress, setProgress] = useState(null);
    const [loading, setLoading] = useState(true);
    const [progressLoading, setProgressLoading] = useState(false);
    const [error, setError] = useState(null);

    const fetchSummary = useCallback(async () => {
        if (!isKnowledgeMapEnabled()) {
            setLoading(false);
            return;
        }
        try {
            setLoading(true);
            const res = await getStudentSummary(studentId);
            const data = res?.data || [];
            setSummary(data);
            if (data.length > 0 && !selectedSubject) {
                setSelectedSubject(data[0].subject_id);
            }
        } catch (err) {
            console.error('Knowledge map summary error:', err);
            setError('Не удалось загрузить данные карты знаний');
        } finally {
            setLoading(false);
        }
    }, [studentId]);

    const fetchProgress = useCallback(async (subjectId) => {
        if (!subjectId) return;
        try {
            setProgressLoading(true);
            const res = await getStudentProgress(studentId, subjectId);
            setProgress(res?.data || null);
        } catch (err) {
            console.error('Knowledge map progress error:', err);
        } finally {
            setProgressLoading(false);
        }
    }, [studentId]);

    useEffect(() => { fetchSummary(); }, [fetchSummary]);
    useEffect(() => { if (selectedSubject) fetchProgress(selectedSubject); }, [selectedSubject, fetchProgress]);

    if (!isKnowledgeMapEnabled()) return null;

    if (loading) {
        return <div className="km-loading">Загрузка карты знаний...</div>;
    }

    if (error) {
        return <div className="km-error">{error}</div>;
    }

    if (summary.length === 0) {
        return (
            <div className="km-empty">
                <div className="km-empty-icon">
                    <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="#94a3b8" strokeWidth="1.5">
                        <path d="M2 3h6a4 4 0 0 1 4 4v14a3 3 0 0 0-3-3H2z"/>
                        <path d="M22 3h-6a4 4 0 0 0-4 4v14a3 3 0 0 1 3-3h7z"/>
                    </svg>
                </div>
                <p className="km-empty-title">Нет назначенных экзаменов</p>
                <p className="km-empty-subtitle">
                    Учитель ещё не назначил предметы для карты знаний.
                    После назначения здесь появится визуализация прогресса.
                </p>
            </div>
        );
    }

    const TrendIcon = ({ trend }) => {
        if (trend === 'up') return (
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="#16a34a" strokeWidth="2">
                <polyline points="23 6 13.5 15.5 8.5 10.5 1 18" />
                <polyline points="17 6 23 6 23 12" />
            </svg>
        );
        if (trend === 'down') return (
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="#dc2626" strokeWidth="2">
                <polyline points="23 18 13.5 8.5 8.5 13.5 1 6" />
                <polyline points="17 18 23 18 23 12" />
            </svg>
        );
        return (
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="#94a3b8" strokeWidth="2">
                <line x1="5" y1="12" x2="19" y2="12" />
            </svg>
        );
    };

    const getScoreColor = (percent) => {
        if (percent >= 70) return '#16a34a';
        if (percent >= 40) return '#d97706';
        return '#dc2626';
    };

    return (
        <div className="km-panel">
            {/* Subject selector */}
            <div className="km-subject-selector">
                {summary.map(s => (
                    <button
                        key={s.subject_id}
                        className={`km-subject-btn ${selectedSubject === s.subject_id ? 'active' : ''}`}
                        onClick={() => setSelectedSubject(s.subject_id)}
                    >
                        <span className="km-subject-name">{s.subject_name}</span>
                        <span className="km-subject-badge" style={{ color: getScoreColor(s.overall_percent) }}>
                            {Math.round(s.overall_percent)}%
                        </span>
                    </button>
                ))}
            </div>

            {/* Radar chart */}
            {progressLoading ? (
                <div className="km-loading">Загрузка...</div>
            ) : progress ? (
                <>
                    <div className="km-chart-wrapper">
                        <KnowledgeRadarChart topics={progress.scores} size={380} />
                    </div>

                    {/* Overall stats */}
                    <div className="km-overall">
                        <div className="km-overall-stat">
                            <span className="km-overall-label">Общий уровень</span>
                            <span className="km-overall-value" style={{ color: getScoreColor(progress.overall_percent) }}>
                                {Math.round(progress.overall_percent)}%
                            </span>
                        </div>
                        <div className="km-overall-stat">
                            <span className="km-overall-label">Всего попыток</span>
                            <span className="km-overall-value">{progress.total_attempts}</span>
                        </div>
                    </div>

                    {/* Topics detail table */}
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
                                    <tr key={score.topic_id || score.topic_number}>
                                        <td className="km-topic-num">{score.topic_number}</td>
                                        <td className="km-topic-title">{score.topic_title}</td>
                                        <td>
                                            <div className="km-progress-cell">
                                                <div className="km-progress-bar-wrapper">
                                                    <div
                                                        className="km-progress-bar"
                                                        style={{
                                                            width: `${Math.min(score.score_percent, 100)}%`,
                                                            backgroundColor: getScoreColor(score.score_percent),
                                                        }}
                                                    />
                                                </div>
                                                <span className="km-progress-text">
                                                    {Math.round(score.score_percent)}%
                                                </span>
                                            </div>
                                        </td>
                                        <td><TrendIcon trend={score.trend} /></td>
                                        <td className="km-attempts">{score.attempts_count}</td>
                                    </tr>
                                ))}
                            </tbody>
                        </table>
                    </div>
                </>
            ) : null}
        </div>
    );
};

export default KnowledgeMapPanel;
