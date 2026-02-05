import React from 'react';

// Icons
const IconX = () => (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
        <line x1="18" y1="6" x2="6" y2="18"/>
        <line x1="6" y1="6" x2="18" y2="18"/>
    </svg>
);

const IconCalendar = () => (
    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
        <rect x="3" y="4" width="18" height="18" rx="2" ry="2"/>
        <line x1="16" y1="2" x2="16" y2="6"/>
        <line x1="8" y1="2" x2="8" y2="6"/>
        <line x1="3" y1="10" x2="21" y2="10"/>
    </svg>
);

const IconBook = () => (
    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
        <path d="M4 19.5A2.5 2.5 0 0 1 6.5 17H20"/>
        <path d="M6.5 2H20v20H6.5A2.5 2.5 0 0 1 4 19.5v-15A2.5 2.5 0 0 1 6.5 2z"/>
    </svg>
);

const IconUser = () => (
    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
        <path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"/>
        <circle cx="12" cy="7" r="4"/>
    </svg>
);

const IconPlay = () => (
    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
        <polygon points="5 3 19 12 5 21 5 3"/>
    </svg>
);

const IconEmpty = () => (
    <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
        <circle cx="12" cy="12" r="10"/>
        <path d="M8 14s1.5 2 4 2 4-2 4-2"/>
        <line x1="9" y1="9" x2="9.01" y2="9"/>
        <line x1="15" y1="9" x2="15.01" y2="9"/>
    </svg>
);

const ACTIVITY_CONFIG = {
    lesson_join: {
        label: 'Посещение занятия',
        icon: IconCalendar,
        iconClass: 'day-modal__activity-icon--lesson',
        weight: 10,
    },
    homework_submit: {
        label: 'Сдача домашнего задания',
        icon: IconBook,
        iconClass: 'day-modal__activity-icon--homework',
        weight: 5,
    },
    homework_start: {
        label: 'Начало домашнего задания',
        icon: IconBook,
        iconClass: 'day-modal__activity-icon--homework',
        weight: 2,
    },
    login: {
        label: 'Вход в систему',
        icon: IconUser,
        iconClass: 'day-modal__activity-icon--login',
        weight: 1,
    },
    recording_watch: {
        label: 'Просмотр записи',
        icon: IconPlay,
        iconClass: 'day-modal__activity-icon--recording',
        weight: 3,
    },
    answer_save: {
        label: 'Сохранение ответа',
        icon: IconBook,
        iconClass: 'day-modal__activity-icon--homework',
        weight: 1,
    },
    chat_message: {
        label: 'Сообщение в чат',
        icon: IconUser,
        iconClass: 'day-modal__activity-icon--login',
        weight: 2,
    },
    question_ask: {
        label: 'Вопрос учителю',
        icon: IconUser,
        iconClass: 'day-modal__activity-icon--login',
        weight: 3,
    },
};

/**
 * Форматирует дату в человекочитаемый формат
 */
function formatDate(dateStr) {
    const date = new Date(dateStr);
    const options = { 
        weekday: 'long', 
        year: 'numeric', 
        month: 'long', 
        day: 'numeric' 
    };
    return date.toLocaleDateString('ru-RU', options);
}

/**
 * ActivityDayModal - модальное окно с детальной информацией о дне
 */
function ActivityDayModal({ isOpen, onClose, dayData, activities }) {
    if (!isOpen || !dayData) return null;
    
    const handleOverlayClick = (e) => {
        if (e.target === e.currentTarget) {
            onClose();
        }
    };
    
    // Группируем активности по типу для отображения
    const groupedActivities = activities?.reduce((acc, activity) => {
        const type = activity.action_type;
        if (!acc[type]) {
            acc[type] = {
                ...ACTIVITY_CONFIG[type] || { label: type, iconClass: '' },
                count: 0,
                items: [],
            };
        }
        acc[type].count += 1;
        acc[type].items.push(activity);
        return acc;
    }, {}) || {};
    
    return (
        <div 
            className={`day-modal-overlay ${isOpen ? 'day-modal-overlay--visible' : ''}`}
            onClick={handleOverlayClick}
        >
            <div className="day-modal" role="dialog" aria-modal="true">
                <div className="day-modal__header">
                    <div>
                        <div className="day-modal__date">{formatDate(dayData.date)}</div>
                        <div className="day-modal__score">
                            {dayData.count} {dayData.count === 1 ? 'балл' : 
                                dayData.count > 1 && dayData.count < 5 ? 'балла' : 'баллов'}
                        </div>
                    </div>
                    <button className="day-modal__close" onClick={onClose} aria-label="Закрыть">
                        <IconX />
                    </button>
                </div>
                
                <div className="day-modal__content">
                    {Object.keys(groupedActivities).length > 0 ? (
                        <div className="day-modal__section">
                            <div className="day-modal__section-title">Активности</div>
                            <div className="day-modal__activity-list">
                                {Object.entries(groupedActivities).map(([type, data]) => {
                                    const Icon = data.icon || IconUser;
                                    return (
                                        <div key={type} className="day-modal__activity-item">
                                            <div className={`day-modal__activity-icon ${data.iconClass}`}>
                                                <Icon />
                                            </div>
                                            <div className="day-modal__activity-info">
                                                <div className="day-modal__activity-title">
                                                    {data.label}
                                                </div>
                                                <div className="day-modal__activity-meta">
                                                    {data.count > 1 ? `${data.count} раз` : '1 раз'}
                                                </div>
                                            </div>
                                            <div className="day-modal__activity-score">
                                                +{data.count * (data.weight || 1)}
                                            </div>
                                        </div>
                                    );
                                })}
                            </div>
                        </div>
                    ) : (
                        <div className="day-modal__empty">
                            <div className="day-modal__empty-icon">
                                <IconEmpty />
                            </div>
                            <div>Нет активности в этот день</div>
                        </div>
                    )}
                </div>
            </div>
        </div>
    );
}

export default ActivityDayModal;
