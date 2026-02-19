import React, { useState, useEffect, useCallback } from 'react';
import { apiClient } from '../../apiService';
import { useAuth } from '../../auth';
import { useNavigate } from 'react-router-dom';
import './OlgaCourseAdmin.css';

/**
 * OlgaCourseAdmin — панель управления курсами для Ольги (teacher/admin).
 * Загрузка обложек, видео уроков, редактирование контента.
 */
const OlgaCourseAdmin = () => {
  const { user } = useAuth();
  const navigate = useNavigate();
  const [courses, setCourses] = useState([]);
  const [loading, setLoading] = useState(true);
  const [expandedCourse, setExpandedCourse] = useState(null);
  const [uploading, setUploading] = useState({});
  const [videoDrafts, setVideoDrafts] = useState({});
  const [message, setMessage] = useState(null);

  const loadCourses = useCallback(async () => {
    try {
      const res = await apiClient.get('courses/');
      setCourses(res.data.results || res.data || []);
    } catch (err) {
      console.error('Ошибка загрузки:', err);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    // Только teacher/admin
    if (user && !['teacher', 'admin'].includes(user.role)) {
      navigate('/olga/courses');
      return;
    }
    loadCourses();
  }, [user, navigate, loadCourses]);

  const showMessage = (text, type = 'success') => {
    setMessage({ text, type });
    setTimeout(() => setMessage(null), 3000);
  };

  const handleCoverUpload = async (courseId, file) => {
    if (!file) return;
    const key = `cover-${courseId}`;
    setUploading(prev => ({ ...prev, [key]: true }));

    const formData = new FormData();
    formData.append('cover', file);

    try {
      const res = await apiClient.post(`courses/${courseId}/upload-cover/`, formData, {
        headers: { 'Content-Type': 'multipart/form-data' },
      });
      showMessage(`Обложка загружена!`);
      // Обновляем в списке
      setCourses(prev => prev.map(c =>
        c.id === courseId ? { ...c, cover_url: res.data.cover_url } : c
      ));
    } catch (err) {
      showMessage(err.response?.data?.error || 'Ошибка загрузки обложки', 'error');
    } finally {
      setUploading(prev => ({ ...prev, [key]: false }));
    }
  };

  const handleVideoLinkSave = async (courseId, lessonId) => {
    const key = `video-link-${lessonId}`;
    const videoUrl = (videoDrafts[lessonId] || '').trim();
    setUploading(prev => ({ ...prev, [key]: true }));

    try {
      await apiClient.patch(`course-lessons/${lessonId}/`, { video_url: videoUrl });
      showMessage('Ссылка на видео сохранена');
      loadCourseDetail(courseId);
    } catch (err) {
      showMessage(err.response?.data?.error || 'Ошибка сохранения ссылки', 'error');
    } finally {
      setUploading(prev => ({ ...prev, [key]: false }));
    }
  };

  const loadCourseDetail = async (courseId) => {
    try {
      const res = await apiClient.get(`courses/${courseId}/`);
      setCourses(prev => prev.map(c =>
        c.id === courseId ? res.data : c
      ));
    } catch (err) {
      console.error('Ошибка загрузки деталей:', err);
    }
  };

  const toggleExpand = (courseId) => {
    if (expandedCourse === courseId) {
      setExpandedCourse(null);
    } else {
      setExpandedCourse(courseId);
      loadCourseDetail(courseId);
    }
  };

  if (loading) {
    return (
      <div className="olga-admin-loading">
        <div className="olga-spinner" />
        <p>Загрузка...</p>
      </div>
    );
  }

  return (
    <div className="olga-admin">
      <div className="olga-admin-header">
        <h1>Управление курсами</h1>
        <p className="olga-admin-subtitle">Загрузка обложек и настройка ссылок на видео</p>
      </div>

      {message && (
        <div className={`olga-admin-message ${message.type}`}>
          {message.text}
        </div>
      )}

      <div className="olga-admin-courses">
        {courses.map(course => (
          <div key={course.id} className="olga-admin-course-card">
            <div className="olga-admin-course-top" onClick={() => toggleExpand(course.id)}>
              <div className="olga-admin-course-cover">
                {course.cover_url ? (
                  <img src={course.cover_url} alt="" />
                ) : (
                  <div className="olga-admin-no-cover">Фото</div>
                )}
              </div>
              <div className="olga-admin-course-info">
                <h3>{course.title}</h3>
                <p>{course.short_description}</p>
                <span className="olga-admin-meta">
                  {course.lessons_count} уроков · {course.price} ₽
                </span>
              </div>
              <span className={`olga-admin-expand ${expandedCourse === course.id ? 'open' : ''}`}>
                ▸
              </span>
            </div>

            {/* Загрузка обложки */}
            <div className="olga-admin-cover-upload">
              <label className="olga-upload-btn">
                {uploading[`cover-${course.id}`] ? 'Загрузка...' : 'Загрузить обложку'}
                <input
                  type="file"
                  accept="image/jpeg,image/png,image/webp"
                  hidden
                  onChange={(e) => handleCoverUpload(course.id, e.target.files[0])}
                  disabled={uploading[`cover-${course.id}`]}
                />
              </label>
              {course.cover_url && (
                <span className="olga-admin-cover-status">✓ Обложка загружена</span>
              )}
            </div>

            {/* Уроки (раскрываемая секция) */}
            {expandedCourse === course.id && course.lessons && (
              <div className="olga-admin-lessons">
                <h4>Уроки курса</h4>
                {course.lessons.map((lesson, idx) => (
                  <div key={lesson.id} className="olga-admin-lesson-row">
                    <div className="olga-admin-lesson-info">
                      <span className="olga-admin-lesson-num">{idx + 1}</span>
                      <span className="olga-admin-lesson-title">{lesson.title}</span>
                      {lesson.video_provider === 'kinescope' && lesson.video_status === 'ready' && (
                        <span className="olga-admin-video-ok">Kinescope</span>
                      )}
                      {lesson.video_provider === 'kinescope' && lesson.video_status === 'processing' && (
                        <span className="olga-admin-video-ok" style={{ color: '#ff9800' }}>Обрабатывается</span>
                      )}
                      {lesson.video_provider === 'kinescope' && lesson.video_status === 'error' && (
                        <span className="olga-admin-video-ok" style={{ color: '#f44336' }}>Ошибка</span>
                      )}
                      {lesson.video_provider !== 'kinescope' && lesson.video_url && (
                        <span className="olga-admin-video-ok">Ссылка задана</span>
                      )}
                    </div>
                    <input
                      type="url"
                      className="olga-admin-video-input"
                      placeholder="https://..."
                      value={videoDrafts[lesson.id] ?? lesson.video_url ?? ''}
                      onChange={(e) => setVideoDrafts(prev => ({ ...prev, [lesson.id]: e.target.value }))}
                    />
                    <button
                      type="button"
                      className="olga-upload-btn small"
                      onClick={() => handleVideoLinkSave(course.id, lesson.id)}
                      disabled={uploading[`video-link-${lesson.id}`]}
                    >
                      {uploading[`video-link-${lesson.id}`] ? '...' : 'Сохранить'}
                    </button>
                  </div>
                ))}
              </div>
            )}
          </div>
        ))}
      </div>
    </div>
  );
};

export default OlgaCourseAdmin;
