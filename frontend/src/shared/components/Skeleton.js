import React from 'react';
import './Skeleton.css';

/**
 * Универсальный Skeleton loader
 * Используется для показа структуры контента до загрузки
 */

// Базовый skeleton элемент
export const Skeleton = ({ 
  width, 
  height, 
  borderRadius, 
  className = '',
  style = {},
  variant = 'default' // 'default' | 'text' | 'title' | 'avatar' | 'card' | 'button'
}) => {
  const variantClass = variant !== 'default' ? `skeleton-${variant}` : '';
  
  return (
    <div 
      className={`skeleton ${variantClass} ${className}`}
      style={{
        width,
        height,
        borderRadius,
        ...style
      }}
    />
  );
};

// Skeleton для текстовой строки
export const SkeletonText = ({ lines = 1, className = '' }) => (
  <div className={`skeleton-text-block ${className}`}>
    {Array.from({ length: lines }).map((_, i) => (
      <div 
        key={i} 
        className="skeleton skeleton-text"
        style={{ 
          width: i === lines - 1 && lines > 1 ? '70%' : '100%',
          animationDelay: `${i * 80}ms`
        }}
      />
    ))}
  </div>
);

// Skeleton для карточки
export const SkeletonCard = ({ className = '', children }) => (
  <div className={`skeleton-card-wrapper ${className}`}>
    {children || (
      <>
        <Skeleton variant="title" style={{ marginBottom: '12px' }} />
        <SkeletonText lines={2} />
      </>
    )}
  </div>
);

// Skeleton для курса студента
export const SkeletonCourseCard = () => (
  <div className="skeleton-course-card">
    <div className="skeleton-course-top">
      <Skeleton className="skeleton-course-badge" width={48} height={48} borderRadius="12px" />
      <div className="skeleton-course-info">
        <Skeleton variant="title" width="60%" />
        <div className="skeleton-course-chips">
          <Skeleton width={120} height={24} borderRadius="6px" />
          <Skeleton width={80} height={24} borderRadius="6px" />
        </div>
      </div>
    </div>
  </div>
);

// Skeleton для баннера сегодняшнего дня
export const SkeletonTodayBanner = () => (
  <div className="skeleton-today-banner">
    <Skeleton width={140} height={20} borderRadius="6px" />
    <Skeleton width={200} height={20} borderRadius="6px" />
    <Skeleton width={100} height={36} borderRadius="12px" style={{ marginLeft: 'auto' }} />
  </div>
);

// Skeleton для урока
export const SkeletonLessonCard = () => (
  <div className="skeleton-lesson-card">
    <Skeleton width={80} height={40} borderRadius="8px" />
    <div className="skeleton-lesson-info">
      <Skeleton width="50%" height={20} borderRadius="6px" />
      <Skeleton width="30%" height={16} borderRadius="6px" />
    </div>
  </div>
);

// Full page loading с красивой анимацией
export const PageLoadingSkeleton = ({ title = 'Загрузка...' }) => (
  <div className="page-loading-skeleton">
    <div className="page-loading-spinner" />
    <p className="page-loading-text">{title}</p>
  </div>
);

// Красивый auth loader
export const AuthCheckingSkeleton = () => (
  <div className="auth-checking-skeleton">
    <div className="auth-checking-logo">
      <div className="auth-logo-pulse" />
    </div>
    <div className="auth-checking-text">Проверка авторизации</div>
    <div className="auth-checking-dots">
      <span />
      <span />
      <span />
    </div>
  </div>
);

// Student Dashboard Skeleton
export const StudentDashboardSkeleton = () => (
  <div className="student-dashboard-skeleton animate-page-enter">
    {/* Title skeleton */}
    <Skeleton 
      width="200px" 
      height="40px" 
      borderRadius="12px" 
      style={{ marginBottom: '24px' }}
    />
    
    {/* Today banner skeleton */}
    <SkeletonTodayBanner />
    
    {/* Courses section skeleton */}
    <div className="skeleton-courses-section">
      <div className="skeleton-section-header">
        <Skeleton width="150px" height="28px" borderRadius="8px" />
        <Skeleton width="100px" height={20} borderRadius="6px" />
      </div>
      
      <div className="skeleton-courses-grid">
        <SkeletonCourseCard />
        <SkeletonCourseCard />
      </div>
    </div>
  </div>
);

// Teacher Dashboard Skeleton
export const TeacherDashboardSkeleton = () => (
  <div className="teacher-dashboard-skeleton animate-page-enter">
    {/* Stats row skeleton */}
    <div className="skeleton-stats-row">
      <div className="skeleton-stat-card">
        <Skeleton width={40} height={40} borderRadius="12px" />
        <div className="skeleton-stat-info">
          <Skeleton width="50%" height={14} borderRadius="4px" />
          <Skeleton width="70%" height={24} borderRadius="6px" />
        </div>
      </div>
      <div className="skeleton-stat-card">
        <Skeleton width={40} height={40} borderRadius="12px" />
        <div className="skeleton-stat-info">
          <Skeleton width="60%" height={14} borderRadius="4px" />
          <Skeleton width="50%" height={24} borderRadius="6px" />
        </div>
      </div>
      <div className="skeleton-stat-card">
        <Skeleton width={40} height={40} borderRadius="12px" />
        <div className="skeleton-stat-info">
          <Skeleton width="45%" height={14} borderRadius="4px" />
          <Skeleton width="65%" height={24} borderRadius="6px" />
        </div>
      </div>
    </div>
    
    {/* Lessons section skeleton */}
    <div className="skeleton-section">
      <Skeleton width="180px" height={28} borderRadius="8px" style={{ marginBottom: '20px' }} />
      <div className="skeleton-lessons-list">
        <SkeletonLessonCard />
        <SkeletonLessonCard />
        <SkeletonLessonCard />
      </div>
    </div>
    
    {/* Groups section skeleton */}
    <div className="skeleton-section">
      <Skeleton width="140px" height={28} borderRadius="8px" style={{ marginBottom: '20px' }} />
      <div className="skeleton-groups-grid">
        <div className="skeleton-group-card">
          <Skeleton width="100%" height={80} borderRadius="12px" />
          <Skeleton width="70%" height={20} borderRadius="6px" style={{ marginTop: '12px' }} />
          <Skeleton width="40%" height={16} borderRadius="4px" style={{ marginTop: '8px' }} />
        </div>
        <div className="skeleton-group-card">
          <Skeleton width="100%" height={80} borderRadius="12px" />
          <Skeleton width="60%" height={20} borderRadius="6px" style={{ marginTop: '12px' }} />
          <Skeleton width="50%" height={16} borderRadius="4px" style={{ marginTop: '8px' }} />
        </div>
      </div>
    </div>
  </div>
);

// Homework List Skeleton
export const HomeworkListSkeleton = () => (
  <div className="homework-list-skeleton animate-page-enter">
    {/* Header */}
    <div className="skeleton-hw-header">
      <Skeleton width="180px" height={32} borderRadius="10px" />
      <Skeleton width="120px" height={40} borderRadius="12px" />
    </div>
    
    {/* Tabs */}
    <div className="skeleton-hw-tabs">
      <Skeleton width="100px" height={36} borderRadius="8px" />
      <Skeleton width="120px" height={36} borderRadius="8px" />
    </div>
    
    {/* Cards */}
    <div className="skeleton-hw-list">
      {[1, 2, 3].map(i => (
        <div key={i} className="skeleton-hw-card">
          <div className="skeleton-hw-card-header">
            <Skeleton width={48} height={48} borderRadius="12px" />
            <div className="skeleton-hw-card-info">
              <Skeleton width="70%" height={20} borderRadius="6px" />
              <Skeleton width="40%" height={16} borderRadius="4px" />
            </div>
            <Skeleton width="80px" height={28} borderRadius="14px" />
          </div>
          <div className="skeleton-hw-card-footer">
            <Skeleton width="100px" height={14} borderRadius="4px" />
            <Skeleton width="60px" height={14} borderRadius="4px" />
          </div>
        </div>
      ))}
    </div>
  </div>
);

export default Skeleton;
