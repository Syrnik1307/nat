import React, { useState, useEffect, useMemo, useRef, useCallback } from 'react';
import FullCalendar from '@fullcalendar/react';
import dayGridPlugin from '@fullcalendar/daygrid';
import timeGridPlugin from '@fullcalendar/timegrid';
import interactionPlugin from '@fullcalendar/interaction';
import apiService from '../../../apiService';
import { Button, Modal, Input, Badge, ConfirmModal } from '../../../shared/components';

/**
 * Календарь занятий с тремя видами: месяц, неделя, день
 * Поддержка drag-and-drop для переноса занятий
 */
const Calendar = () => {
  const [view, setView] = useState('timeGridWeek'); // 'dayGridMonth' | 'timeGridWeek' | 'timeGridDay'
  const [events, setEvents] = useState([]);
  const [loading, setLoading] = useState(true);
  const [selectedEvent, setSelectedEvent] = useState(null);
  const [showEventModal, setShowEventModal] = useState(false);
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [activeGroup, setActiveGroup] = useState('all');
  const calendarRef = useRef(null);
  const [confirmModal, setConfirmModal] = useState({ isOpen: false, title: '', message: '', onConfirm: null, confirmText: 'Да, удалить', cancelText: 'Отмена', variant: 'danger' });
  const [alertModal, setAlertModal] = useState({ isOpen: false, title: '', message: '', confirmText: 'ОК', variant: 'info' });

  // Форма создания занятия
  const [newEvent, setNewEvent] = useState({
    title: '',
    group: '',
    start: '',
    duration: 60,
    description: '',
  });

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
            return '#1d4ed8';
          case 'in_progress':
            return '#2563eb';
          case 'completed':
            return '#1e40af';
          case 'cancelled':
            return '#ef4444';
          default:
            return '#2563eb';
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
    if (activeGroup === 'all') {
      return events;
    }
    return events.filter(evt => evt.extendedProps?.group === activeGroup);
  }, [events, activeGroup]);


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

  // Клик на дату (создание нового занятия)
  const handleDateClick = (info) => {
    setNewEvent({
      ...newEvent,
      start: info.dateStr,
    });
    setShowCreateModal(true);
  };

  // Перетаскивание занятия
  const handleEventDrop = async (info) => {
    try {
      await apiService.patch(`/api/schedule/lessons/${info.event.id}/`, {
        start_time: info.event.start.toISOString(),
        end_time: info.event.end.toISOString(),
      });
      console.log('Занятие перенесено');
    } catch (error) {
      console.error('Ошибка переноса занятия:', error);
      info.revert(); // Откатить изменения при ошибке
    }
  };

  // Изменение размера занятия
  const handleEventResize = async (info) => {
    try {
      await apiService.patch(`/api/schedule/lessons/${info.event.id}/`, {
        end_time: info.event.end.toISOString(),
      });
      console.log('Длительность занятия изменена');
    } catch (error) {
      console.error('Ошибка изменения длительности:', error);
      info.revert();
    }
  };

  // Создание нового занятия
  const handleCreateLesson = async () => {
    try {
      const endTime = new Date(newEvent.start);
      endTime.setMinutes(endTime.getMinutes() + newEvent.duration);

      await apiService.post('/api/schedule/lessons/', {
        group: newEvent.group,
        start_time: newEvent.start,
        end_time: endTime.toISOString(),
        description: newEvent.description,
      });

      setShowCreateModal(false);
      setNewEvent({ title: '', group: '', start: '', duration: 60, description: '' });
      loadLessons();
    } catch (error) {
      console.error('Ошибка создания занятия:', error);
    }
  };

  // Удаление занятия
  const handleDeleteLesson = async (lessonId) => {
    setConfirmModal({
      isOpen: true,
      title: 'Удалить занятие',
      message: 'Вы уверены, что хотите удалить это занятие? Это действие нельзя отменить.',
      confirmText: 'Удалить',
      cancelText: 'Отмена',
      variant: 'danger',
      onConfirm: async () => {
        try {
          await apiService.delete(`/api/schedule/lessons/${lessonId}/`);
          setShowEventModal(false);
          setConfirmModal(prev => ({ ...prev, isOpen: false }));
          loadLessons();
          setAlertModal({ isOpen: true, title: 'Занятие удалено', message: 'Занятие успешно удалено из календаря.', confirmText: 'ОК', variant: 'info' });
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
          <Button variant="primary" onClick={() => setShowCreateModal(true)}>
            + Новое занятие
          </Button>
        </div>
      </div>

      <div className="calendar-layout">
        <aside className="calendar-sidebar" aria-label="Фильтр групп">
          <div className="sidebar-header">
            <span className="sidebar-title">Группы</span>
            <Badge variant="neutral">{groupOptions.length}</Badge>
          </div>
          <div className="group-list">
            <button
              type="button"
              className={`group-item ${activeGroup === 'all' ? 'active' : ''}`}
              onClick={() => setActiveGroup('all')}
            >
              <span className="group-name">Все группы</span>
              <span className="group-meta">{events.length}</span>
            </button>
            {groupOptions.map(group => (
              <button
                type="button"
                key={group.id}
                className={`group-item ${activeGroup === group.id ? 'active' : ''}`}
                onClick={() => setActiveGroup(group.id)}
              >
                <span className="group-name">{group.name}</span>
                <span className="group-meta">{group.count}</span>
              </button>
            ))}
          </div>
        </aside>

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
          <div>
            <div style={{ marginBottom: '1.5rem' }}>
              <h3 style={{ fontSize: '1.25rem', fontWeight: '600', marginBottom: '0.5rem' }}>
                {selectedEvent.title}
              </h3>
              <Badge variant={selectedEvent.status === 'scheduled' ? 'success' : 'neutral'}>
                {selectedEvent.status}
              </Badge>
            </div>

            <div style={{ marginBottom: '1rem' }}>
              <strong style={{ color: '#6b7280', fontSize: '0.875rem' }}>Группа:</strong>
              <div style={{ marginTop: '0.25rem' }}>{selectedEvent.group_name}</div>
            </div>

            <div style={{ marginBottom: '1rem' }}>
              <strong style={{ color: '#6b7280', fontSize: '0.875rem' }}>Время:</strong>
              <div style={{ marginTop: '0.25rem' }}>
                {new Date(selectedEvent.start).toLocaleString('ru-RU')}
                {selectedEvent.end && ` - ${new Date(selectedEvent.end).toLocaleTimeString('ru-RU')}`}
              </div>
            </div>

            {selectedEvent.description && (
              <div style={{ marginBottom: '1rem' }}>
                <strong style={{ color: '#6b7280', fontSize: '0.875rem' }}>Описание:</strong>
                <div style={{ marginTop: '0.25rem' }}>{selectedEvent.description}</div>
              </div>
            )}

            {selectedEvent.zoom_join_url && (
              <div style={{ marginBottom: '1.5rem' }}>
                <Button
                  variant="primary"
                  onClick={() => window.open(selectedEvent.zoom_join_url, '_blank')}
                  style={{ width: '100%' }}
                >
                  🎥 Присоединиться к Zoom
                </Button>
              </div>
            )}

            <div style={{ display: 'flex', gap: '0.75rem' }}>
              <Button
                variant="secondary"
                onClick={() => setShowEventModal(false)}
                style={{ flex: 1 }}
              >
                Закрыть
              </Button>
              <Button
                variant="danger"
                onClick={() => handleDeleteLesson(selectedEvent.id)}
                style={{ flex: 1 }}
              >
                Удалить
              </Button>
            </div>
          </div>
        )}
      </Modal>

      {/* Модальное окно создания занятия */}
      <Modal
        isOpen={showCreateModal}
        onClose={() => setShowCreateModal(false)}
        title="Создать новое занятие"
        size="medium"
      >
        <Input
          label="Группа (ID)"
          type="number"
          value={newEvent.group}
          onChange={(e) => setNewEvent({ ...newEvent, group: e.target.value })}
          placeholder="1"
          required
        />

        <Input
          label="Дата и время начала"
          type="datetime-local"
          value={newEvent.start}
          onChange={(e) => setNewEvent({ ...newEvent, start: e.target.value })}
          required
        />

        <Input
          label="Длительность (минуты)"
          type="number"
          value={newEvent.duration}
          onChange={(e) => setNewEvent({ ...newEvent, duration: parseInt(e.target.value) })}
          placeholder="60"
          required
        />

        <Input
          label="Описание (опционально)"
          type="textarea"
          value={newEvent.description}
          onChange={(e) => setNewEvent({ ...newEvent, description: e.target.value })}
          placeholder="Дополнительная информация о занятии"
        />

        <div style={{ display: 'flex', gap: '0.75rem', marginTop: '1.5rem' }}>
          <Button
            variant="secondary"
            onClick={() => setShowCreateModal(false)}
            style={{ flex: 1 }}
          >
            Отмена
          </Button>
          <Button
            variant="success"
            onClick={handleCreateLesson}
            style={{ flex: 1 }}
          >
            Создать
          </Button>
        </div>
      </Modal>

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
          }

          .calendar-header {
            display: flex;
            align-items: center;
            justify-content: space-between;
            gap: 1.5rem;
          }

          .calendar-title h1 {
            margin: 0;
            font-size: 2rem;
            font-weight: 700;
            color: #1e293b;
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
            background: #e0e7ff;
            padding: 0.25rem;
            border-radius: 999px;
            gap: 0.25rem;
          }

          .view-toggle button {
            border: none;
            background: transparent;
            color: #1e3a8a;
            font-weight: 600;
            font-size: 0.9rem;
            padding: 0.45rem 1.1rem;
            border-radius: 999px;
            cursor: pointer;
            transition: all 0.2s ease;
          }

          .view-toggle button.active {
            background: #2563eb;
            color: white;
            box-shadow: 0 8px 16px -12px rgba(37, 99, 235, 0.7);
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
            color: #475569;
            font-size: 0.9rem;
            cursor: pointer;
            transition: all 0.2s ease;
          }

          .group-item:hover {
            background: #eff6ff;
            color: #2563eb;
          }

          .group-item.active {
            background: linear-gradient(135deg, #2563eb, #3b82f6);
            color: white;
            box-shadow: 0 12px 24px -12px rgba(37, 99, 235, 0.7);
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
            color: #1e293b;
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
            --fc-page-bg-color: #f8fafc;
            --fc-today-bg-color: rgba(37, 99, 235, 0.08);
            font-family: 'Inter', system-ui, -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
          }

          .fc .fc-toolbar.fc-header-toolbar {
            margin-bottom: 1.5rem;
          }

          .fc .fc-button-primary {
            background: linear-gradient(135deg, #2563eb, #1d4ed8);
            border: none;
            border-radius: 10px;
            box-shadow: 0 12px 24px -14px rgba(37, 99, 235, 0.65);
          }

          .fc .fc-button-primary:hover {
            background: linear-gradient(135deg, #1d4ed8, #1e40af);
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
            background: #f1f5f9;
            color: #1d4ed8;
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
            box-shadow: 0 12px 24px -16px rgba(37, 99, 235, 0.75);
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
