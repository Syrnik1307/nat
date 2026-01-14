import React, { useState } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import { useAuth } from '../../../auth';
import { HomeworkConstructor } from '../index';
import SubmissionsList from './teacher/SubmissionsList';
import GradedSubmissionsList from './teacher/GradedSubmissionsList';
import TemplatesList from './teacher/TemplatesList';
import './HomeworkPage.css';

/**
 * Главная страница домашних заданий с четырьмя вкладками:
 * 1. Конструктор - создание/редактирование ДЗ
 * 2. Шаблоны - библиотека шаблонов для повторного использования
 * 3. ДЗ на проверку - очереди для преподавателя
 * 4. Проверенные ДЗ - архив проверенных работ
 */
const HomeworkPage = () => {
  const { role } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  
  // Определяем активную вкладку из URL или по умолчанию
  const getActiveTabFromPath = () => {
    if (location.pathname.includes('/homework/templates')) return 'templates';
    if (location.pathname.includes('/homework/to-review')) return 'review';
    if (location.pathname.includes('/homework/graded')) return 'graded';
    return 'constructor';
  };
  
  const [activeTab, setActiveTab] = useState(getActiveTabFromPath());

  const handleTabChange = (tab) => {
    setActiveTab(tab);
    // Обновляем URL при смене вкладки
    if (tab === 'constructor') {
      navigate('/homework/constructor', { replace: true });
    } else if (tab === 'templates') {
      navigate('/homework/templates', { replace: true });
    } else if (tab === 'review') {
      navigate('/homework/to-review', { replace: true });
    } else if (tab === 'graded') {
      navigate('/homework/graded', { replace: true });
    }
  };

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
        >
          <span className="tab-icon">✏️</span>
          <span className="tab-label">Конструктор</span>
        </button>
        <button
          className={`homework-tab ${activeTab === 'templates' ? 'active' : ''}`}
          onClick={() => handleTabChange('templates')}
        >
          <span className="tab-icon">📋</span>
          <span className="tab-label">Шаблоны</span>
        </button>
        <button
          className={`homework-tab ${activeTab === 'review' ? 'active' : ''}`}
          onClick={() => handleTabChange('review')}
        >
          <span className="tab-icon">📥</span>
          <span className="tab-label">На проверку</span>
        </button>
        <button
          className={`homework-tab ${activeTab === 'graded' ? 'active' : ''}`}
          onClick={() => handleTabChange('graded')}
        >
          <span className="tab-icon">✅</span>
          <span className="tab-label">Проверенные</span>
        </button>
      </div>

      {/* Контент вкладок */}
      <div className="homework-content">
        {activeTab === 'constructor' && <HomeworkConstructor />}
        {activeTab === 'templates' && <TemplatesList />}
        {activeTab === 'review' && <SubmissionsList filterStatus="submitted" />}
        {activeTab === 'graded' && <GradedSubmissionsList />}
      </div>
    </div>
  );
};

export default HomeworkPage;
