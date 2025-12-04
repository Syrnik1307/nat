import React, { useEffect, useState } from 'react';
import './RecurringLessonsManage.css';
import {
  getGroups,
  getRecurringLessons,
  createRecurringLesson,
  updateRecurringLesson,
  deleteRecurringLesson,
  generateLessonsFromRecurring,
} from '../apiService';
import Button from '../shared/components/Button';
import Input from '../shared/components/Input';
import Badge from '../shared/components/Badge';
import Select from '../shared/components/Select';
import TimePicker from '../shared/components/TimePicker';
import DatePicker from '../shared/components/DatePicker';

const initialForm = {
  title: '',
  group_id: '',
  day_of_week: '',
  week_type: 'ALL',
  start_time: '',
  end_time: '',
  start_date: '',
  end_date: '',
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

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!form.group_id || form.day_of_week === '') {
      alert('Заполните все обязательные поля');
      return;
    }
    setSaving(true);
    try {
      const payload = { ...form, day_of_week: parseInt(form.day_of_week, 10) };
      if (editingId) {
        await updateRecurringLesson(editingId, payload);
      } else {
        await createRecurringLesson(payload);
      }
      await refresh();
      setForm({ ...initialForm });
      setEditingId(null);
      setShowForm(false);
    } catch (e) {
      alert(e.response?.data ? JSON.stringify(e.response.data) : 'Ошибка сохранения');
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
    if (!window.confirm('Вы уверены, что хотите удалить регулярный урок?')) return;
    try {
      await deleteRecurringLesson(id);
      await refresh();
    } catch (e) {
      alert('Ошибка удаления');
    }
  };

  const handleGenerate = async (item) => {
    const until = window.prompt('Сгенерировать уроки до даты (ГГГГ-ММ-ДД):');
    if (!until) return;
    try {
      const res = await generateLessonsFromRecurring(item.id, { 
        until_date: until, 
        dry_run: false 
      });
      alert(`Создано уроков: ${res.data.created_count}`);
      await refresh();
    } catch (err) {
      alert(err.response?.data?.detail || 'Ошибка генерации');
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
              <Input
                label="Название урока"
                type="text"
                required
                value={form.title}
                onChange={(e) => setForm({ ...form, title: e.target.value })}
                placeholder="Введите название"
              />

              <Select
                label="Группа"
                required
                value={form.group_id}
                onChange={(e) => setForm({ ...form, group_id: e.target.value })}
                options={groups.map(g => ({ value: String(g.id), label: g.name }))}
                placeholder="Выберите группу"
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
                  <h3 className="rl-card-title">{item.title}</h3>
                  <Badge variant="info">
                    {item.group?.name || '—'}
                  </Badge>
                </div>

                <div className="rl-card-body">
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
                    variant="text" 
                    size="small"
                    onClick={() => handleGenerate(item)}
                  >
                    Сгенерировать
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
    </div>
  );
};

export default RecurringLessonsManage;
