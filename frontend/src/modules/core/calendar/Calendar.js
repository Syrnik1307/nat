import React, { useState, useEffect, useMemo, useRef, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import FullCalendar from '@fullcalendar/react';
import dayGridPlugin from '@fullcalendar/daygrid';
import timeGridPlugin from '@fullcalendar/timegrid';
import interactionPlugin from '@fullcalendar/interaction';
import apiService from '../../../apiService';
import { Button, Modal, Badge, ConfirmModal } from '../../../shared/components';
import { useAuth } from '../../../auth';

const PALETTE = {
  primary: '#1e3a8a', // deep blue
  primaryDark: '#0f1f4b',
  primaryLight: '#3b82f6',
  secondary: '#e0e7ff',
  surface: '#f5f7ff',
  text: '#0f172a',
  muted: '#475569',
  success: '#22c55e',
  danger: '#ef4444',
  warning: '#f59e0b',
};

const formatStatus = (status) => {
  switch (status) {
    case 'in_progress':
      return 'Идет';
    case 'completed':
      return 'Завершено';
    case 'cancelled':
      return 'Отменено';
    default:
      return 'Запланировано';
  }
};

/**
 * Календарь занятий с тремя видами: месяц, неделя, день
 * Поддержка drag-and-drop для переноса занятий
 */
const Calendar = () => {
  const navigate = useNavigate();
  const { user } = useAuth();
  const userRole = user?.role || 'student';
  const isStudent = userRole === 'student';
  const [view, setView] = useState('timeGridWeek'); // 'dayGridMonth' | 'timeGridWeek' | 'timeGridDay'
  const [events, setEvents] = useState([]);
  const [loading, setLoading] = useState(true);
  const [selectedEvent, setSelectedEvent] = useState(null);
  const [showEventModal, setShowEventModal] = useState(false);
  const calendarRef = useRef(null);
  const [confirmModal, setConfirmModal] = useState({ isOpen: false, title: '', message: '', onConfirm: null, confirmText: 'Да, удалить', cancelText: 'Отмена', variant: 'danger' });
  const [alertModal, setAlertModal] = useState({ isOpen: false, title: '', message: '', confirmText: 'ОК', variant: 'info' });

  // Загрузка занятий
  const loadLessons = useCallback(async () => {
    setLoading(true);
    try {
      // Получаем диапазон дат: текущий месяц + 2 месяца вперед
      const now = new Date();
      const startDate = new Date(now.getFullYear(), now.getMonth(), 1);
      const endDate = new Date(now.getFullYear(), now.getMonth() + 3, 0);
      
      const startISOString = startDate.toISOString().split('T')[0];
      const endISOString = endDate.toISOString().split('T')[0];

      const response = await apiService.get('/schedule/lessons/', {
        params: {
          include_recurring: true,
          start: startISOString,
          end: endISOString,
        }
      });
      
      const resolveColor = (status) => {
        switch (status) {
          case 'scheduled':
            return PALETTE.primary;
          case 'in_progress':
            return PALETTE.primaryDark;
          case 'completed':
            return PALETTE.success;
          case 'cancelled':
            return PALETTE.danger;
          default:
            return PALETTE.primary;
        }
      };
      
      // Обработка ответа (может быть массив или пагинированный объект)
      const lessons = Array.isArray(response.data) ? response.data : (response.data.results || []);
      
      const formattedEvents = lessons.map(lesson => {
        const color = resolveColor(lesson.status || 'scheduled');
        return {
          id: lesson.id,
          title: lesson.group_name || lesson.title,
          start: lesson.start_time,
          end: lesson.end_time,
          backgroundColor: color,
          borderColor: color,
          extendedProps: {
            group: lesson.group,
            group_name: lesson.group_name,
            zoom_join_url: lesson.zoom_join_url,
            status: lesson.status,
            description: lesson.description,
            is_recurring: lesson.is_recurring || false,
            recurring_lesson_id: lesson.recurring_lesson_id || null,
            recording_id: lesson.recording_id || null,
            homework_id: lesson.homework_id || null,
          },
        };
      });
      setEvents(formattedEvents);
    } catch (error) {
      console.error('Ошибка загрузки занятий:', error);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadLessons();
  }, [loadLessons]);

  useEffect(() => {
    if (calendarRef.current) {
      calendarRef.current.getApi().changeView(view);
    }
  }, [view]);

  const groupOptions = useMemo(() => {
    const map = new Map();
    events.forEach(evt => {
      const groupId = evt.extendedProps?.group;
      if (!groupId) return;
      if (!map.has(groupId)) {
        map.set(groupId, {
          id: groupId,
          name: evt.extendedProps?.group_name || `Группа ${groupId}`,
          count: 1,
        });
      } else {
        const current = map.get(groupId);
        map.set(groupId, { ...current, count: current.count + 1 });
      }
    });
    return Array.from(map.values()).sort((a, b) => a.name.localeCompare(b.name));
  }, [events]);

  const filteredEvents = useMemo(() => {
    return events;
  }, [events]);


  // Клик на занятие
  const handleEventClick = (info) => {
    setSelectedEvent({
      id: info.event.id,
      title: info.event.title,
      start: info.event.start,
      end: info.event.end,
      ...info.event.extendedProps,
    });
    setShowEventModal(true);
  };

  // Клик на дату (редирект на регулярные занятия)
  const handleDateClick = (info) => {
    navigate('/recurring-lessons/manage');
  };

  // Перетаскивание занятия
  const handleEventDrop = async (info) => {
    try {
      await apiService.patch(`/schedule/lessons/${info.event.id}/`, {
        start_time: info.event.start.toISOString(),
        end_time: info.event.end.toISOString(),
      });
    } catch (error) {
      console.error('Ошибка переноса занятия:', error);
      info.revert(); // Откатить изменения при ошибке
    }
  };

  // Изменение размера занятия
  const handleEventResize = async (info) => {
    try {
      await apiService.patch(`/schedule/lessons/${info.event.id}/`, {
        end_time: info.event.end.toISOString(),
      });
    } catch (error) {
      console.error('Ошибка изменения длительности:', error);
      info.revert();
    }
  };

  // Создание нового занятия - удалено, теперь редирект на регулярные
  const handleCreateLesson = async () => {
    // Это не используется больше
  };

  // Удаление занятия
  const handleDeleteLesson = async (lesson) => {
    const isRecurring = lesson?.is_recurring || (typeof lesson?.id === 'string' && lesson.id.startsWith('recurring-'));
    const recurringIdFromString = isRecurring && typeof lesson?.id === 'string' ? lesson.id.split('-')[1] : null;
    const recurringId = lesson?.recurring_lesson_id || recurringIdFromString;
    const targetTitle = isRecurring ? 'Удалить серию занятий' : 'Удалить занятие';
    const targetMessage = isRecurring
      ? 'Это повторяющееся занятие. Будет удалена вся серия. Продолжить?'
      : 'Вы уверены, что хотите удалить это занятие? Это действие нельзя отменить.';

    setConfirmModal({
      isOpen: true,
      title: targetTitle,
      message: targetMessage,
      confirmText: isRecurring ? 'Удалить серию' : 'Удалить',
      cancelText: 'Отмена',
      variant: 'danger',
      onConfirm: async () => {
        try {
          if (isRecurring) {
            if (!recurringId) {
              throw new Error('Recurring lesson id is missing');
            }
            await apiService.delete(`/recurring-lessons/${recurringId}/`);
          } else {
            await apiService.delete(`/schedule/lessons/${lesson.id}/`);
          }
          setShowEventModal(false);
          setConfirmModal(prev => ({ ...prev, isOpen: false }));
          loadLessons();
          setAlertModal({
            isOpen: true,
            title: isRecurring ? 'Серия удалена' : 'Занятие удалено',
            message: isRecurring ? 'Серия регулярных занятий удалена.' : 'Занятие успешно удалено из календаря.',
            confirmText: 'ОК',
            variant: 'info'
          });
        } catch (error) {
          console.error('Ошибка удаления занятия:', error);
          setConfirmModal(prev => ({ ...prev, isOpen: false }));
          setAlertModal({ isOpen: true, title: 'Ошибка', message: 'Не удалось удалить занятие. Попробуйте позже.', confirmText: 'Понятно', variant: 'danger' });
        }
      }
    });
  };

  return (
    <div className="calendar-shell">
      <div className="calendar-header">
        <div className="calendar-title">
          <h1>Календарь занятий</h1>
          <p>Следите за нагрузкой групп и управляйте расписанием в едином окне</p>
        </div>
        <div className="calendar-header-actions">
          <div className="view-toggle" role="tablist" aria-label="Переключение вида календаря">
            {[
              { id: 'dayGridMonth', label: 'Месяц' },
              { id: 'timeGridWeek', label: 'Неделя' },
              { id: 'timeGridDay', label: 'День' },
            ].map(option => (
              <button
                key={option.id}
                type="button"
                role="tab"
                aria-selected={view === option.id}
                className={view === option.id ? 'active' : ''}
                onClick={() => setView(option.id)}
              >
                {option.label}
              </button>
            ))}
          </div>
          <Button
            variant="secondary"
            size="small"
            onClick={() => navigate('/calendar/settings')}
            className="calendar-settings-btn"
          >
            Добавить в календарь
          </Button>
        </div>
      </div>

      {/* Подсказка о синхронизации с телефоном */}
      {!localStorage.getItem('lectio_connected_calendar') && !localStorage.getItem('lectio_sync_tip_hidden') && (
        <div className="calendar-sync-tip">
          <span className="calendar-sync-tip-text">
            <strong>Совет:</strong> Добавьте расписание в свой календарь для автоматической синхронизации
          </span>
          <button 
            className="calendar-sync-tip-close"
            onClick={() => {
              localStorage.setItem('lectio_sync_tip_hidden', 'true');
              window.location.reload();
            }}
            aria-label="Закрыть подсказку"
          >
            ✕
          </button>
        </div>
      )}

      <div className="calendar-layout" style={{ gridTemplateColumns: '1fr' }}>
        <div className="calendar-container">
          {loading ? (
            <div className="calendar-loading">Загрузка календаря...</div>
          ) : (
            <FullCalendar
              ref={calendarRef}
              plugins={[dayGridPlugin, timeGridPlugin, interactionPlugin]}
              initialView={view}
              headerToolbar={{
                left: 'prev,next today',
                center: 'title',
                right: ' ',
              }}
              events={filteredEvents}
              eventClick={handleEventClick}
              dateClick={handleDateClick}
              editable
              droppable
              eventDrop={handleEventDrop}
              eventResize={handleEventResize}
              locale="ru"
              height="auto"
              allDaySlot={false}
              slotDuration="00:30:00"
              slotLabelFormat={{ hour: '2-digit', minute: '2-digit', hour12: false }}
              slotMinTime="08:00:00"
              slotMaxTime="24:00:00"
              nowIndicator
              dayMaxEvents={4}
              eventTimeFormat={{ hour: '2-digit', minute: '2-digit', hour12: false }}
              eventDisplay="block"
              stickyHeaderDates
              buttonText={{
                today: 'Сегодня',
                month: 'Месяц',
                week: 'Неделя',
                day: 'День',
              }}
            />
          )}
        </div>
      </div>

      {/* Модальное окно просмотра занятия */}
      <Modal
        isOpen={showEventModal}
        onClose={() => setShowEventModal(false)}
        title="Информация о занятии"
        size="medium"
      >
        {selectedEvent && (
          <div className="tp-modal">
            <div className="tp-modal-header">
              <div>
                <p className="tp-eyebrow">Детали занятия</p>
                <h3 className="tp-modal-title">{selectedEvent.title}</h3>
              </div>
              <div className="tp-chip-row">
                <span className={`tp-chip tp-chip-${selectedEvent.status || 'scheduled'}`}>
                  {formatStatus(selectedEvent.status)}
                </span>
                {selectedEvent.is_recurring && (
                  <span className="tp-chip tp-chip-info">Повторяется</span>
                )}
              </div>
            </div>

            <div className="tp-meta">
              <div className="tp-meta-item">
                <span className="tp-meta-label">Время</span>
                <span className="tp-meta-value">
                  {new Date(selectedEvent.start).toLocaleString('ru-RU')}
                  {selectedEvent.end && ` — ${new Date(selectedEvent.end).toLocaleTimeString('ru-RU')}`}
                </span>
              </div>
              <div className="tp-meta-item">
                <span className="tp-meta-label">Группа</span>
                <span className="tp-meta-value">{selectedEvent.group_name}</span>
              </div>
            </div>

            {selectedEvent.description && (
              <div className="tp-section">
                <span className="tp-meta-label">Описание</span>
                <p className="tp-description">{selectedEvent.description}</p>
              </div>
            )}

            {/* Кнопки действий для урока */}
            {(() => {
              const now = new Date();
              const lessonEnd = selectedEvent.end ? new Date(selectedEvent.end) : new Date(selectedEvent.start);
              const isPast = lessonEnd < now;
              
              if (isStudent && isPast) {
                // Прошедший урок для студента: показываем запись и ДЗ (если есть)
                const hasRecording = !!selectedEvent.recording_id;
                const hasHomework = !!selectedEvent.homework_id;
                
                if (!hasRecording && !hasHomework) {
                  return null; // Нет ни записи, ни ДЗ
                }
                
                return (
                  <div className="tp-section tp-action-buttons">
                    {hasRecording && (
                      <Button
                        variant="secondary"
                        onClick={() => navigate(`/recordings/${selectedEvent.recording_id}`)}
                        style={{ flex: 1 }}
                      >
                        📹 Запись урока
                      </Button>
                    )}
                    {hasHomework && (
                      <Button
                        variant="secondary"
                        onClick={() => navigate(`/homework/${selectedEvent.homework_id}/solve`)}
                        style={{ flex: 1 }}
                      >
                        📝 Домашнее задание
                      </Button>
                    )}
                  </div>
                );
              } else if (!isPast && selectedEvent.zoom_join_url) {
                // Предстоящий/текущий урок с Zoom ссылкой
                return (
                  <div className="tp-section">
                    <Button
                      variant="primary"
                      onClick={() => window.open(selectedEvent.zoom_join_url, '_blank')}
                      style={{ width: '100%' }}
                    >
                      Присоединиться к Zoom
                    </Button>
                  </div>
                );
              } else if (!isPast && selectedEvent.google_meet_link) {
                // Предстоящий/текущий урок с Google Meet ссылкой
                return (
                  <div className="tp-section">
                    <Button
                      variant="primary"
                      onClick={() => window.open(selectedEvent.google_meet_link, '_blank')}
                      style={{ width: '100%', background: 'linear-gradient(135deg, #00ac47 0%, #00832d 100%)' }}
                    >
                      Присоединиться к Google Meet
                    </Button>
                  </div>
                );
              }
              return null;
            })()}

            <div className="tp-modal-footer">
              <Button
                variant="primary"
                onClick={() => setShowEventModal(false)}
                style={{ flex: 1 }}
              >
                Закрыть
              </Button>
              {!isStudent && (
                <Button
                  variant="danger"
                  onClick={() => handleDeleteLesson(selectedEvent)}
                  style={{ flex: 1 }}
                >
                  Удалить
                </Button>
              )}
            </div>
          </div>
        )}
      </Modal>

      {/* Модальное окно создания занятия */}
      {/* УДАЛЕНО: редирект на /recurring-lessons/manage */}

      <ConfirmModal
        isOpen={confirmModal.isOpen}
        onClose={() => setConfirmModal(prev => ({ ...prev, isOpen: false }))}
        onConfirm={confirmModal.onConfirm}
        title={confirmModal.title}
        message={confirmModal.message}
        confirmText={confirmModal.confirmText}
        cancelText={confirmModal.cancelText}
        variant={confirmModal.variant}
      />
      <ConfirmModal
        isOpen={alertModal.isOpen}
        onClose={() => setAlertModal(prev => ({ ...prev, isOpen: false }))}
        onConfirm={() => setAlertModal(prev => ({ ...prev, isOpen: false }))}
        title={alertModal.title}
        message={alertModal.message}
        confirmText={alertModal.confirmText}
        hideCancel
        variant={alertModal.variant}
      />

      <style>
        {`
          .calendar-shell {
            padding: 2rem;
            max-width: 1440px;
            margin: 0 auto;
            display: flex;
            flex-direction: column;
            gap: 1.75rem;
            position: relative;
            z-index: 1;
          }

          .calendar-header {
            display: flex;
            align-items: center;
            justify-content: space-between;
            gap: 1.5rem;
          }

          /* Sync Tip Banner */
          .calendar-sync-tip {
            display: flex;
            align-items: center;
            gap: 12px;
            background: linear-gradient(135deg, #fef3c7, #fde68a);
            border: 2px solid #f59e0b;
            border-radius: 14px;
            padding: 14px 18px;
            margin-bottom: -0.5rem;
          }

          .calendar-sync-tip-icon {
            font-size: 20px;
          }

          .calendar-sync-tip-text {
            flex: 1;
            font-size: 14px;
            color: #92400e;
          }

          .calendar-sync-tip-text strong {
            color: #78350f;
          }

          .calendar-sync-tip-close {
            background: transparent;
            border: none;
            font-size: 16px;
            color: #92400e;
            cursor: pointer;
            padding: 4px 8px;
            border-radius: 6px;
            transition: background 0.2s;
          }

          .calendar-sync-tip-close:hover {
            background: rgba(0,0,0,0.1);
          }

          .calendar-title h1 {
            margin: 0;
            font-size: 2rem;
            font-weight: 700;
            color: ${PALETTE.text};
          }

          .calendar-title p {
            margin: 0.25rem 0 0 0;
            color: #64748b;
            font-size: 0.95rem;
          }

          .calendar-header-actions {
            display: flex;
            align-items: center;
            gap: 1rem;
          }

          .view-toggle {
            display: inline-flex;
            background: ${PALETTE.secondary};
            padding: 0.25rem;
            border-radius: 999px;
            gap: 0.25rem;
          }

          .view-toggle button {
            border: none;
            background: transparent;
            color: ${PALETTE.text};
            font-weight: 600;
            font-size: 0.9rem;
            padding: 0.45rem 1.1rem;
            border-radius: 999px;
            cursor: pointer;
            transition: all 0.2s ease;
          }

          .view-toggle button.active {
            background: linear-gradient(135deg, ${PALETTE.primary}, ${PALETTE.primaryDark});
            color: white;
            box-shadow: 0 8px 16px -12px rgba(30, 58, 138, 0.65);
          }

          .calendar-layout {
            display: grid;
            grid-template-columns: 280px 1fr;
            gap: 1.5rem;
            align-items: start;
          }

          .calendar-sidebar {
            background: white;
            border-radius: 16px;
            box-shadow: 0 10px 25px -15px rgba(15, 23, 42, 0.25);
            padding: 1.25rem;
            display: flex;
            flex-direction: column;
            gap: 1rem;
          }

          .sidebar-header {
            display: flex;
            align-items: center;
            justify-content: space-between;
            font-weight: 600;
            color: #1e293b;
          }

          .sidebar-title {
            font-size: 1rem;
          }

          .group-list {
            display: flex;
            flex-direction: column;
            gap: 0.5rem;
            max-height: 420px;
            overflow-y: auto;
            padding-right: 0.25rem;
          }

          .group-item {
            border: none;
            background: transparent;
            display: flex;
            align-items: center;
            justify-content: space-between;
            border-radius: 12px;
            padding: 0.55rem 0.85rem;
            color: ${PALETTE.muted};
            font-size: 0.9rem;
            cursor: pointer;
            transition: all 0.2s ease;
          }

          .group-item:hover {
            background: rgba(30, 58, 138, 0.08);
            color: ${PALETTE.primary};
          }

          .group-item.active {
            background: linear-gradient(135deg, ${PALETTE.primary}, ${PALETTE.primaryDark});
            color: white;
            box-shadow: 0 12px 24px -12px rgba(30, 58, 138, 0.7);
          }

          .group-item.active .group-meta {
            color: white;
            background: rgba(255, 255, 255, 0.2);
          }

          .group-meta {
            display: inline-flex;
            align-items: center;
            justify-content: center;
            min-width: 32px;
            height: 28px;
            border-radius: 999px;
            background: #e2e8f0;
            font-weight: 600;
            font-size: 0.8rem;
            color: ${PALETTE.text};
          }

          .calendar-container {
            background: white;
            border-radius: 20px;
            box-shadow: 0 18px 40px -20px rgba(15, 23, 42, 0.35);
            padding: 1.5rem;
          }

          .calendar-loading {
            text-align: center;
            padding: 4rem 1rem;
            color: #64748b;
            font-size: 1rem;
          }

          /* FULLCALENDAR THEME */
          .fc {
            --fc-border-color: #e2e8f0;
            --fc-page-bg-color: ${PALETTE.surface};
            --fc-today-bg-color: rgba(30, 58, 138, 0.08);
            font-family: 'Inter', system-ui, -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
          }

          .fc .fc-toolbar.fc-header-toolbar {
            margin-bottom: 1.5rem;
          }

          /* Hide any extra toolbar chunk on the right (artifacts) */
          .calendar-container .fc .fc-toolbar .fc-toolbar-chunk:last-child {
            display: none !important;
          }
          /* Defensive: ensure only left (prev/next/today) and center (title) remain */
          .calendar-container .fc .fc-toolbar > .fc-toolbar-chunk:nth-child(n+3) {
            display: none !important;
          }

          .fc .fc-button-primary {
            background: linear-gradient(135deg, ${PALETTE.primary}, ${PALETTE.primaryDark});
            border: none;
            border-radius: 10px;
            box-shadow: 0 12px 24px -14px rgba(30, 58, 138, 0.65);
          }

          .fc .fc-button-primary:hover {
            background: linear-gradient(135deg, ${PALETTE.primaryDark}, ${PALETTE.primary});
          }

          .fc .fc-button-primary:disabled {
            background: #cbd5f5;
            color: #1e3a8a;
          }

          .fc .fc-daygrid-day-number {
            color: #1e293b;
            font-weight: 600;
          }

          .fc .fc-col-header-cell {
            background: #eef2ff;
            color: ${PALETTE.primaryDark};
            font-weight: 600;
            padding: 0.75rem 0;
          }

          .fc .fc-timegrid-axis-cushion {
            color: #64748b;
            font-weight: 500;
          }

          .fc .fc-timegrid-slot {
            height: 52px;
            background-image: linear-gradient(to right, rgba(148, 163, 184, 0.08) 0%, rgba(148, 163, 184, 0.02) 100%);
          }

          .fc .fc-timegrid-slot-lane:nth-child(odd) {
            background-color: rgba(148, 163, 184, 0.04);
          }

          .fc-theme-standard td, .fc-theme-standard th {
            border-color: #e2e8f0;
          }

          .fc .fc-timegrid-now-indicator-line {
            border-color: #ef4444;
          }

          .fc-event {
            cursor: pointer;
            border: none !important;
            border-radius: 14px !important;
            padding: 0.35rem 0.5rem !important;
            box-shadow: 0 12px 24px -16px rgba(30, 58, 138, 0.45);
          }

          .fc-event:hover {
            filter: brightness(1.05);
          }

          .fc-event .fc-event-time {
            font-weight: 600;
          }

          .fc-event .fc-event-title {
            font-size: 0.85rem;
            font-weight: 500;
            white-space: normal;
          }

          .fc .fc-daygrid-day-frame {
            padding: 0.5rem;
          }

          .fc .fc-daygrid-event-harness {
            margin-top: 0.35rem;
          }

          .fc .fc-timegrid-cols .fc-day-today .fc-timegrid-col-frame,
          .fc .fc-daygrid-day.fc-day-today {
            background: linear-gradient(180deg, rgba(59, 130, 246, 0.12), rgba(59, 130, 246, 0.05));
          }

          .fc .fc-scrollgrid {
            border-radius: 16px;
            overflow: hidden;
          }

          /* MODALS */
          .tp-modal {
            display: flex;
            flex-direction: column;
            gap: 1.25rem;
          }

          .tp-modal-header {
            display: flex;
            align-items: flex-start;
            justify-content: space-between;
            gap: 1rem;
          }

          .tp-eyebrow {
            margin: 0;
            text-transform: uppercase;
            letter-spacing: 0.08em;
            color: ${PALETTE.muted};
            font-size: 0.75rem;
            font-weight: 700;
          }

          .tp-modal-title {
            margin: 0.15rem 0 0 0;
            font-size: 1.35rem;
            font-weight: 700;
            color: ${PALETTE.text};
          }

          .tp-chip-row {
            display: flex;
            gap: 0.5rem;
            flex-wrap: wrap;
          }

          .tp-chip {
            display: inline-flex;
            align-items: center;
            padding: 0.4rem 0.9rem;
            border-radius: 999px;
            font-size: 0.88rem;
            font-weight: 700;
            background: rgba(30, 58, 138, 0.16);
            color: ${PALETTE.primaryDark};
            border: 1px solid rgba(30, 58, 138, 0.35);
          }

          .tp-chip-info {
            background: rgba(30, 58, 138, 0.18);
            color: ${PALETTE.primary};
            border-color: rgba(30, 58, 138, 0.45);
          }

          .tp-chip-scheduled { background: rgba(30, 58, 138, 0.18); color: ${PALETTE.primary}; border-color: rgba(30, 58, 138, 0.5); }
          .tp-chip-in_progress { background: rgba(59, 130, 246, 0.18); color: ${PALETTE.primaryDark}; border-color: rgba(59, 130, 246, 0.5); }
          .tp-chip-completed { background: rgba(34, 197, 94, 0.2); color: ${PALETTE.success}; border-color: ${PALETTE.success}; }
          .tp-chip-cancelled { background: rgba(239, 68, 68, 0.2); color: ${PALETTE.danger}; border-color: ${PALETTE.danger}; }

          .tp-meta {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 1rem;
            padding: 1rem;
            border: 1px solid #e2e8f0;
            border-radius: 14px;
            background: linear-gradient(135deg, rgba(30,58,138,0.04), rgba(30,58,138,0.02));
          }

          .tp-meta-item { display: flex; flex-direction: column; gap: 0.25rem; }
          .tp-meta-label { color: #64748b; font-size: 0.85rem; font-weight: 600; }
          .tp-meta-value { color: ${PALETTE.text}; font-weight: 600; }

          .tp-section { display: flex; flex-direction: column; gap: 0.35rem; }
          .tp-description { margin: 0; color: ${PALETTE.muted}; line-height: 1.55; }

          .tp-action-buttons {
            display: flex;
            flex-direction: row;
            gap: 0.75rem;
          }

          .tp-modal-footer {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(160px, 1fr));
            gap: 0.75rem;
            align-items: center;
          }

          /* Локально фиксируем стили кнопок модалки, чтобы всегда были как в дизайн-системе */
          .tp-modal-footer button,
          .tp-section button,
          .tp-action-buttons button {
            background: linear-gradient(135deg, #0b2b65 0%, #0a1f4d 100%);
            color: #ffffff;
            border: none;
            border-radius: 10px;
            padding: 0.7rem 1rem;
            font-weight: 700;
            font-family: 'Plus Jakarta Sans', sans-serif;
            font-size: 0.9rem;
            box-shadow: 0 8px 20px -10px rgba(30, 58, 138, 0.45);
            cursor: pointer;
            transition: all 0.2s ease;
          }

          .tp-modal-footer button:hover,
          .tp-section button:hover,
          .tp-action-buttons button:hover {
            background: linear-gradient(135deg, #103779 0%, #0c265b 100%);
            transform: translateY(-1px);
          }

          /* Опасная кнопка (удалить) */
          .tp-modal-footer button:nth-child(2) {
            background: linear-gradient(135deg, #ef4444 0%, #b91c1c 100%);
            box-shadow: 0 6px 16px -10px rgba(239, 68, 68, 0.45);
          }

          .tp-modal-footer button:nth-child(2):hover {
            background: linear-gradient(135deg, #dc2626 0%, #991b1b 100%);
          }

          .tp-form-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(240px, 1fr));
            gap: 1rem;
          }

          /* Confirm modal overrides (local) */
          .confirm-modal-content {
            border: 1px solid #e2e8f0;
            box-shadow: 0 16px 40px -24px rgba(15, 23, 42, 0.35);
            padding: 1.75rem;
          }

          .confirm-modal-btn-confirm {
            background: linear-gradient(135deg, ${PALETTE.primary}, ${PALETTE.primaryDark});
            box-shadow: 0 8px 20px -14px rgba(30, 58, 138, 0.4);
          }

          .confirm-modal-btn-danger {
            background: linear-gradient(135deg, ${PALETTE.danger}, '#b91c1c');
          }

          .confirm-modal-btn-cancel {
            border: 1px solid #e2e8f0;
          }

          @media (max-width: 1100px) {
            .calendar-layout {
              grid-template-columns: 1fr;
            }

            .calendar-sidebar {
              order: 2;
            }
          }

          @media (max-width: 768px) {
            .calendar-shell {
              padding: 1.25rem;
            }

            .calendar-header {
              flex-direction: column;
              align-items: flex-start;
            }

            .calendar-header-actions {
              width: 100%;
              justify-content: space-between;
            }

            .view-toggle {
              width: 100%;
            }

            .view-toggle button {
              flex: 1;
              text-align: center;
            }
          }
        `}
      </style>
    </div>
  );
};

export default Calendar;
