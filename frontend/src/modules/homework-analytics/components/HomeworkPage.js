import React, { useState, useCallback, useEffect, lazy, Suspense } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import { useAuth } from '../../../auth';
import { getTeacherStatsSummary } from '../../../apiService';
import { getCached } from '../../../utils/dataCache';
import './HomeworkPage.css';

// Ленивая загрузка вкладок для ускорения переключений
const loadHomeworkConstructor = () => import('../index').then((m) => ({ default: m.HomeworkConstructor }));
const loadSubmissionsList = () => import('./teacher/SubmissionsList');
const loadGradedSubmissionsList = () => import('./teacher/GradedSubmissionsList');
const loadMyHomeworksList = () => import('./teacher/MyHomeworksList');

const HomeworkConstructor = lazy(loadHomeworkConstructor);
const SubmissionsList = lazy(loadSubmissionsList);
const GradedSubmissionsList = lazy(loadGradedSubmissionsList);
const MyHomeworksList = lazy(loadMyHomeworksList);

/**
 * Главная страница домашних заданий с четырьмя вкладками:
 * 1. Конструктор - создание/редактирование ДЗ
 * 2. Мои ДЗ - управление созданными заданиями (редактировать, удалить, переназначить)
 * 3. ДЗ на проверку - очереди для преподавателя
 * 4. Проверенные ДЗ - архив проверенных работ
 */
const HomeworkPage = () => {
  const { role } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  
  // Определяем активную вкладку из URL или по умолчанию
  const getActiveTabFromPath = () => {
    if (location.pathname.includes('/homework/my')) return 'my';
    if (location.pathname.includes('/homework/to-review')) return 'review';
    if (location.pathname.includes('/homework/graded')) return 'graded';
    return 'constructor';
  };
  
  const [activeTab, setActiveTab] = useState(getActiveTabFromPath());
  const [pendingReviewCount, setPendingReviewCount] = useState(0);
  
  // Состояние для редактирования ДЗ
  const [editingHomework, setEditingHomework] = useState(null);
  const [isDuplicating, setIsDuplicating] = useState(false);

  const schedulePreload = (fn) => {
    if (typeof window !== 'undefined' && 'requestIdleCallback' in window) {
      window.requestIdleCallback(() => fn(), { timeout: 2000 });
    } else {
      setTimeout(fn, 100);
    }
  };

  // Предзагрузка всех вкладок в фоне для мгновенного переключения
  useEffect(() => {
    schedulePreload(loadHomeworkConstructor);
    schedulePreload(loadMyHomeworksList);
    schedulePreload(loadSubmissionsList);
    schedulePreload(loadGradedSubmissionsList);
  }, []);

  useEffect(() => {
    if (role !== 'teacher') return;

    let isMounted = true;
    const loadPending = async () => {
      try {
        // Use cached data with 30s TTL - deduplicates with NavBar/TeacherHomePage
        const statsData = await getCached('teacher:stats', async () => {
          const res = await getTeacherStatsSummary();
          return res.data;
        }, 30000);
        const pending = Number(statsData?.pending_submissions || 0);
        if (isMounted) setPendingReviewCount(pending);
      } catch (e) {
        if (isMounted) setPendingReviewCount(0);
      }
    };

    loadPending();
    const interval = setInterval(loadPending, 60000);
    return () => {
      isMounted = false;
      clearInterval(interval);
    };
  }, [role]);

  const handleTabChange = (tab) => {
    setActiveTab(tab);
    // Сбрасываем редактируемое ДЗ при переходе на другую вкладку
    if (tab !== 'constructor') {
      setEditingHomework(null);
      setIsDuplicating(false);
    }
    // Обновляем URL при смене вкладки
    if (tab === 'constructor') {
      navigate('/homework/constructor', { replace: true });
    } else if (tab === 'my') {
      navigate('/homework/my', { replace: true });
    } else if (tab === 'review') {
      navigate('/homework/to-review', { replace: true });
    } else if (tab === 'graded') {
      navigate('/homework/graded', { replace: true });
    }
  };

  // Обработчик редактирования/дублирования ДЗ
  const handleEditHomework = useCallback((homework, options = {}) => {
    setEditingHomework(homework);
    setIsDuplicating(options.duplicate || false);
    setActiveTab('constructor');
    navigate('/homework/constructor', { replace: true });
  }, [navigate]);

  // Только для преподавателей
  if (role !== 'teacher') {
    return (
      <div style={{ padding: '2rem', textAlign: 'center' }}>
        <p>Доступ только для преподавателей</p>
      </div>
    );
  }

  return (
    <div className="homework-page">
      <div className="homework-header">
        <h1 className="homework-title">Домашние задания</h1>
        <p className="homework-subtitle">Создавайте, назначайте и проверяйте работы учеников</p>
      </div>

      {/* Навигация по вкладкам */}
      <div className="homework-tabs">
        <button
          className={`homework-tab ${activeTab === 'constructor' ? 'active' : ''}`}
          onClick={() => handleTabChange('constructor')}
          onMouseEnter={() => schedulePreload(loadHomeworkConstructor)}
        >
          <span className="tab-label">Конструктор</span>
        </button>
        <button
          className={`homework-tab ${activeTab === 'my' ? 'active' : ''}`}
          onClick={() => handleTabChange('my')}
          onMouseEnter={() => schedulePreload(loadMyHomeworksList)}
        >
          <span className="tab-label">Мои ДЗ</span>
        </button>
        <button
          className={`homework-tab ${activeTab === 'review' ? 'active' : ''}`}
          onClick={() => handleTabChange('review')}
          onMouseEnter={() => schedulePreload(loadSubmissionsList)}
        >
          <span className="tab-label">На проверку</span>
          {pendingReviewCount > 0 && (
            <span className="tab-badge">{pendingReviewCount}</span>
          )}
        </button>
        <button
          className={`homework-tab ${activeTab === 'graded' ? 'active' : ''}`}
          onClick={() => handleTabChange('graded')}
          onMouseEnter={() => schedulePreload(loadGradedSubmissionsList)}
        >
          <span className="tab-label">Проверенные</span>
        </button>
      </div>

      {/* Контент вкладок */}
      <div className="homework-content">
        <Suspense fallback={<div className="homework-tab-loading">Загрузка раздела...</div>}>
          {activeTab === 'constructor' && (
            <HomeworkConstructor 
              editingHomework={editingHomework}
              isDuplicating={isDuplicating}
              onClearEditing={() => {
                setEditingHomework(null);
                setIsDuplicating(false);
              }}
            />
          )}
          {activeTab === 'my' && <MyHomeworksList onEditHomework={handleEditHomework} />}
          {activeTab === 'review' && <SubmissionsList filterStatus="submitted" />}
          {activeTab === 'graded' && <GradedSubmissionsList />}
        </Suspense>
      </div>
    </div>
  );
};

export default HomeworkPage;
