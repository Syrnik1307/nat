/**
 * GroupDetailModal.js
 * Модальное окно с подробной информацией о группе
 * Содержит табы: Журнал посещений, ДЗ, Контроль, Рейтинг, Отчеты
 */

import React, { useState } from 'react';
import './GroupDetailModal.css';

import AttendanceLogTab from './tabs/AttendanceLogTab';
import HomeworkTab from './tabs/HomeworkTab';
import GroupRatingTab from './tabs/GroupRatingTab';
import GroupReportsTab from './tabs/GroupReportsTab';
import GroupAIReportsTab from './tabs/GroupAIReportsTab';
import GroupLessonReportsTab from './tabs/GroupLessonReportsTab';
import GroupAnalyticsSummaryTab from './tabs/GroupAnalyticsSummaryTab';

const GroupDetailModal = ({ group, isOpen, onClose, onStudentClick }) => {
  const [activeTab, setActiveTab] = useState('attendance');

  if (!isOpen || !group) {
    return null;
  }

  const tabs = [
    { id: 'attendance', label: 'Журнал посещений' },
    { id: 'homework', label: 'Домашние задания' },
    { id: 'control', label: 'Контрольные точки' },
    { id: 'rating', label: 'Рейтинг группы' },
    { id: 'reports', label: 'Отчеты' },
    { id: 'analytics-summary', label: 'Сводная аналитика' },
    { id: 'lesson-reports', label: 'Отчеты по урокам' },
    { id: 'ai-reports', label: 'AI-анализ ошибок' },
  ];

  const renderTabContent = () => {
    switch (activeTab) {
      case 'attendance':
        return (
          <AttendanceLogTab
            groupId={group.id}
            onStudentClick={onStudentClick}
          />
        );
      case 'rating':
        return (
          <GroupRatingTab
            groupId={group.id}
            onStudentClick={onStudentClick}
          />
        );
      case 'reports':
        return (
          <GroupReportsTab groupId={group.id} />
        );
      case 'analytics-summary':
        return (
           <GroupAnalyticsSummaryTab groupId={group.id} />
        );
      case 'lesson-reports':
        return (
          <GroupLessonReportsTab groupId={group.id} />
        );
      case 'homework':
        return (
          <HomeworkTab groupId={group.id} />
        );
      case 'ai-reports':
        return (
          <GroupAIReportsTab groupId={group.id} />
        );
      case 'control':
        return (
          <div className="tab-content">
            <div className="placeholder">
              Контрольные точки (интеграция с модулем аналитики)
            </div>
          </div>
        );
      default:
        return null;
    }
  };

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-content group-detail-modal" onClick={(e) => e.stopPropagation()}>
        {/* Заголовок модали */}
        <div className="modal-header">
          <div className="header-info">
            <h2 className="modal-title">{group.name}</h2>
            <span className="group-students-count">
              {(() => {
                const rawCount =
                  typeof group.student_count === 'number'
                    ? group.student_count
                    : typeof group.students_count === 'number'
                      ? group.students_count
                      : Array.isArray(group.students)
                        ? group.students.length
                        : 0;
                const count = Math.max(0, rawCount);

                const suffix =
                  count % 10 === 1 && count % 100 !== 11
                    ? ''
                    : count % 10 >= 2 && count % 10 <= 4 && (count % 100 < 10 || count % 100 >= 20)
                      ? 'а'
                      : 'ов';

                return `${count} ученик${suffix}`;
              })()}
            </span>
          </div>
          <button
            className="modal-close-btn"
            onClick={onClose}
            aria-label="Закрыть"
          >
            ✕
          </button>
        </div>

        {/* Табы навигация */}
        <div className="tabs-nav">
          {tabs.map((tab) => (
            <button
              key={tab.id}
              className={`tab-button ${activeTab === tab.id ? 'active' : ''}`}
              onClick={() => setActiveTab(tab.id)}
              title={tab.label}
            >
              {tab.label}
            </button>
          ))}
        </div>

        {/* Содержимое активного таба */}
        <div className="modal-body">
          {renderTabContent()}
        </div>
      </div>
    </div>
  );
};

export default GroupDetailModal;
