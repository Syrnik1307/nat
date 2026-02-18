import React, { useState, useEffect, useCallback } from 'react';
import { useAuth } from '../../auth';
import { useNavigate } from 'react-router-dom';
import {
  getCourses, getCourse, createCourse, updateCourse, deleteCourse,
  getCourseModules, createCourseModule, updateCourseModule, deleteCourseModule, reorderCourseModules,
  getCourseLessons, createCourseLesson, updateCourseLesson, deleteCourseLesson, reorderCourseLessons,
  uploadCourseCover, uploadCourseLessonMaterial, deleteCourseLessonMaterial,
} from '../../apiService';
import './OlgaCourseManager.css';

/**
 * OlgaCourseManager — полнофункциональный конструктор курсов для тенанта «Ольга».
 * Визуально отделён от основного LectioSpace AdminPanel (CourseManager).
 * Использует Olga-дизайн (тёплые тона, Georgia шрифт).
 * API-запросы изолированы через X-Tenant-ID header (выставляется автоматически).
 */
const OlgaCourseManager = () => {
  const { user } = useAuth();
  const navigate = useNavigate();

  const [courses, setCourses] = useState([]);
  const [loading, setLoading] = useState(true);
  const [message, setMessage] = useState(null);
  const [view, setView] = useState('list'); // 'list' | 'editor'
  const [editingCourseId, setEditingCourseId] = useState(null);

  useEffect(() => {
    if (user && !['teacher', 'admin'].includes(user.role)) {
      navigate('/olga/courses');
    }
  }, [user, navigate]);

  const loadCourses = useCallback(async () => {
    try {
      setLoading(true);
      const res = await getCourses();
      setCourses(res.data.results || res.data || []);
    } catch {
      showMessage('Ошибка загрузки курсов', 'error');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { loadCourses(); }, [loadCourses]);

  const showMessage = (text, type = 'success') => {
    setMessage({ text, type });
    setTimeout(() => setMessage(null), 4000);
  };

  // ═══ CRUD ═══
  const handleCreate = async () => {
    try {
      const res = await createCourse({ title: 'Новый курс', description: '', status: 'draft' });
      showMessage('Курс создан');
      setEditingCourseId(res.data.id);
      setView('editor');
      loadCourses();
    } catch (err) {
      showMessage(err.response?.data?.detail || 'Ошибка создания курса', 'error');
    }
  };

  const handleDelete = async (id, e) => {
    e.stopPropagation();
    if (!window.confirm('Удалить этот курс и всё его содержимое?')) return;
    try {
      await deleteCourse(id);
      setCourses(prev => prev.filter(c => c.id !== id));
      showMessage('Курс удалён');
      if (editingCourseId === id) { setView('list'); setEditingCourseId(null); }
    } catch {
      showMessage('Ошибка удаления', 'error');
    }
  };

  const openEditor = (course) => { setEditingCourseId(course.id); setView('editor'); };
  const closeEditor = () => { setView('list'); setEditingCourseId(null); loadCourses(); };

  // ═══ List view ═══
  if (loading && view === 'list') {
    return (
      <div className="ocm">
        <div className="ocm-loading"><div className="olga-spinner" /><p>Загрузка курсов…</p></div>
      </div>
    );
  }

  if (view === 'editor' && editingCourseId) {
    return (
      <div className="ocm">
        {message && <div className={`ocm-message ${message.type}`}>{message.text}</div>}
        <OlgaCourseEditor
          courseId={editingCourseId}
          onClose={closeEditor}
          showMessage={showMessage}
        />
      </div>
    );
  }

  return (
    <div className="ocm">
      {message && <div className={`ocm-message ${message.type}`}>{message.text}</div>}

      <div className="ocm-header">
        <div>
          <h1 className="ocm-title">✿ Управление курсами</h1>
          <p className="ocm-subtitle">Создавайте и наполняйте курсы контентом</p>
        </div>
        <button className="ocm-btn ocm-btn-primary" onClick={handleCreate}>
          ＋ Создать курс
        </button>
      </div>

      {courses.length === 0 ? (
        <div className="ocm-empty">
          <div className="ocm-empty-icon">✿</div>
          <h3>Курсов пока нет</h3>
          <p>Создайте свой первый курс</p>
          <button className="ocm-btn ocm-btn-primary" onClick={handleCreate}>
            ＋ Создать первый курс
          </button>
        </div>
      ) : (
        <div className="ocm-grid">
          {courses.map(course => (
            <div key={course.id} className="ocm-card" onClick={() => openEditor(course)}>
              <div className="ocm-card-cover">
                {course.cover_url ? (
                  <img src={course.cover_url} alt={course.title} />
                ) : (
                  <div className="ocm-card-placeholder">✿</div>
                )}
                <span className={`ocm-card-badge ${course.status}`}>
                  {course.status === 'published' ? 'Опубликован' :
                   course.status === 'archived' ? 'Архив' : 'Черновик'}
                </span>
              </div>
              <div className="ocm-card-body">
                <h3 className="ocm-card-title">{course.title}</h3>
                <p className="ocm-card-desc">
                  {course.short_description || course.description || 'Без описания'}
                </p>
                <div className="ocm-card-meta">
                  <span>📝 {course.lessons_count || 0} уроков</span>
                  <span>📦 {course.modules_count || 0} модулей</span>
                  {course.price && <span>💰 {course.price} ₽</span>}
                </div>
              </div>
              <button
                className="ocm-card-delete"
                onClick={(e) => handleDelete(course.id, e)}
                title="Удалить курс"
              >✕</button>
            </div>
          ))}
        </div>
      )}
    </div>
  );
};


// ═══════════════════════════════════════════════════
// EDITOR
// ═══════════════════════════════════════════════════

const OlgaCourseEditor = ({ courseId, onClose, showMessage }) => {
  const [course, setCourse] = useState(null);
  const [modules, setModules] = useState([]);
  const [lessons, setLessons] = useState([]);
  const [loading, setLoading] = useState(true);
  const [activeTab, setActiveTab] = useState('info');
  const [expandedModules, setExpandedModules] = useState({});
  const [editingLesson, setEditingLesson] = useState(null);
  const [editingModule, setEditingModule] = useState(null);
  const [saving, setSaving] = useState(false);
  const [uploading, setUploading] = useState({});

  const [form, setForm] = useState({
    title: '', description: '', short_description: '',
    price: '', duration: '', status: 'draft',
  });

  const loadData = useCallback(async () => {
    try {
      setLoading(true);
      const [cRes, mRes, lRes] = await Promise.all([
        getCourse(courseId),
        getCourseModules(courseId),
        getCourseLessons(courseId),
      ]);
      const c = cRes.data;
      setCourse(c);
      setForm({
        title: c.title || '', description: c.description || '',
        short_description: c.short_description || '',
        price: c.price || '', duration: c.duration || '',
        status: c.status || 'draft',
      });
      const mods = mRes.data.results || mRes.data || [];
      setModules(mods);
      const lsns = lRes.data.results || lRes.data || [];
      setLessons(lsns);
      const exp = {};
      mods.forEach(m => { exp[m.id] = true; });
      setExpandedModules(exp);
    } catch {
      showMessage('Ошибка загрузки курса', 'error');
    } finally {
      setLoading(false);
    }
  }, [courseId, showMessage]);

  useEffect(() => { loadData(); }, [loadData]);

  // ─── Save course info ───
  const handleSave = async () => {
    try {
      setSaving(true);
      await updateCourse(courseId, form);
      showMessage('Курс сохранён');
      loadData();
    } catch (err) {
      showMessage(err.response?.data?.detail || 'Ошибка сохранения', 'error');
    } finally {
      setSaving(false);
    }
  };

  // ─── Cover upload ───
  const handleCoverUpload = async (e) => {
    const file = e.target.files[0];
    if (!file) return;
    setUploading(prev => ({ ...prev, cover: true }));
    try {
      const fd = new FormData();
      fd.append('cover', file);
      const res = await uploadCourseCover(courseId, fd);
      setCourse(prev => ({ ...prev, cover_url: res.data.cover_url }));
      showMessage('Обложка загружена!');
    } catch (err) {
      showMessage(err.response?.data?.error || 'Ошибка загрузки обложки', 'error');
    } finally {
      setUploading(prev => ({ ...prev, cover: false }));
    }
  };

  // ─── Module CRUD ───
  const handleAddModule = async () => {
    try {
      await createCourseModule({ course: courseId, title: 'Новый модуль', order: modules.length });
      showMessage('Модуль добавлен');
      loadData();
    } catch {
      showMessage('Ошибка создания модуля', 'error');
    }
  };

  const handleSaveModule = async (moduleId, data) => {
    try {
      await updateCourseModule(moduleId, { ...data, course: courseId });
      setEditingModule(null);
      loadData();
    } catch {
      showMessage('Ошибка сохранения модуля', 'error');
    }
  };

  const handleDeleteModule = async (moduleId) => {
    if (!window.confirm('Удалить модуль? Уроки останутся без модуля.')) return;
    try {
      await deleteCourseModule(moduleId);
      showMessage('Модуль удалён');
      loadData();
    } catch {
      showMessage('Ошибка удаления', 'error');
    }
  };

  const handleMoveModule = async (moduleId, direction) => {
    const idx = modules.findIndex(m => m.id === moduleId);
    if ((direction === 'up' && idx === 0) || (direction === 'down' && idx === modules.length - 1)) return;
    const arr = [...modules];
    const swapIdx = direction === 'up' ? idx - 1 : idx + 1;
    [arr[idx], arr[swapIdx]] = [arr[swapIdx], arr[idx]];
    const items = arr.map((m, i) => ({ id: m.id, order: i }));
    setModules(arr.map((m, i) => ({ ...m, order: i })));
    try { await reorderCourseModules(items); }
    catch { loadData(); }
  };

  // ─── Lesson CRUD ───
  const handleAddLesson = async (moduleId = null) => {
    const count = lessons.filter(l => l.module === moduleId).length;
    try {
      await createCourseLesson({ course: courseId, module: moduleId, title: 'Новый урок', order: count });
      showMessage('Урок добавлен');
      loadData();
    } catch {
      showMessage('Ошибка создания урока', 'error');
    }
  };

  const handleSaveLesson = async (data) => {
    try {
      await updateCourseLesson(data.id, { ...data, course: courseId });
      setEditingLesson(null);
      showMessage('Урок сохранён');
      loadData();
    } catch {
      showMessage('Ошибка сохранения урока', 'error');
    }
  };

  const handleDeleteLesson = async (lessonId) => {
    if (!window.confirm('Удалить этот урок?')) return;
    try {
      await deleteCourseLesson(lessonId);
      showMessage('Урок удалён');
      loadData();
    } catch {
      showMessage('Ошибка удаления', 'error');
    }
  };

  const handleMoveLesson = async (lessonId, moduleId, direction) => {
    const arr = lessons.filter(l => l.module === moduleId).sort((a, b) => a.order - b.order);
    const idx = arr.findIndex(l => l.id === lessonId);
    if ((direction === 'up' && idx === 0) || (direction === 'down' && idx === arr.length - 1)) return;
    const swapIdx = direction === 'up' ? idx - 1 : idx + 1;
    [arr[idx], arr[swapIdx]] = [arr[swapIdx], arr[idx]];
    const items = arr.map((l, i) => ({ id: l.id, order: i, module: moduleId }));
    setLessons(prev => {
      const others = prev.filter(l => l.module !== moduleId);
      return [...others, ...arr.map((l, i) => ({ ...l, order: i }))];
    });
    try { await reorderCourseLessons(items); }
    catch { loadData(); }
  };

  const toggleModule = (id) => setExpandedModules(prev => ({ ...prev, [id]: !prev[id] }));

  if (loading) {
    return <div className="ocm-loading"><div className="olga-spinner" /><p>Загрузка курса…</p></div>;
  }

  const lessonsWithoutModule = lessons.filter(l => !l.module).sort((a, b) => a.order - b.order);

  return (
    <div className="ocm-editor">
      {/* Header */}
      <div className="ocm-editor-header">
        <div className="ocm-editor-header-left">
          <button className="ocm-back-btn" onClick={onClose} title="Назад">←</button>
          <h2>{form.title || 'Редактирование курса'}</h2>
        </div>
        <div className="ocm-editor-header-right">
          <button className="ocm-btn ocm-btn-secondary" onClick={onClose}>Закрыть</button>
          <button className="ocm-btn ocm-btn-primary" onClick={handleSave} disabled={saving}>
            {saving ? '⏳ Сохранение…' : '💾 Сохранить'}
          </button>
        </div>
      </div>

      {/* Tabs */}
      <div className="ocm-tabs">
        <button className={`ocm-tab ${activeTab === 'info' ? 'active' : ''}`}
          onClick={() => setActiveTab('info')}>📋 Информация</button>
        <button className={`ocm-tab ${activeTab === 'constructor' ? 'active' : ''}`}
          onClick={() => setActiveTab('constructor')}>🏗️ Содержание</button>
      </div>

      {/* ═══ INFO TAB ═══ */}
      {activeTab === 'info' && (
        <div className="ocm-tab-content">
          <div className="ocm-form-group">
            <label>Название курса *</label>
            <input type="text" value={form.title}
              onChange={e => setForm(f => ({ ...f, title: e.target.value }))}
              placeholder="Введите название курса" />
          </div>

          <div className="ocm-form-group">
            <label>Краткое описание</label>
            <input type="text" value={form.short_description}
              onChange={e => setForm(f => ({ ...f, short_description: e.target.value }))}
              placeholder="Краткое описание для каталога" maxLength={500} />
          </div>

          <div className="ocm-form-group">
            <label>Полное описание</label>
            <textarea value={form.description}
              onChange={e => setForm(f => ({ ...f, description: e.target.value }))}
              placeholder="Подробное описание курса" rows={5} />
          </div>

          <div className="ocm-form-row">
            <div className="ocm-form-group">
              <label>Цена (₽)</label>
              <input type="number" value={form.price}
                onChange={e => setForm(f => ({ ...f, price: e.target.value }))}
                placeholder="0" min="0" step="0.01" />
            </div>
            <div className="ocm-form-group">
              <label>Длительность</label>
              <input type="text" value={form.duration}
                onChange={e => setForm(f => ({ ...f, duration: e.target.value }))}
                placeholder='Напр. "6 часов"' />
            </div>
          </div>

          <div className="ocm-form-group">
            <label>Статус</label>
            <select value={form.status}
              onChange={e => setForm(f => ({ ...f, status: e.target.value }))}>
              <option value="draft">📝 Черновик</option>
              <option value="published">✅ Опубликован</option>
              <option value="archived">📦 В архиве</option>
            </select>
          </div>

          {/* Cover */}
          <div className="ocm-form-group">
            <label>Обложка курса</label>
            <div className="ocm-cover-section">
              <div className="ocm-cover-preview">
                {course?.cover_url ? (
                  <img src={course.cover_url} alt="Обложка" />
                ) : (
                  <span className="ocm-cover-placeholder-icon">✿</span>
                )}
              </div>
              <div>
                <label className="ocm-btn ocm-btn-secondary" style={{ cursor: 'pointer' }}>
                  {uploading.cover ? '⏳ Загрузка…' : '📷 Загрузить обложку'}
                  <input type="file" accept="image/jpeg,image/png,image/webp"
                    hidden onChange={handleCoverUpload} disabled={uploading.cover} />
                </label>
                <p className="ocm-hint">JPG, PNG или WebP. Максимум 5 МБ.</p>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* ═══ CONSTRUCTOR TAB ═══ */}
      {activeTab === 'constructor' && (
        <div className="ocm-tab-content">
          <div className="ocm-constructor">
            {modules.sort((a, b) => a.order - b.order).map((mod, modIdx) => {
              const moduleLessons = lessons.filter(l => l.module === mod.id).sort((a, b) => a.order - b.order);
              const isExpanded = expandedModules[mod.id];

              return (
                <div key={mod.id} className="ocm-module">
                  <div className="ocm-module-header" onClick={() => toggleModule(mod.id)}>
                    <div className="ocm-module-header-left">
                      {editingModule === mod.id ? (
                        <OlgaModuleEditInline
                          module={mod}
                          onSave={(data) => handleSaveModule(mod.id, data)}
                          onCancel={() => setEditingModule(null)}
                        />
                      ) : (
                        <>
                          <span className="ocm-module-title">{mod.title}</span>
                          <span className="ocm-module-meta">
                            ({moduleLessons.length} {lessonsWord(moduleLessons.length)})
                          </span>
                        </>
                      )}
                    </div>
                    <div className="ocm-module-actions" onClick={e => e.stopPropagation()}>
                      <button className="ocm-move-btn" onClick={() => handleMoveModule(mod.id, 'up')} disabled={modIdx === 0} title="Вверх">▲</button>
                      <button className="ocm-move-btn" onClick={() => handleMoveModule(mod.id, 'down')} disabled={modIdx === modules.length - 1} title="Вниз">▼</button>
                      <button className="ocm-icon-btn" onClick={() => setEditingModule(mod.id)} title="Редактировать">✏️</button>
                      <button className="ocm-icon-btn danger" onClick={() => handleDeleteModule(mod.id)} title="Удалить">🗑️</button>
                    </div>
                    <span className={`ocm-module-toggle ${isExpanded ? 'open' : ''}`}>▸</span>
                  </div>

                  {isExpanded && (
                    <div className="ocm-module-body">
                      {moduleLessons.map((lesson, lIdx) => (
                        <OlgaLessonRow
                          key={lesson.id}
                          lesson={lesson}
                          index={lIdx}
                          total={moduleLessons.length}
                          onEdit={() => setEditingLesson(lesson)}
                          onDelete={() => handleDeleteLesson(lesson.id)}
                          onMove={(dir) => handleMoveLesson(lesson.id, mod.id, dir)}
                        />
                      ))}
                      <button className="ocm-add-lesson-btn" onClick={() => handleAddLesson(mod.id)}>
                        ＋ Добавить урок
                      </button>
                    </div>
                  )}
                </div>
              );
            })}

            {/* Lessons without module */}
            {lessonsWithoutModule.length > 0 && (
              <div className="ocm-module">
                <div className="ocm-module-header" onClick={() => toggleModule('none')}>
                  <div className="ocm-module-header-left">
                    <span className="ocm-module-title" style={{ fontStyle: 'italic', opacity: 0.7 }}>
                      Без модуля
                    </span>
                    <span className="ocm-module-meta">
                      ({lessonsWithoutModule.length} {lessonsWord(lessonsWithoutModule.length)})
                    </span>
                  </div>
                  <span className={`ocm-module-toggle ${expandedModules['none'] ? 'open' : ''}`}>▸</span>
                </div>
                {expandedModules['none'] && (
                  <div className="ocm-module-body">
                    {lessonsWithoutModule.map((lesson, lIdx) => (
                      <OlgaLessonRow
                        key={lesson.id}
                        lesson={lesson}
                        index={lIdx}
                        total={lessonsWithoutModule.length}
                        onEdit={() => setEditingLesson(lesson)}
                        onDelete={() => handleDeleteLesson(lesson.id)}
                        onMove={(dir) => handleMoveLesson(lesson.id, null, dir)}
                      />
                    ))}
                  </div>
                )}
              </div>
            )}

            <div className="ocm-constructor-actions">
              <button className="ocm-add-module-btn" onClick={handleAddModule}>
                📦 Добавить модуль
              </button>
              <button className="ocm-add-module-btn" onClick={() => handleAddLesson(null)}>
                📝 Добавить урок (без модуля)
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Lesson edit modal */}
      {editingLesson && (
        <OlgaLessonEditModal
          lesson={editingLesson}
          modules={modules}
          courseId={courseId}
          onSave={handleSaveLesson}
          onClose={() => setEditingLesson(null)}
          showMessage={showMessage}
        />
      )}
    </div>
  );
};


// ═══════════════════════════════════════════════════
// LessonRow
// ═══════════════════════════════════════════════════

const OlgaLessonRow = ({ lesson, index, total, onEdit, onDelete, onMove }) => (
  <div className="ocm-lesson-row">
    <div className="ocm-lesson-num">{index + 1}</div>
    <div className="ocm-lesson-info">
      <div className="ocm-lesson-title">{lesson.title}</div>
      <div className="ocm-lesson-badges">
        {lesson.video_url && <span className="ocm-badge video">🎬 Видео</span>}
        {lesson.content && <span className="ocm-badge text">📄 Текст</span>}
        {lesson.is_free_preview && <span className="ocm-badge preview">👁️ Превью</span>}
        {lesson.materials && lesson.materials.length > 0 && (
          <span className="ocm-badge file">📎 {lesson.materials.length}</span>
        )}
      </div>
    </div>
    <div className="ocm-lesson-actions">
      <button className="ocm-move-btn" onClick={() => onMove('up')} disabled={index === 0}>▲</button>
      <button className="ocm-move-btn" onClick={() => onMove('down')} disabled={index === total - 1}>▼</button>
      <button className="ocm-icon-btn" onClick={onEdit} title="Редактировать">✏️</button>
      <button className="ocm-icon-btn danger" onClick={onDelete} title="Удалить">🗑️</button>
    </div>
  </div>
);


// ═══════════════════════════════════════════════════
// ModuleEditInline
// ═══════════════════════════════════════════════════

const OlgaModuleEditInline = ({ module, onSave, onCancel }) => {
  const [title, setTitle] = useState(module.title);
  return (
    <div className="ocm-module-edit" onClick={e => e.stopPropagation()}>
      <input type="text" value={title} onChange={e => setTitle(e.target.value)} autoFocus
        onKeyDown={e => {
          if (e.key === 'Enter') onSave({ title, description: module.description, order: module.order });
          if (e.key === 'Escape') onCancel();
        }} />
      <button className="ocm-btn ocm-btn-small ocm-btn-primary" onClick={() => onSave({ title, description: module.description, order: module.order })}>✓</button>
      <button className="ocm-btn ocm-btn-small ocm-btn-secondary" onClick={onCancel}>✕</button>
    </div>
  );
};


// ═══════════════════════════════════════════════════
// LessonEditModal
// ═══════════════════════════════════════════════════

const OlgaLessonEditModal = ({ lesson, modules, courseId, onSave, onClose, showMessage }) => {
  const [form, setForm] = useState({
    id: lesson.id,
    title: lesson.title || '',
    video_url: lesson.video_url || '',
    content: lesson.content || '',
    duration: lesson.duration || '',
    is_free_preview: lesson.is_free_preview || false,
    module: lesson.module || null,
    order: lesson.order || 0,
  });
  const [materials, setMaterials] = useState(lesson.materials || []);
  const [uploadingMaterial, setUploadingMaterial] = useState(false);

  const handleMaterialUpload = async (e) => {
    const file = e.target.files[0];
    if (!file) return;
    setUploadingMaterial(true);
    try {
      const fd = new FormData();
      fd.append('file', file);
      fd.append('name', file.name);
      const res = await uploadCourseLessonMaterial(lesson.id, fd);
      setMaterials(prev => [...prev, res.data]);
      showMessage('Материал загружен!');
    } catch (err) {
      showMessage(err.response?.data?.error || 'Ошибка загрузки файла', 'error');
    } finally {
      setUploadingMaterial(false);
    }
  };

  const handleDeleteMaterial = async (materialId) => {
    try {
      await deleteCourseLessonMaterial(lesson.id, materialId);
      setMaterials(prev => prev.filter(m => m.id !== materialId));
      showMessage('Материал удалён');
    } catch {
      showMessage('Ошибка удаления материала', 'error');
    }
  };

  return (
    <div className="ocm-modal-overlay" onClick={onClose}>
      <div className="ocm-modal" onClick={e => e.stopPropagation()}>
        <div className="ocm-modal-header">
          <h3>Редактирование урока</h3>
          <button className="ocm-modal-close" onClick={onClose}>✕</button>
        </div>

        <div className="ocm-modal-body">
          <div className="ocm-form-group">
            <label>Название урока *</label>
            <input type="text" value={form.title}
              onChange={e => setForm(f => ({ ...f, title: e.target.value }))}
              placeholder="Название урока" />
          </div>

          <div className="ocm-form-row">
            <div className="ocm-form-group">
              <label>Модуль</label>
              <select value={form.module || ''}
                onChange={e => setForm(f => ({ ...f, module: e.target.value ? Number(e.target.value) : null }))}>
                <option value="">— Без модуля —</option>
                {modules.map(m => <option key={m.id} value={m.id}>{m.title}</option>)}
              </select>
            </div>
            <div className="ocm-form-group">
              <label>Длительность</label>
              <input type="text" value={form.duration}
                onChange={e => setForm(f => ({ ...f, duration: e.target.value }))}
                placeholder='Напр. "15 мин"' />
            </div>
          </div>

          <div className="ocm-form-group">
            <label>Ссылка на видео для iframe</label>
            <input type="url" value={form.video_url}
              onChange={e => setForm(f => ({ ...f, video_url: e.target.value }))}
              placeholder="https://... (YouTube/Rutube/Vimeo/embed)" />
          </div>

          <div className="ocm-form-group">
            <label>Текстовый контент</label>
            <textarea value={form.content}
              onChange={e => setForm(f => ({ ...f, content: e.target.value }))}
              placeholder="Текстовый контент урока…" rows={6} />
          </div>

          <div className="ocm-form-group">
            <label className="ocm-checkbox">
              <input type="checkbox" checked={form.is_free_preview}
                onChange={e => setForm(f => ({ ...f, is_free_preview: e.target.checked }))} />
              Бесплатный превью (доступен без покупки)
            </label>
          </div>

          {/* Materials */}
          <div className="ocm-form-group">
            <label>Материалы для скачивания</label>
            {materials.length > 0 && (
              <div className="ocm-materials-list">
                {materials.map(mat => (
                  <div key={mat.id} className="ocm-material-row">
                    <a href={mat.url} target="_blank" rel="noopener noreferrer">📎 {mat.name}</a>
                    <button className="ocm-icon-btn danger" onClick={() => handleDeleteMaterial(mat.id)}>🗑️</button>
                  </div>
                ))}
              </div>
            )}
            <label className="ocm-upload-area">
              {uploadingMaterial ? '⏳ Загрузка файла…' : '📁 Нажмите для загрузки файла'}
              <input type="file" hidden onChange={handleMaterialUpload} disabled={uploadingMaterial} />
            </label>
          </div>
        </div>

        <div className="ocm-modal-footer">
          <button className="ocm-btn ocm-btn-secondary" onClick={onClose}>Отмена</button>
          <button className="ocm-btn ocm-btn-primary" onClick={() => onSave(form)}>💾 Сохранить</button>
        </div>
      </div>
    </div>
  );
};


// ═══ Helper ═══
function lessonsWord(n) {
  const abs = Math.abs(n) % 100;
  const last = abs % 10;
  if (abs >= 11 && abs <= 19) return 'уроков';
  if (last === 1) return 'урок';
  if (last >= 2 && last <= 4) return 'урока';
  return 'уроков';
}


export default OlgaCourseManager;
