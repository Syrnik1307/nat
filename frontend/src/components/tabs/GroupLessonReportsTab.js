import React, { useState, useEffect } from 'react';
import { apiClient } from '../../apiService';
import LessonAnalyticsModal from '../../modules/Recordings/LessonAnalyticsModal';
import './GroupLessonReportsTab.css';

const GroupLessonReportsTab = ({ groupId }) => {
  const [lessons, setLessons] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [selectedLessonId, setSelectedLessonId] = useState(null);
  const [showAnalytics, setShowAnalytics] = useState(false);

  useEffect(() => {
    loadLessons();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [groupId]);

  const loadLessons = async () => {
    try {
      setLoading(true);
      // Fetch lessons for this group. 
      // We assume the API supports filtering by group_id and maybe ordering by date desc
      const response = await apiClient.get('/schedule/lessons/', {
        params: {
          group: groupId, // backend usually expects 'group' ID
          ordering: '-start_time',
          limit: 20 // Show last 20 lessons
        }
      });
      setLessons(response.data.results || response.data || []);
    } catch (err) {
      console.error('Failed to load lessons:', err);
      setError('Не удалось загрузить список уроков');
    } finally {
      setLoading(false);
    }
  };

  const handleOpenAnalytics = (lessonId) => {
    setSelectedLessonId(lessonId);
    setShowAnalytics(true);
  };

  if (loading) return <div className="tab-loading">Загрузка уроков...</div>;
  if (error) return <div className="tab-error">{error}</div>;

  return (
    <div className="group-lesson-reports-tab">
      <div className="tab-header">
        <h3 className="tab-title">Отчеты по урокам</h3>
        <p className="tab-description">
          Аналитика активности студентов на основе транскрипции Zoom встреч.
        </p>
      </div>

      <div className="lessons-list">
        {lessons.length === 0 ? (
          <div className="tab-empty">Уроков пока нет</div>
        ) : (
          lessons.map((lesson) => (
            <div key={lesson.id} className="lesson-report-item">
              <div className="lesson-info">
                <div className="lesson-date">
                  {new Date(lesson.start_time).toLocaleDateString('ru-RU')}
                </div>
                <div className="lesson-topic">
                  {lesson.topic || 'Без темы'}
                </div>
              </div>
              
              <button 
                className="report-btn"
                onClick={() => handleOpenAnalytics(lesson.id)}
              >
                📊 Открыть отчет
              </button>
            </div>
          ))
        )}
      </div>

      {showAnalytics && selectedLessonId && (
        <LessonAnalyticsModal
          isOpen={showAnalytics}
          onClose={() => setShowAnalytics(false)}
          lessonId={selectedLessonId}
        />
      )}
    </div>
  );
};

export default GroupLessonReportsTab;
