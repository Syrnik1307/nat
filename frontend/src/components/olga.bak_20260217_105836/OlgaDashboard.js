import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../../auth';
import { apiClient } from '../../apiService';
import './OlgaDashboard.css';

/**
 * OlgaDashboard — Личный кабинет ученика для тенанта «Ольга».
 *
 * Показывает:
 * 1. Секция «Мои курсы» — купленные курсы с кнопкой «Продолжить обучение»
 * 2. Секция «Все курсы» — полный каталог с возможностью покупки
 */
const OlgaDashboard = () => {
  const navigate = useNavigate();
  const { user } = useAuth();
  const [courses, setCourses] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    loadCourses();
  }, []);

  const loadCourses = async () => {
    setLoading(true);
    try {
      const res = await apiClient.get('courses/');
      setCourses(res.data.results || res.data || []);
    } catch (err) {
      console.error('Ошибка загрузки курсов:', err);
      setError('Не удалось загрузить курсы');
      setCourses(getDemoCourses());
    } finally {
      setLoading(false);
    }
  };

  const myCourses = courses.filter(c => c.has_access);
  const availableCourses = courses.filter(c => !c.has_access);

  const openCourse = (courseId) => {
    navigate(`/olga/courses/${courseId}`);
  };

  if (loading) {
    return (
      <div className="olga-dash">
        <div className="olga-dash-loading">
          <div className="olga-spinner" />
          <p>Загрузка...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="olga-dash">
      {/* Приветствие */}
      <div className="olga-dash-hero">
        <h1 className="olga-dash-title">
          Добро пожаловать{user?.first_name ? `, ${user.first_name}` : ''}!
        </h1>
        <p className="olga-dash-subtitle">
          Ваш личный кабинет — здесь все ваши курсы и обучение
        </p>
      </div>

      {/* ═══ Мои курсы ═══ */}
      <section className="olga-dash-section">
        <div className="olga-dash-section-header">
          <h2 className="olga-dash-section-title">
            <span className="olga-dash-icon">📚</span> Мои курсы
          </h2>
          {myCourses.length > 0 && (
            <span className="olga-dash-count">{myCourses.length}</span>
          )}
        </div>

        {myCourses.length === 0 ? (
          <div className="olga-dash-empty">
            <span className="olga-dash-empty-icon">✿</span>
            <p className="olga-dash-empty-text">У вас пока нет купленных курсов</p>
            <p className="olga-dash-empty-hint">Выберите курс из каталога ниже, чтобы начать обучение</p>
          </div>
        ) : (
          <div className="olga-dash-grid my-courses">
            {myCourses.map(course => (
              <div
                key={course.id}
                className="olga-dash-card purchased"
                onClick={() => openCourse(course.id)}
                role="button"
                tabIndex={0}
                onKeyDown={(e) => e.key === 'Enter' && openCourse(course.id)}
              >
                <div className="olga-dash-card-image">
                  {course.cover_url ? (
                    <img src={course.cover_url} alt={course.title} />
                  ) : (
                    <div className="olga-dash-card-placeholder">
                      <span>✿</span>
                    </div>
                  )}
                  <span className="olga-dash-badge purchased">Куплено</span>
                </div>
                <div className="olga-dash-card-body">
                  <h3 className="olga-dash-card-title">{course.title}</h3>
                  <p className="olga-dash-card-desc">
                    {course.short_description || course.description}
                  </p>
                  <div className="olga-dash-card-meta">
                    {course.lessons_count != null && (
                      <span className="olga-dash-meta-item">
                        📚 {course.lessons_count} {pluralize(course.lessons_count, 'урок', 'урока', 'уроков')}
                      </span>
                    )}
                    {course.duration && (
                      <span className="olga-dash-meta-item">⏱ {course.duration}</span>
                    )}
                  </div>
                  {/* Прогресс, если есть */}
                  {course.progress != null && (
                    <div className="olga-dash-progress">
                      <div className="olga-dash-progress-bar">
                        <div
                          className="olga-dash-progress-fill"
                          style={{ width: `${Math.min(course.progress, 100)}%` }}
                        />
                      </div>
                      <span className="olga-dash-progress-text">
                        {Math.round(course.progress)}% пройдено
                      </span>
                    </div>
                  )}
                  <button className="olga-dash-continue-btn" onClick={(e) => { e.stopPropagation(); openCourse(course.id); }}>
                    Продолжить обучение →
                  </button>
                </div>
              </div>
            ))}
          </div>
        )}
      </section>

      {/* ═══ Все курсы (каталог) ═══ */}
      {availableCourses.length > 0 && (
        <section className="olga-dash-section">
          <div className="olga-dash-section-header">
            <h2 className="olga-dash-section-title">
              <span className="olga-dash-icon">✨</span> Доступные курсы
            </h2>
          </div>

          <div className="olga-dash-grid available-courses">
            {availableCourses.map(course => (
              <div
                key={course.id}
                className="olga-dash-card available"
                onClick={() => openCourse(course.id)}
                role="button"
                tabIndex={0}
                onKeyDown={(e) => e.key === 'Enter' && openCourse(course.id)}
              >
                <div className="olga-dash-card-image">
                  {course.cover_url ? (
                    <img src={course.cover_url} alt={course.title} />
                  ) : (
                    <div className="olga-dash-card-placeholder">
                      <span>✿</span>
                    </div>
                  )}
                  {course.price && (
                    <span className="olga-dash-badge price">{course.price} ₽</span>
                  )}
                </div>
                <div className="olga-dash-card-body">
                  <h3 className="olga-dash-card-title">{course.title}</h3>
                  <p className="olga-dash-card-desc">
                    {course.short_description || course.description}
                  </p>
                  <div className="olga-dash-card-meta">
                    {course.lessons_count != null && (
                      <span className="olga-dash-meta-item">
                        📚 {course.lessons_count} {pluralize(course.lessons_count, 'урок', 'урока', 'уроков')}
                      </span>
                    )}
                    {course.duration && (
                      <span className="olga-dash-meta-item">⏱ {course.duration}</span>
                    )}
                  </div>
                  <button className="olga-dash-buy-btn" onClick={(e) => { e.stopPropagation(); openCourse(course.id); }}>
                    Подробнее →
                  </button>
                </div>
              </div>
            ))}
          </div>
        </section>
      )}

      {error && courses.length === 0 && (
        <div className="olga-dash-error">
          <p>{error}</p>
        </div>
      )}
    </div>
  );
};

/** Плюрализация для русского языка */
function pluralize(n, one, few, many) {
  const abs = Math.abs(n) % 100;
  const lastDigit = abs % 10;
  if (abs > 10 && abs < 20) return many;
  if (lastDigit > 1 && lastDigit < 5) return few;
  if (lastDigit === 1) return one;
  return many;
}

/** Демо-данные */
function getDemoCourses() {
  return [
    {
      id: 'demo-1',
      title: 'Основы лепки фарфоровых роз',
      short_description: 'Научитесь создавать реалистичные розы из холодного фарфора.',
      cover_url: null,
      price: 4900,
      has_access: false,
      lessons_count: 12,
      duration: '6 часов',
    },
    {
      id: 'demo-2',
      title: 'Полевые цветы',
      short_description: 'Ромашки, васильки, маки — создаём букет полевых цветов.',
      cover_url: null,
      price: 3900,
      has_access: true,
      lessons_count: 8,
      duration: '4 часа',
      progress: 35,
    },
    {
      id: 'demo-3',
      title: 'Пионы и ранункулюсы',
      short_description: 'Сложные многолепестковые цветы. Техника раскатки и сборки.',
      cover_url: null,
      price: 6500,
      has_access: false,
      lessons_count: 15,
      duration: '8 часов',
    },
  ];
}

export default OlgaDashboard;
