/**
 * GroupDetailModal.js
 * Модальное окно с подробной информацией о группе
 * Содержит табы: Журнал посещений, Тесты, ДЗ, Контроль, Рейтинг, Отчеты
 */

import React, { useState } from 'react';
import './GroupDetailModal.css';

import AttendanceLogTab from './tabs/AttendanceLogTab';
import GroupRatingTab from './tabs/GroupRatingTab';
import GroupReportsTab from './tabs/GroupReportsTab';

const GroupDetailModal = ({ group, isOpen, onClose, onStudentClick }) => {
  const [activeTab, setActiveTab] = useState('attendance');
  const [error, setError] = useState(null);

  if (!isOpen || !group) {
    return null;
  }

  const tabs = [
    { id: 'attendance', label: 'Журнал посещений', icon: '📋' },
    { id: 'tests', label: 'Тесты на проверку', icon: '✓' },
    { id: 'homework', label: 'Домашние задания', icon: '📝' },
    { id: 'control', label: 'Контрольные точки', icon: '🎯' },
    { id: 'rating', label: 'Рейтинг группы', icon: '⭐' },
    { id: 'reports', label: 'Отчеты', icon: '📊' },
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
      case 'tests':
        return (
          <div className="tab-content">
            <div className="placeholder">
              📌 Тесты на проверку (интеграция с модулем ДЗ)
            </div>
          </div>
        );
      case 'homework':
        return (
          <div className="tab-content">
            <div className="placeholder">
              📌 Домашние задания (интеграция с модулем ДЗ)
            </div>
          </div>
        );
      case 'control':
        return (
          <div className="tab-content">
            <div className="placeholder">
              📌 Контрольные точки (интеграция с модулем аналитики)
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
              👥 {group.student_count || 0} ученик{
                (group.student_count || 0) % 10 === 1 && (group.student_count || 0) % 100 !== 11 ? '' :
                (group.student_count || 0) % 10 >= 2 && (group.student_count || 0) % 10 <= 4 && 
                ((group.student_count || 0) % 100 < 10 || (group.student_count || 0) % 100 >= 20) ? 'а' : 'ов'
              }
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
              <span className="tab-icon">{tab.icon}</span>
              <span className="tab-label">{tab.label}</span>
            </button>
          ))}
        </div>

        {/* Содержимое активного таба */}
        <div className="modal-body">
          {error && (
            <div className="error-message">
              ⚠️ {error}
            </div>
          )}
          {renderTabContent()}
        </div>
      </div>
    </div>
  );
};

export default GroupDetailModal;
