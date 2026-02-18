import React, { useState, useEffect, useCallback } from 'react';
import { useAuth } from '../auth';
import { apiClient } from '../apiService';
import {
  getCourses, getCourse, createCourse, updateCourse, deleteCourse,
  getCourseModules, createCourseModule, updateCourseModule, deleteCourseModule, reorderCourseModules,
  getCourseLessons, createCourseLesson, updateCourseLesson, deleteCourseLesson, reorderCourseLessons,
  uploadCourseCover, uploadCourseLessonVideo, uploadCourseLessonMaterial, deleteCourseLessonMaterial,
  getHomeworkList,
} from '../apiService';
import './CourseManager.css';

/**
 * CourseManager — Конструктор курсов для Администратора.
 * Позволяет создавать, редактировать курсы с модулями и уроками.
 */
const CourseManager = () => {
  const { user } = useAuth();

  // ═══ State ═══
  const [courses, setCourses] = useState([]);
  const [loading, setLoading] = useState(true);
  const [message, setMessage] = useState(null);
  const [view, setView] = useState('list'); // 'list' | 'editor'
  const [editingCourse, setEditingCourse] = useState(null);

  // ═══ Load courses ═══
  const loadCourses = useCallback(async () => {
    try {
      setLoading(true);
      const res = await getCourses();
      setCourses(res.data.results || res.data || []);
    } catch (err) {
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

  // ═══ Course CRUD ═══
  const handleCreateCourse = async () => {
    try {
      const res = await createCourse({
        title: 'Новый курс',
        description: '',
        status: 'draft',
      });
      showMessage('Курс создан!');
      openEditor(res.data);
      loadCourses();
    } catch (err) {
      showMessage(err.response?.data?.detail || 'Ошибка создания курса', 'error');
    }
  };

  const handleDeleteCourse = async (courseId, e) => {
    e.stopPropagation();
    if (!window.confirm('Удалить этот курс и всё его содержимое?')) return;
    try {
      await deleteCourse(courseId);
      setCourses(prev => prev.filter(c => c.id !== courseId));
      showMessage('Курс удалён');
      if (editingCourse?.id === courseId) {
        setView('list');
        setEditingCourse(null);
      }
    } catch (err) {
      showMessage('Ошибка удаления', 'error');
    }
  };

  const openEditor = (course) => {
    setEditingCourse(course);
    setView('editor');
  };

  const closeEditor = () => {
    setView('list');
    setEditingCourse(null);
    loadCourses();
  };

  // ═══ Render ═══
  if (loading && view === 'list') {
    return (
      <div className="course-manager">
        <div className="cm-loading">
          <div className="cm-spinner" />
          <p>Загрузка курсов…</p>
        </div>
      </div>
    );
  }

  return (
    <div className="course-manager">
      {message && (
        <div className={`cm-message ${message.type}`}>{message.text}</div>
      )}

      {view === 'list' && (
        <>
          <div className="cm-header">
            <h1>📚 Конструктор курсов</h1>
            <div className="cm-header-actions">
              <button className="cm-btn cm-btn-primary" onClick={handleCreateCourse}>
                ➕ Создать курс
              </button>
            </div>
          </div>

          {courses.length === 0 ? (
            <div className="cm-empty">
              <div className="cm-empty-icon">📚</div>
              <h3>Курсов пока нет</h3>
              <p>Создайте свой первый курс с уроками, видео и материалами</p>
              <button className="cm-btn cm-btn-primary" onClick={handleCreateCourse}>
                ➕ Создать первый курс
              </button>
            </div>
          ) : (
            <div className="cm-courses-grid">
              {courses.map(course => (
                <div
                  key={course.id}
                  className="cm-course-card"
                  onClick={() => openEditor(course)}
                >
                  <div className="cm-course-cover">
                    {course.cover_url ? (
                      <img src={course.cover_url} alt={course.title} />
                    ) : (
                      <div className="cm-course-cover-placeholder">📖</div>
                    )}
                    <span className={`cm-course-status-badge ${course.status || (course.is_published ? 'published' : 'draft')}`}>
                      {course.status === 'published' ? 'Опубликован' :
                       course.status === 'archived' ? 'Архив' : 'Черновик'}
                    </span>
                  </div>
                  <div className="cm-course-body">
                    <h3>{course.title}</h3>
                    <p>{course.short_description || course.description || 'Без описания'}</p>
                    <div className="cm-course-meta">
                      <span>📝 {course.lessons_count || 0} уроков</span>
                      <span>📦 {course.modules_count || 0} модулей</span>
                      {course.price && <span>💰 {course.price} ₽</span>}
                      <span>👥 {course.student_count || 0}</span>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </>
      )}

      {view === 'editor' && editingCourse && (
        <CourseEditor
          courseId={editingCourse.id}
          onClose={closeEditor}
          showMessage={showMessage}
        />
      )}
    </div>
  );
};


// ═══════════════════════════════════════════════════════════════
// COURSE EDITOR
// ═══════════════════════════════════════════════════════════════

const CourseEditor = ({ courseId, onClose, showMessage }) => {
  const [course, setCourse] = useState(null);
  const [modules, setModules] = useState([]);
  const [lessons, setLessons] = useState([]);
  const [homeworks, setHomeworks] = useState([]);
  const [loading, setLoading] = useState(true);
  const [activeTab, setActiveTab] = useState('info'); // 'info' | 'constructor'
  const [expandedModules, setExpandedModules] = useState({});
  const [editingLesson, setEditingLesson] = useState(null);
  const [editingModule, setEditingModule] = useState(null);
  const [saving, setSaving] = useState(false);
  const [uploading, setUploading] = useState({});

  // ═══ Course form state ═══
  const [form, setForm] = useState({
    title: '', description: '', short_description: '',
    price: '', duration: '', status: 'draft',
  });

  // ═══ Load data ═══
  const loadData = useCallback(async () => {
    try {
      setLoading(true);
      const [courseRes, modulesRes, lessonsRes, hwRes] = await Promise.all([
        getCourse(courseId),
        getCourseModules(courseId),
        getCourseLessons(courseId),
        getHomeworkList().catch(() => ({ data: [] })),
      ]);

      const courseData = courseRes.data;
      setCourse(courseData);
      setForm({
        title: courseData.title || '',
        description: courseData.description || '',
        short_description: courseData.short_description || '',
        price: courseData.price || '',
        duration: courseData.duration || '',
        status: courseData.status || 'draft',
      });

      const mods = modulesRes.data.results || modulesRes.data || [];
      setModules(mods);

      const lsns = lessonsRes.data.results || lessonsRes.data || [];
      setLessons(lsns);

      const hws = hwRes.data.results || hwRes.data || [];
      setHomeworks(hws);

      // Expand all modules by default
      const exp = {};
      mods.forEach(m => { exp[m.id] = true; });
      setExpandedModules(exp);
    } catch (err) {
      showMessage('Ошибка загрузки данных курса', 'error');
    } finally {
      setLoading(false);
    }
  }, [courseId, showMessage]);

  useEffect(() => { loadData(); }, [loadData]);

  // ═══ Save course info ═══
  const handleSaveCourse = async () => {
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

  // ═══ Cover upload ═══
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

  // ═══ Module CRUD ═══
  const handleAddModule = async () => {
    try {
      const newOrder = modules.length;
      await createCourseModule({ course: courseId, title: 'Новый модуль', order: newOrder });
      showMessage('Модуль добавлен');
      loadData();
    } catch (err) {
      showMessage('Ошибка создания модуля', 'error');
    }
  };

  const handleSaveModule = async (moduleId, data) => {
    try {
      await updateCourseModule(moduleId, { ...data, course: courseId });
      setEditingModule(null);
      loadData();
    } catch (err) {
      showMessage('Ошибка сохранения модуля', 'error');
    }
  };

  const handleDeleteModule = async (moduleId) => {
    if (!window.confirm('Удалить модуль? Уроки модуля останутся без модуля.')) return;
    try {
      await deleteCourseModule(moduleId);
      showMessage('Модуль удалён');
      loadData();
    } catch (err) {
      showMessage('Ошибка удаления модуля', 'error');
    }
  };

  const handleMoveModule = async (moduleId, direction) => {
    const idx = modules.findIndex(m => m.id === moduleId);
    if ((direction === 'up' && idx === 0) || (direction === 'down' && idx === modules.length - 1)) return;
    const newModules = [...modules];
    const swapIdx = direction === 'up' ? idx - 1 : idx + 1;
    [newModules[idx], newModules[swapIdx]] = [newModules[swapIdx], newModules[idx]];
    const items = newModules.map((m, i) => ({ id: m.id, order: i }));
    setModules(newModules.map((m, i) => ({ ...m, order: i })));
    try {
      await reorderCourseModules(items);
    } catch (err) {
      showMessage('Ошибка перемещения', 'error');
      loadData();
    }
  };

  // ═══ Lesson CRUD ═══
  const handleAddLesson = async (moduleId = null) => {
    const moduleLessons = lessons.filter(l => l.module === moduleId);
    const newOrder = moduleLessons.length;
    try {
      await createCourseLesson({
        course: courseId,
        module: moduleId,
        title: 'Новый урок',
        order: newOrder,
      });
      showMessage('Урок добавлен');
      loadData();
    } catch (err) {
      showMessage('Ошибка создания урока', 'error');
    }
  };

  const handleSaveLesson = async (lessonData) => {
    try {
      await updateCourseLesson(lessonData.id, {
        ...lessonData,
        course: courseId,
      });
      setEditingLesson(null);
      showMessage('Урок сохранён');
      loadData();
    } catch (err) {
      showMessage('Ошибка сохранения урока', 'error');
    }
  };

  const handleDeleteLesson = async (lessonId) => {
    if (!window.confirm('Удалить этот урок?')) return;
    try {
      await deleteCourseLesson(lessonId);
      showMessage('Урок удалён');
      loadData();
    } catch (err) {
      showMessage('Ошибка удаления урока', 'error');
    }
  };

  const handleMoveLesson = async (lessonId, moduleId, direction) => {
    const moduleLessons = lessons
      .filter(l => l.module === moduleId)
      .sort((a, b) => a.order - b.order);
    const idx = moduleLessons.findIndex(l => l.id === lessonId);
    if ((direction === 'up' && idx === 0) || (direction === 'down' && idx === moduleLessons.length - 1)) return;
    const newArr = [...moduleLessons];
    const swapIdx = direction === 'up' ? idx - 1 : idx + 1;
    [newArr[idx], newArr[swapIdx]] = [newArr[swapIdx], newArr[idx]];
    const items = newArr.map((l, i) => ({ id: l.id, order: i, module: moduleId }));
    // Optimistic update
    setLessons(prev => {
      const others = prev.filter(l => l.module !== moduleId);
      return [...others, ...newArr.map((l, i) => ({ ...l, order: i }))];
    });
    try {
      await reorderCourseLessons(items);
    } catch {
      loadData();
    }
  };

  // ═══ Video upload for lesson ═══
  const handleVideoUpload = async (lessonId, file) => {
    if (!file) return;
    const key = `video-${lessonId}`;
    setUploading(prev => ({ ...prev, [key]: true }));
    try {
      const fd = new FormData();
      fd.append('video', file);
      const res = await uploadCourseLessonVideo(courseId, lessonId, fd);
      const provider = res.data?.provider;
      if (provider === 'kinescope' && res.data?.status === 'processing') {
        showMessage('Видео отправлено на обработку в Kinescope. Статус обновится автоматически.');
      } else {
        showMessage('Видео загружено!');
      }
      loadData();
    } catch (err) {
      showMessage(err.response?.data?.error || 'Ошибка загрузки видео', 'error');
    } finally {
      setUploading(prev => ({ ...prev, [key]: false }));
    }
  };

  // ═══ Toggle module expand ═══
  const toggleModule = (moduleId) => {
    setExpandedModules(prev => ({ ...prev, [moduleId]: !prev[moduleId] }));
  };

  if (loading) {
    return (
      <div className="cm-editor">
        <div className="cm-loading">
          <div className="cm-spinner" />
          <p>Загрузка курса…</p>
        </div>
      </div>
    );
  }

  const lessonsWithoutModule = lessons.filter(l => !l.module).sort((a, b) => a.order - b.order);

  return (
    <div className="cm-editor">
      {/* Header */}
      <div className="cm-editor-header">
        <div className="cm-editor-header-left">
          <button className="cm-back-btn" onClick={onClose} title="Назад к списку">←</button>
          <h2>{form.title || 'Редактирование курса'}</h2>
        </div>
        <div className="cm-editor-header-right">
          <button className="cm-btn cm-btn-secondary" onClick={onClose}>Закрыть</button>
          <button className="cm-btn cm-btn-primary" onClick={handleSaveCourse} disabled={saving}>
            {saving ? '⏳ Сохранение…' : '💾 Сохранить'}
          </button>
        </div>
      </div>

      {/* Tabs */}
      <div className="cm-tabs">
        <button
          className={`cm-tab ${activeTab === 'info' ? 'active' : ''}`}
          onClick={() => setActiveTab('info')}
        >
          📋 Основная информация
        </button>
        <button
          className={`cm-tab ${activeTab === 'constructor' ? 'active' : ''}`}
          onClick={() => setActiveTab('constructor')}
        >
          🏗️ Конструктор содержания
        </button>
      </div>

      {/* ═══ INFO TAB ═══ */}
      {activeTab === 'info' && (
        <div className="cm-tab-content">
          <div className="cm-form-group">
            <label>Название курса *</label>
            <input
              type="text"
              value={form.title}
              onChange={e => setForm(f => ({ ...f, title: e.target.value }))}
              placeholder="Введите название курса"
            />
          </div>

          <div className="cm-form-group">
            <label>Краткое описание</label>
            <input
              type="text"
              value={form.short_description}
              onChange={e => setForm(f => ({ ...f, short_description: e.target.value }))}
              placeholder="Краткое описание для каталога (до 500 символов)"
              maxLength={500}
            />
          </div>

          <div className="cm-form-group">
            <label>Полное описание</label>
            <textarea
              value={form.description}
              onChange={e => setForm(f => ({ ...f, description: e.target.value }))}
              placeholder="Подробное описание курса, что изучат ученики"
              rows={5}
            />
          </div>

          <div className="cm-form-row">
            <div className="cm-form-group">
              <label>Цена (₽)</label>
              <input
                type="number"
                value={form.price}
                onChange={e => setForm(f => ({ ...f, price: e.target.value }))}
                placeholder="0"
                min="0"
                step="0.01"
              />
            </div>
            <div className="cm-form-group">
              <label>Длительность</label>
              <input
                type="text"
                value={form.duration}
                onChange={e => setForm(f => ({ ...f, duration: e.target.value }))}
                placeholder='Например: "6 часов" или "3 месяца"'
              />
            </div>
          </div>

          <div className="cm-form-group">
            <label>Статус</label>
            <select
              value={form.status}
              onChange={e => setForm(f => ({ ...f, status: e.target.value }))}
            >
              <option value="draft">📝 Черновик</option>
              <option value="published">✅ Опубликован</option>
              <option value="archived">📦 В архиве</option>
            </select>
          </div>

          {/* Cover */}
          <div className="cm-form-group">
            <label>Обложка курса</label>
            <div className="cm-cover-section">
              <div className="cm-cover-preview">
                {course?.cover_url ? (
                  <img src={course.cover_url} alt="Обложка" />
                ) : (
                  <span style={{ fontSize: '2rem', opacity: 0.4 }}>📷</span>
                )}
              </div>
              <div>
                <label className="cm-btn cm-btn-secondary" style={{ cursor: 'pointer' }}>
                  {uploading.cover ? '⏳ Загрузка…' : '📷 Загрузить обложку'}
                  <input
                    type="file"
                    accept="image/jpeg,image/png,image/webp"
                    hidden
                    onChange={handleCoverUpload}
                    disabled={uploading.cover}
                  />
                </label>
                <p style={{ fontSize: '0.8rem', color: '#94a3b8', marginTop: '0.5rem' }}>
                  JPG, PNG или WebP. Максимум 5 МБ.
                </p>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* ═══ CONSTRUCTOR TAB ═══ */}
      {activeTab === 'constructor' && (
        <div className="cm-tab-content">
          <div className="cm-constructor">
            {/* Modules */}
            {modules.sort((a, b) => a.order - b.order).map((mod, modIdx) => {
              const moduleLessons = lessons
                .filter(l => l.module === mod.id)
                .sort((a, b) => a.order - b.order);
              const isExpanded = expandedModules[mod.id];

              return (
                <div key={mod.id} className="cm-module">
                  <div className="cm-module-header" onClick={() => toggleModule(mod.id)}>
                    <div className="cm-module-header-left">
                      <span className="cm-module-drag-handle">⠿</span>
                      {editingModule === mod.id ? (
                        <ModuleEditInline
                          module={mod}
                          onSave={(data) => handleSaveModule(mod.id, data)}
                          onCancel={() => setEditingModule(null)}
                        />
                      ) : (
                        <>
                          <span className="cm-module-title">{mod.title}</span>
                          <span className="cm-module-meta">
                            ({moduleLessons.length} {getLessonsWord(moduleLessons.length)})
                          </span>
                        </>
                      )}
                    </div>
                    <div className="cm-module-actions" onClick={e => e.stopPropagation()}>
                      <button
                        className="cm-move-btn" title="Вверх"
                        onClick={() => handleMoveModule(mod.id, 'up')}
                        disabled={modIdx === 0}
                      >▲</button>
                      <button
                        className="cm-move-btn" title="Вниз"
                        onClick={() => handleMoveModule(mod.id, 'down')}
                        disabled={modIdx === modules.length - 1}
                      >▼</button>
                      <button
                        className="cm-btn-icon"
                        title="Редактировать"
                        onClick={() => setEditingModule(mod.id)}
                      >✏️</button>
                      <button
                        className="cm-btn-icon danger"
                        title="Удалить модуль"
                        onClick={() => handleDeleteModule(mod.id)}
                      >🗑️</button>
                    </div>
                    <span className={`cm-module-toggle ${isExpanded ? 'open' : ''}`}>▸</span>
                  </div>

                  {isExpanded && (
                    <div className="cm-module-body">
                      <div className="cm-lessons-list">
                        {moduleLessons.map((lesson, lIdx) => (
                          <LessonRow
                            key={lesson.id}
                            lesson={lesson}
                            index={lIdx}
                            totalInModule={moduleLessons.length}
                            onEdit={() => setEditingLesson(lesson)}
                            onDelete={() => handleDeleteLesson(lesson.id)}
                            onMove={(dir) => handleMoveLesson(lesson.id, mod.id, dir)}
                            onVideoUpload={(file) => handleVideoUpload(lesson.id, file)}
                            uploading={uploading[`video-${lesson.id}`]}
                          />
                        ))}
                      </div>
                      <button className="cm-add-lesson-btn" onClick={() => handleAddLesson(mod.id)}>
                        ➕ Добавить урок
                      </button>
                    </div>
                  )}
                </div>
              );
            })}

            {/* Lessons without module */}
            {lessonsWithoutModule.length > 0 && (
              <div className="cm-module">
                <div className="cm-module-header" onClick={() => toggleModule('none')}>
                  <div className="cm-module-header-left">
                    <span className="cm-module-title" style={{ fontStyle: 'italic', color: '#94a3b8' }}>
                      Без модуля
                    </span>
                    <span className="cm-module-meta">
                      ({lessonsWithoutModule.length} {getLessonsWord(lessonsWithoutModule.length)})
                    </span>
                  </div>
                  <span className={`cm-module-toggle ${expandedModules['none'] ? 'open' : ''}`}>▸</span>
                </div>
                {expandedModules['none'] && (
                  <div className="cm-module-body">
                    <div className="cm-lessons-list">
                      {lessonsWithoutModule.map((lesson, lIdx) => (
                        <LessonRow
                          key={lesson.id}
                          lesson={lesson}
                          index={lIdx}
                          totalInModule={lessonsWithoutModule.length}
                          onEdit={() => setEditingLesson(lesson)}
                          onDelete={() => handleDeleteLesson(lesson.id)}
                          onMove={(dir) => handleMoveLesson(lesson.id, null, dir)}
                          onVideoUpload={(file) => handleVideoUpload(lesson.id, file)}
                          uploading={uploading[`video-${lesson.id}`]}
                        />
                      ))}
                    </div>
                  </div>
                )}
              </div>
            )}

            {/* Add buttons */}
            <div style={{ display: 'flex', gap: '0.75rem' }}>
              <button className="cm-add-module-btn" onClick={handleAddModule} style={{ flex: 1 }}>
                📦 Добавить модуль
              </button>
              <button className="cm-add-module-btn" onClick={() => handleAddLesson(null)} style={{ flex: 1 }}>
                📝 Добавить урок (без модуля)
              </button>
            </div>
          </div>
        </div>
      )}

      {/* ═══ LESSON EDIT MODAL ═══ */}
      {editingLesson && (
        <LessonEditModal
          lesson={editingLesson}
          modules={modules}
          homeworks={homeworks}
          courseId={courseId}
          onSave={handleSaveLesson}
          onClose={() => setEditingLesson(null)}
          showMessage={showMessage}
          onReload={loadData}
        />
      )}
    </div>
  );
};


// ═══════════════════════════════════════════════════════════════
// LessonRow — one lesson in the list
// ═══════════════════════════════════════════════════════════════

const LessonRow = ({ lesson, index, totalInModule, onEdit, onDelete, onMove, onVideoUpload, uploading }) => (
  <div className="cm-lesson-row">
    <div className="cm-lesson-order">{index + 1}</div>
    <div className="cm-lesson-info">
      <div className="cm-lesson-info-title">{lesson.title}</div>
      <div className="cm-lesson-badges">
        {lesson.video_url && lesson.video_status !== 'processing' && lesson.video_status !== 'error' && (
          <span className="cm-lesson-badge video">
            {lesson.video_provider === 'kinescope' ? '🎬 Kinescope' : '🎬 Видео'}
          </span>
        )}
        {lesson.video_status === 'processing' && (
          <span className="cm-lesson-badge video" style={{ background: '#ff9800', color: '#fff' }}>⏳ Обрабатывается</span>
        )}
        {lesson.video_status === 'error' && (
          <span className="cm-lesson-badge video" style={{ background: '#f44336', color: '#fff' }}>❌ Ошибка видео</span>
        )}
        {lesson.content && <span className="cm-lesson-badge text">📄 Текст</span>}
        {lesson.homework && <span className="cm-lesson-badge homework">📝 ДЗ{lesson.homework_title ? `: ${lesson.homework_title}` : ''}</span>}
        {lesson.is_free_preview && <span className="cm-lesson-badge preview">👁️ Превью</span>}
        {lesson.materials && lesson.materials.length > 0 && (
          <span className="cm-lesson-badge file">📎 {lesson.materials.length} файл(ов)</span>
        )}
      </div>
    </div>
    <div className="cm-lesson-actions">
      <button className="cm-move-btn" onClick={() => onMove('up')} disabled={index === 0} title="Вверх">▲</button>
      <button className="cm-move-btn" onClick={() => onMove('down')} disabled={index === totalInModule - 1} title="Вниз">▼</button>
      <label className="cm-btn-icon" title="Загрузить видео" style={{ cursor: 'pointer' }}>
        {uploading ? '⏳' : '🎥'}
        <input
          type="file"
          accept="video/mp4,video/webm,video/quicktime"
          hidden
          onChange={(e) => onVideoUpload(e.target.files[0])}
          disabled={uploading}
        />
      </label>
      <button className="cm-btn-icon" onClick={onEdit} title="Редактировать">✏️</button>
      <button className="cm-btn-icon danger" onClick={onDelete} title="Удалить">🗑️</button>
    </div>
  </div>
);


// ═══════════════════════════════════════════════════════════════
// ModuleEditInline — inline module title edit
// ═══════════════════════════════════════════════════════════════

const ModuleEditInline = ({ module, onSave, onCancel }) => {
  const [title, setTitle] = useState(module.title);
  return (
    <div className="cm-module-edit" onClick={e => e.stopPropagation()}>
      <input
        type="text"
        value={title}
        onChange={e => setTitle(e.target.value)}
        autoFocus
        onKeyDown={e => {
          if (e.key === 'Enter') onSave({ title, description: module.description, order: module.order });
          if (e.key === 'Escape') onCancel();
        }}
      />
      <button className="cm-btn cm-btn-small cm-btn-primary" onClick={() => onSave({ title, description: module.description, order: module.order })}>✓</button>
      <button className="cm-btn cm-btn-small cm-btn-secondary" onClick={onCancel}>✕</button>
    </div>
  );
};


// ═══════════════════════════════════════════════════════════════
// LessonEditModal — Editing a lesson
// ═══════════════════════════════════════════════════════════════

const LessonEditModal = ({ lesson, modules, homeworks, courseId, onSave, onClose, showMessage, onReload }) => {
  const [form, setForm] = useState({
    id: lesson.id,
    title: lesson.title || '',
    video_url: lesson.video_url || '',
    content: lesson.content || '',
    duration: lesson.duration || '',
    is_free_preview: lesson.is_free_preview || false,
    module: lesson.module || null,
    homework: lesson.homework || null,
    order: lesson.order || 0,
  });
  const [materials, setMaterials] = useState(lesson.materials || []);
  const [uploadingMaterial, setUploadingMaterial] = useState(false);

  const handleSave = () => {
    onSave(form);
  };

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
    } catch (err) {
      showMessage('Ошибка удаления материала', 'error');
    }
  };

  return (
    <div className="cm-modal-overlay" onClick={onClose}>
      <div className="cm-modal" onClick={e => e.stopPropagation()}>
        <div className="cm-modal-header">
          <h3>Редактирование урока</h3>
          <button className="cm-modal-close" onClick={onClose}>✕</button>
        </div>

        <div className="cm-modal-body">
          <div className="cm-form-group">
            <label>Название урока *</label>
            <input
              type="text"
              value={form.title}
              onChange={e => setForm(f => ({ ...f, title: e.target.value }))}
              placeholder="Название урока"
            />
          </div>

          <div className="cm-form-row">
            <div className="cm-form-group">
              <label>Модуль</label>
              <select
                value={form.module || ''}
                onChange={e => setForm(f => ({ ...f, module: e.target.value ? Number(e.target.value) : null }))}
              >
                <option value="">— Без модуля —</option>
                {modules.map(m => (
                  <option key={m.id} value={m.id}>{m.title}</option>
                ))}
              </select>
            </div>
            <div className="cm-form-group">
              <label>Длительность</label>
              <input
                type="text"
                value={form.duration}
                onChange={e => setForm(f => ({ ...f, duration: e.target.value }))}
                placeholder='Напр. "15 мин" или "1 ч"'
              />
            </div>
          </div>

          <div className="cm-form-group">
            <label>Ссылка на видео</label>
            <input
              type="url"
              value={form.video_url}
              onChange={e => setForm(f => ({ ...f, video_url: e.target.value }))}
              placeholder="https://..."
            />
          </div>

          <div className="cm-form-group">
            <label>Текстовый контент (HTML)</label>
            <textarea
              value={form.content}
              onChange={e => setForm(f => ({ ...f, content: e.target.value }))}
              placeholder="Текстовый контент урока..."
              rows={6}
            />
          </div>

          <div className="cm-form-group">
            <label>Домашнее задание</label>
            <select
              value={form.homework || ''}
              onChange={e => setForm(f => ({ ...f, homework: e.target.value ? Number(e.target.value) : null }))}
            >
              <option value="">— Не привязано —</option>
              {homeworks.map(hw => (
                <option key={hw.id} value={hw.id}>{hw.title}</option>
              ))}
            </select>
          </div>

          <div className="cm-form-group">
            <label className="cm-checkbox">
              <input
                type="checkbox"
                checked={form.is_free_preview}
                onChange={e => setForm(f => ({ ...f, is_free_preview: e.target.checked }))}
              />
              Бесплатный превью (доступен без покупки)
            </label>
          </div>

          {/* Materials */}
          <div className="cm-form-group">
            <label>Материалы для скачивания</label>
            {materials.length > 0 && (
              <div className="cm-materials-list">
                {materials.map(mat => (
                  <div key={mat.id} className="cm-material-row">
                    <span className="cm-material-name">
                      📎 <a href={mat.url} target="_blank" rel="noopener noreferrer">{mat.name}</a>
                    </span>
                    <button
                      className="cm-btn-icon danger"
                      onClick={() => handleDeleteMaterial(mat.id)}
                      title="Удалить"
                    >🗑️</button>
                  </div>
                ))}
              </div>
            )}
            <div style={{ marginTop: '0.5rem' }}>
              <label className="cm-upload-area" style={{ display: 'block' }}>
                {uploadingMaterial ? '⏳ Загрузка файла…' : '📁 Нажмите для загрузки файла (PDF, DOC, ZIP и т.д.)'}
                <input
                  type="file"
                  hidden
                  onChange={handleMaterialUpload}
                  disabled={uploadingMaterial}
                />
              </label>
            </div>
          </div>
        </div>

        <div className="cm-modal-footer">
          <button className="cm-btn cm-btn-secondary" onClick={onClose}>Отмена</button>
          <button className="cm-btn cm-btn-primary" onClick={handleSave}>💾 Сохранить</button>
        </div>
      </div>
    </div>
  );
};


// ═══ Helpers ═══

function getLessonsWord(count) {
  const abs = Math.abs(count) % 100;
  const last = abs % 10;
  if (abs >= 11 && abs <= 19) return 'уроков';
  if (last === 1) return 'урок';
  if (last >= 2 && last <= 4) return 'урока';
  return 'уроков';
}


export default CourseManager;
