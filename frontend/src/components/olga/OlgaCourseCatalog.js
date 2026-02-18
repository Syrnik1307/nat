import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { apiClient } from '../../apiService';
import './OlgaCourseCatalog.css';

/**
 * OlgaCourseCatalog — каталог курсов тенанта Ольги.
 *
 * Показывает:
 * - Список курсов (карточки с обложкой, названием, описанием)
 * - Статус доступа: «Куплено» / «Купить»
 * - Фильтрация / поиск по курсам
 */
const OlgaCourseCatalog = () => {
  const navigate = useNavigate();
  const [courses, setCourses] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [search, setSearch] = useState('');

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
      // Показываем демо-данные при отсутствии API
      setCourses(getDemoCourses());
    } finally {
      setLoading(false);
    }
  };

  const filteredCourses = courses.filter(c =>
    c.title?.toLowerCase().includes(search.toLowerCase()) ||
    c.description?.toLowerCase().includes(search.toLowerCase())
  );

  const openCourse = (courseId) => {
    navigate(`/olga/courses/${courseId}`);
  };

  return (
    <div className="olga-catalog">
      {/* Шапка каталога */}
      <div className="olga-catalog-hero">
        <h1 className="olga-catalog-title">Курсы</h1>
        <p className="olga-catalog-subtitle">
          Авторские курсы по созданию фарфоровых цветов ручной работы
        </p>
      </div>

      {/* Поиск */}
      <div className="olga-catalog-controls">
        <div className="olga-search-wrap">
          <span className="olga-search-icon">🔍</span>
          <input
            type="text"
            className="olga-search-input"
            placeholder="Поиск по курсам..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
          />
        </div>
        <span className="olga-course-count">
          {filteredCourses.length} {pluralize(filteredCourses.length, 'курс', 'курса', 'курсов')}
        </span>
      </div>

      {/* Контент */}
      {loading ? (
        <div className="olga-catalog-loading">
          <div className="olga-spinner" />
          <p>Загрузка курсов...</p>
        </div>
      ) : error && courses.length === 0 ? (
        <div className="olga-catalog-empty">
          <p>{error}</p>
        </div>
      ) : filteredCourses.length === 0 ? (
        <div className="olga-catalog-empty">
          <span className="olga-empty-icon">✿</span>
          <p>Курсы не найдены</p>
        </div>
      ) : (
        <div className="olga-catalog-grid">
          {filteredCourses.map(course => (
            <div
              key={course.id}
              className="olga-course-card"
              onClick={() => openCourse(course.id)}
              role="button"
              tabIndex={0}
              onKeyDown={(e) => e.key === 'Enter' && openCourse(course.id)}
            >
              <div className="olga-course-image">
                {course.cover_url ? (
                  <img src={course.cover_url} alt={course.title} />
                ) : (
                  <div className="olga-course-placeholder">
                    <span>✿</span>
                  </div>
                )}
                {course.has_access && (
                  <span className="olga-course-badge purchased">Куплено</span>
                )}
                {!course.has_access && course.price && (
                  <span className="olga-course-badge price">{course.price} ₽</span>
                )}
              </div>
              <div className="olga-course-info">
                <h3 className="olga-course-title">{course.title}</h3>
                <p className="olga-course-desc">{course.short_description || course.description}</p>
                <div className="olga-course-meta">
                  {course.lessons_count != null && (
                    <span className="olga-meta-item">
                      📚 {course.lessons_count} {pluralize(course.lessons_count, 'урок', 'урока', 'уроков')}
                    </span>
                  )}
                  {course.duration && (
                    <span className="olga-meta-item">⏱ {course.duration}</span>
                  )}
                </div>
              </div>
            </div>
          ))}
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

/** Демо-данные для отображения при отсутствии бэкенда курсов */
function getDemoCourses() {
  return [
    {
      id: 'demo-1',
      title: 'Основы лепки фарфоровых роз',
      short_description: 'Научитесь создавать реалистичные розы из холодного фарфора. От простых бутонов до пышных соцветий.',
      cover_url: null,
      price: 4900,
      has_access: false,
      lessons_count: 12,
      duration: '6 часов',
    },
    {
      id: 'demo-2',
      title: 'Полевые цветы',
      short_description: 'Ромашки, васильки, маки — создаём букет полевых цветов с тонировкой масляными красками.',
      cover_url: null,
      price: 3900,
      has_access: true,
      lessons_count: 8,
      duration: '4 часа',
    },
    {
      id: 'demo-3',
      title: 'Пионы и ранункулюсы',
      short_description: 'Сложные многолепестковые цветы. Техника раскатки, сборки и тонировки пастелью.',
      cover_url: null,
      price: 6500,
      has_access: false,
      lessons_count: 15,
      duration: '8 часов',
    },
    {
      id: 'demo-4',
      title: 'Свадебный букет из фарфора',
      short_description: 'Создание композиции для особого случая: подбор цветов, каркас, сборка.',
      cover_url: null,
      price: 7900,
      has_access: false,
      lessons_count: 10,
      duration: '5 часов',
    },
  ];
}

export default OlgaCourseCatalog;
