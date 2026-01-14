import React, { useEffect, useState } from 'react';
import './RecurringLessonsManage.css';
import {
  getGroups,
  getRecurringLessons,
  createRecurringLesson,
  updateRecurringLesson,
  deleteRecurringLesson,
} from '../apiService';
import Button from '../shared/components/Button';
import Input from '../shared/components/Input';
import Badge from '../shared/components/Badge';
import Select from '../shared/components/Select';
import TimePicker from '../shared/components/TimePicker';
import DatePicker from '../shared/components/DatePicker';
import { Notification, ConfirmModal } from '../shared/components';
import useNotification from '../shared/hooks/useNotification';

const initialForm = {
  title: '',
  group_id: '',
  day_of_week: '',
  week_type: 'ALL',
  start_time: '',
  end_time: '',
  start_date: '',
  end_date: '',
  // Telegram-уведомления
  telegram_notify_enabled: false,
  telegram_notify_minutes: 10,
  telegram_notify_to_group: true,
  telegram_notify_to_students: false,
  telegram_group_chat_id: '',
};

const dayOptions = [
  { value: 0, label: 'Понедельник' },
  { value: 1, label: 'Вторник' },
  { value: 2, label: 'Среда' },
  { value: 3, label: 'Четверг' },
  { value: 4, label: 'Пятница' },
  { value: 5, label: 'Суббота' },
  { value: 6, label: 'Воскресенье' },
];

const weekTypeOptions = [
  { value: 'ALL', label: 'Каждая неделя' },
  { value: 'UPPER', label: 'Верхняя неделя' },
  { value: 'LOWER', label: 'Нижняя неделя' },
];

const RecurringLessonsManage = () => {
  const { notification, confirm, showNotification, closeNotification, showConfirm, closeConfirm } = useNotification();
  const [groups, setGroups] = useState([]);
  const [items, setItems] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [form, setForm] = useState({ ...initialForm });
  const [saving, setSaving] = useState(false);
  const [editingId, setEditingId] = useState(null);
  const [activeFilter, setActiveFilter] = useState('all');
  const [showForm, setShowForm] = useState(false);

  useEffect(() => {
    const load = async () => {
      try {
        const [groupsRes, recurringRes] = await Promise.all([
          getGroups(),
          getRecurringLessons({}),
        ]);
        setGroups(Array.isArray(groupsRes.data) ? groupsRes.data : groupsRes.data.results || []);
        setItems(Array.isArray(recurringRes.data) ? recurringRes.data : recurringRes.data.results || []);
      } catch (e) {
        setError('Ошибка загрузки данных');
      } finally {
        setLoading(false);
      }
    };
    load();
  }, []);

  const refresh = async () => {
    const res = await getRecurringLessons({});
    setItems(Array.isArray(res.data) ? res.data : res.data.results || []);
  };

  // Функция для нормализации даты в формат YYYY-MM-DD
  const normalizeDateToISO = (dateStr) => {
    if (!dateStr) return '';
    // Уже в формате YYYY-MM-DD
    if (/^\d{4}-\d{2}-\d{2}$/.test(dateStr)) {
      return dateStr;
    }
    // Формат DD.MM.YYYY -> YYYY-MM-DD
    if (/^\d{2}\.\d{2}\.\d{4}$/.test(dateStr)) {
      const [day, month, year] = dateStr.split('.');
      return `${year}-${month}-${day}`;
    }
    // Попробуем распарсить как Date
    const d = new Date(dateStr);
    if (!isNaN(d.getTime())) {
      return d.toISOString().split('T')[0];
    }
    return dateStr; // Возвращаем как есть
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!form.group_id || form.day_of_week === '') {
      showNotification('warning', 'Внимание', 'Заполните все обязательные поля');
      return;
    }

    setSaving(true);
    try {
      const payload = {
        ...form,
        day_of_week: parseInt(form.day_of_week, 10),
        start_date: normalizeDateToISO(form.start_date),
        end_date: normalizeDateToISO(form.end_date),
      };
      if (editingId) {
        await updateRecurringLesson(editingId, payload);
        showNotification('success', 'Успешно', 'Регулярный урок обновлен');
      } else {
        await createRecurringLesson(payload);
        showNotification('success', 'Успешно', 'Регулярный урок создан');
      }
      await refresh();
      setForm({ ...initialForm });
      setEditingId(null);
      setShowForm(false);
    } catch (e) {
      // Парсим ошибки валидации от бэкенда
      let errorMessage = 'Ошибка сохранения';
      if (e.response?.data) {
        const data = e.response.data;
        if (typeof data === 'object') {
          // Преобразуем {field: [errors]} в читаемый текст
          const messages = [];
          for (const [field, errors] of Object.entries(data)) {
            const errorText = Array.isArray(errors) ? errors.join(', ') : String(errors);
            // Человекочитаемые названия полей
            const fieldNames = {
              telegram_notify_enabled: 'Telegram-уведомления',
              telegram_group_chat_id: 'Chat ID группы',
              telegram_notify_to_group: 'Отправка в группу',
              telegram_notify_minutes: 'Минуты до начала',
              telegram_announce_enabled: 'Анонс',
              telegram_announce_time: 'Время анонса',
              zoom_pmi_link: 'Zoom PMI ссылка',
              end_time: 'Время окончания',
              start_time: 'Время начала',
              group_id: 'Группа',
              day_of_week: 'День недели',
            };
            const fieldName = fieldNames[field] || field;
            messages.push(`${fieldName}: ${errorText}`);
          }
          errorMessage = messages.join('\n') || JSON.stringify(data);
        } else {
          errorMessage = String(data);
        }
      }
      showNotification('error', 'Ошибка', errorMessage);
    } finally {
      setSaving(false);
    }
  };

  const startEdit = (item) => {
    setEditingId(item.id);
    setForm({
      title: item.title,
      group_id: String(item.group?.id || item.group_id || ''),
      day_of_week: String(item.day_of_week),
      week_type: item.week_type,
      start_time: item.start_time.slice(0, 5),
      end_time: item.end_time.slice(0, 5),
      start_date: item.start_date,
      end_date: item.end_date,
      // Telegram-уведомления
      telegram_notify_enabled: item.telegram_notify_enabled || false,
      telegram_notify_minutes: item.telegram_notify_minutes || 10,
      telegram_notify_to_group: item.telegram_notify_to_group !== false,
      telegram_notify_to_students: item.telegram_notify_to_students || false,
      telegram_group_chat_id: item.telegram_group_chat_id || '',
    });
    setShowForm(true);
    window.scrollTo({ top: 0, behavior: 'smooth' });
  };

  const cancelEdit = () => {
    setEditingId(null);
    setForm({ ...initialForm });
    setShowForm(false);
  };

  const handleDelete = async (id) => {
    const confirmed = await showConfirm({
      title: 'Удаление регулярного урока',
      message: 'Вы уверены, что хотите удалить регулярный урок?',
      variant: 'danger',
      confirmText: 'Удалить',
      cancelText: 'Отмена'
    });
    if (!confirmed) return;
    try {
      await deleteRecurringLesson(id);
      await refresh();
      showNotification('success', 'Успешно', 'Регулярный урок удален');
    } catch (e) {
      showNotification('error', 'Ошибка', 'Не удалось удалить регулярный урок');
    }
  };

  const filteredItems = items.filter(item => {
    if (activeFilter === 'all') return true;
    if (activeFilter === 'upper') return item.week_type === 'UPPER' || item.week_type === 'ALL';
    if (activeFilter === 'lower') return item.week_type === 'LOWER' || item.week_type === 'ALL';
    return true;
  });

  if (loading) return <div className="rl-loading">Загрузка...</div>;
  if (error) return <div className="rl-error">{error}</div>;

  return (
    <div className="rl-container">
      {/* Header */}
      <div className="rl-header">
        <h1 className="rl-title">Регулярные уроки</h1>
        <Button 
          variant="primary" 
          onClick={() => {
            setShowForm(!showForm);
            if (showForm) cancelEdit();
          }}
        >
          {showForm ? 'Скрыть форму' : 'Добавить урок'}
        </Button>
      </div>

      {/* Filter Tabs */}
      <div className="rl-filters">
        <button 
          className={`rl-filter ${activeFilter === 'all' ? 'active' : ''}`}
          onClick={() => setActiveFilter('all')}
        >
          Все уроки
        </button>
        <button 
          className={`rl-filter ${activeFilter === 'upper' ? 'active' : ''}`}
          onClick={() => setActiveFilter('upper')}
        >
          Верхняя неделя
        </button>
        <button 
          className={`rl-filter ${activeFilter === 'lower' ? 'active' : ''}`}
          onClick={() => setActiveFilter('lower')}
        >
          Нижняя неделя
        </button>
      </div>

      {/* Form */}
      {showForm && (
        <div className="rl-form-card">
          <h2 className="rl-form-title">
            {editingId ? 'Редактировать урок' : 'Создать новый урок'}
          </h2>
          <form onSubmit={handleSubmit} className="rl-form">
            <div className="rl-form-grid">
              <Select
                label="Группа"
                required
                value={form.group_id}
                onChange={(e) => setForm({ ...form, group_id: e.target.value })}
                options={groups.map(g => ({ value: String(g.id), label: g.name }))}
                placeholder="Выберите группу"
              />

              <Input
                label="Тема урока (необязательно)"
                type="text"
                value={form.title}
                onChange={(e) => setForm({ ...form, title: e.target.value })}
                placeholder="Если не указано, будет использовано имя группы"
              />

              <Select
                label="День недели"
                required
                value={form.day_of_week}
                onChange={(e) => setForm({ ...form, day_of_week: e.target.value })}
                options={dayOptions.map(d => ({ value: String(d.value), label: d.label }))}
                placeholder="Выберите день"
              />

              <Select
                label="Периодичность"
                required
                value={form.week_type}
                onChange={(e) => setForm({ ...form, week_type: e.target.value })}
                options={weekTypeOptions}
                placeholder="Выберите периодичность"
              />

              <TimePicker
                label="Время начала"
                required
                value={form.start_time}
                onChange={(e) => setForm({ ...form, start_time: e.target.value })}
              />

              <TimePicker
                label="Время окончания"
                required
                value={form.end_time}
                onChange={(e) => setForm({ ...form, end_time: e.target.value })}
              />

              <DatePicker
                label="Дата начала"
                required
                value={form.start_date}
                onChange={(e) => setForm({ ...form, start_date: e.target.value })}
              />

              <DatePicker
                label="Дата окончания"
                required
                value={form.end_date}
                onChange={(e) => setForm({ ...form, end_date: e.target.value })}
              />
            </div>

            {/* TODO: Telegram-уведомления (временно скрыты) */}

            <div className="rl-form-actions">
              <Button type="submit" variant="primary" disabled={saving}>
                {saving ? 'Сохранение...' : editingId ? 'Сохранить' : 'Создать'}
              </Button>
              {editingId && (
                <Button type="button" variant="secondary" onClick={cancelEdit}>
                  Отмена
                </Button>
              )}
            </div>
          </form>
        </div>
      )}

      {/* List */}
      <div className="rl-list">
        {filteredItems.length === 0 ? (
          <div className="rl-empty">
            <p>Нет регулярных уроков</p>
          </div>
        ) : (
          <div className="rl-cards">
            {filteredItems.map(item => (
              <div key={item.id} className="rl-card">
                <div className="rl-card-header">
                  <h3 className="rl-card-title">{item.display_name || item.title || item.group?.name || 'Урок'}</h3>
                  <Badge variant="info">
                    {item.group?.name || '—'}
                  </Badge>
                </div>

                <div className="rl-card-body">
                  {item.title && (
                    <div className="rl-card-row">
                      <span className="rl-card-label">Тема:</span>
                      <span className="rl-card-value">{item.title}</span>
                    </div>
                  )}
                  
                  <div className="rl-card-row">
                    <span className="rl-card-label">День:</span>
                    <span className="rl-card-value">{item.day_of_week_display}</span>
                  </div>
                  
                  <div className="rl-card-row">
                    <span className="rl-card-label">Время:</span>
                    <span className="rl-card-value">
                      {item.start_time.slice(0, 5)} — {item.end_time.slice(0, 5)}
                    </span>
                  </div>

                  <div className="rl-card-row">
                    <span className="rl-card-label">Период:</span>
                    <span className="rl-card-value">
                      {item.start_date} — {item.end_date}
                    </span>
                  </div>

                  <div className="rl-card-row">
                    <span className="rl-card-label">Неделя:</span>
                    <Badge 
                      variant={item.week_type === 'ALL' ? 'neutral' : item.week_type === 'UPPER' ? 'success' : 'warning'}
                      size="small"
                    >
                      {item.week_type_display}
                    </Badge>
                  </div>
                </div>

                <div className="rl-card-actions">
                  <Button 
                    variant="outline" 
                    size="small"
                    onClick={() => startEdit(item)}
                  >
                    Редактировать
                  </Button>
                  <Button 
                    variant="danger" 
                    size="small"
                    onClick={() => handleDelete(item.id)}
                  >
                    Удалить
                  </Button>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      <Notification
        isOpen={notification.isOpen}
        onClose={closeNotification}
        type={notification.type}
        title={notification.title}
        message={notification.message}
      />

      <ConfirmModal
        isOpen={confirm.isOpen}
        onClose={closeConfirm}
        onConfirm={confirm.onConfirm}
        title={confirm.title}
        message={confirm.message}
        variant={confirm.variant}
        confirmText={confirm.confirmText}
        cancelText={confirm.cancelText}
      />
    </div>
  );
};

export default RecurringLessonsManage;
