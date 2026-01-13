import React, { useState, useEffect, useCallback } from 'react';
import './TeacherMaterialsPage.css';
import api, { withScheduleApiBase } from '../../apiService';
import RecordingCard from './RecordingCard';
import RecordingPlayer from './RecordingPlayer';
import { ConfirmModal, Select, ToastContainer, Button, Input, Modal } from '../../shared/components';

/**
 * TeacherMaterialsPage - Страница материалов урока
 * Объединяет записи, доски Miro, конспекты и другие материалы в одном месте
 */
function TeacherMaterialsPage() {
  // Активная вкладка
  const [activeTab, setActiveTab] = useState('recordings');
  
  // Данные
  const [recordings, setRecordings] = useState([]);
  const [materials, setMaterials] = useState({ miro: [], notes: [], document: [], link: [] });
  const [lessons, setLessons] = useState([]);
  const [groups, setGroups] = useState([]);
  
  // UI State
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [searchTerm, setSearchTerm] = useState('');
  const [groupFilter, setGroupFilter] = useState('all');
  const [selectedRecording, setSelectedRecording] = useState(null);
  
  // Модальные окна
  const [showAddMiroModal, setShowAddMiroModal] = useState(false);
  const [showAddNotesModal, setShowAddNotesModal] = useState(false);
  const [showAddDocModal, setShowAddDocModal] = useState(false);
  const [showUploadModal, setShowUploadModal] = useState(false);
  
  // Формы
  const [miroForm, setMiroForm] = useState({
    board_url: '',
    title: '',
    description: '',
    lesson_id: '',
    visibility: 'all_teacher_groups'
  });
  
  const [notesForm, setNotesForm] = useState({
    title: '',
    content: '',
    description: '',
    lesson_id: '',
    visibility: 'all_teacher_groups'
  });
  
  const [docForm, setDocForm] = useState({
    title: '',
    file_url: '',
    description: '',
    lesson_id: '',
    material_type: 'document',
    visibility: 'all_teacher_groups'
  });
  
  // Stats
  const [stats, setStats] = useState({
    recordings: 0,
    miro: 0,
    notes: 0,
    documents: 0
  });
  
  // Toasts
  const [toasts, setToasts] = useState([]);
  const [confirmModal, setConfirmModal] = useState({ isOpen: false });
  
  // Miro status
  const [miroStatus, setMiroStatus] = useState(null);

  const addToast = useCallback((toast) => {
    const id = Date.now() + Math.random();
    setToasts(prev => [...prev, { id, ...toast }]);
    setTimeout(() => removeToast(id), 5000);
    return id;
  }, []);

  const removeToast = useCallback((id) => {
    setToasts(prev => prev.filter(t => t.id !== id));
  }, []);

  useEffect(() => {
    loadAllData();
    loadMiroStatus();
  }, []);

  const loadAllData = async () => {
    setLoading(true);
    try {
      await Promise.all([
        loadRecordings(),
        loadMaterials(),
        loadLessons(),
        loadGroups()
      ]);
    } catch (err) {
      console.error('Error loading data:', err);
      setError('Не удалось загрузить данные');
    } finally {
      setLoading(false);
    }
  };

  const loadRecordings = async () => {
    try {
      const response = await api.get('recordings/teacher/', withScheduleApiBase());
      const data = response.data.results || response.data;
      setRecordings(Array.isArray(data) ? data : []);
    } catch (err) {
      console.error('Error loading recordings:', err);
    }
  };

  const loadMaterials = async () => {
    try {
      const response = await api.get('lesson-materials/teacher_materials/', withScheduleApiBase());
      if (response.data.materials) {
        setMaterials(response.data.materials);
        setStats({
          ...stats,
          miro: response.data.stats?.miro_count || 0,
          notes: response.data.stats?.notes_count || 0,
          documents: response.data.stats?.documents_count || 0
        });
      }
    } catch (err) {
      console.error('Error loading materials:', err);
    }
  };

  const loadLessons = async () => {
    try {
      const response = await api.get('lessons', withScheduleApiBase());
      const data = response.data.results || response.data;
      const now = new Date();
      const pastWindow = new Date(now.getTime() - 60 * 24 * 60 * 60 * 1000); // 60 дней
      const filtered = (Array.isArray(data) ? data : []).filter(l => {
        const dt = l.start_time ? new Date(l.start_time) : null;
        return dt && dt >= pastWindow;
      });
      setLessons(filtered);
    } catch (err) {
      console.error('Error loading lessons:', err);
    }
  };

  const loadGroups = async () => {
    try {
      const response = await api.get('groups', withScheduleApiBase());
      const data = response.data.results || response.data;
      setGroups(Array.isArray(data) ? data : []);
    } catch (err) {
      console.error('Error loading groups:', err);
    }
  };

  const loadMiroStatus = async () => {
    try {
      const response = await api.get('miro/status/', withScheduleApiBase());
      setMiroStatus(response.data);
    } catch (err) {
      console.error('Error loading Miro status:', err);
    }
  };

  // Обработчики добавления материалов
  const handleAddMiroBoard = async (e) => {
    e.preventDefault();
    
    if (!miroForm.board_url) {
      addToast({ type: 'warning', title: 'Внимание', message: 'Введите URL доски Miro' });
      return;
    }

    try {
      const response = await api.post('miro/add-board/', miroForm, withScheduleApiBase());
      addToast({ type: 'success', title: 'Успех', message: 'Доска Miro добавлена!' });
      setShowAddMiroModal(false);
      setMiroForm({ board_url: '', title: '', description: '', lesson_id: '', visibility: 'all_teacher_groups' });
      loadMaterials();
    } catch (err) {
      addToast({ 
        type: 'error', 
        title: 'Ошибка', 
        message: err.response?.data?.error || 'Не удалось добавить доску' 
      });
    }
  };

  const handleAddNotes = async (e) => {
    e.preventDefault();
    
    if (!notesForm.title) {
      addToast({ type: 'warning', title: 'Внимание', message: 'Введите название конспекта' });
      return;
    }

    try {
      const response = await api.post('materials/add-notes/', notesForm, withScheduleApiBase());
      addToast({ type: 'success', title: 'Успех', message: 'Конспект добавлен!' });
      setShowAddNotesModal(false);
      setNotesForm({ title: '', content: '', description: '', lesson_id: '', visibility: 'all_teacher_groups' });
      loadMaterials();
    } catch (err) {
      addToast({ 
        type: 'error', 
        title: 'Ошибка', 
        message: err.response?.data?.error || 'Не удалось добавить конспект' 
      });
    }
  };

  const handleAddDocument = async (e) => {
    e.preventDefault();
    
    if (!docForm.title || !docForm.file_url) {
      addToast({ type: 'warning', title: 'Внимание', message: 'Заполните название и ссылку' });
      return;
    }

    try {
      const response = await api.post('materials/add-document/', docForm, withScheduleApiBase());
      addToast({ type: 'success', title: 'Успех', message: 'Документ добавлен!' });
      setShowAddDocModal(false);
      setDocForm({ title: '', file_url: '', description: '', lesson_id: '', material_type: 'document', visibility: 'all_teacher_groups' });
      loadMaterials();
    } catch (err) {
      addToast({ 
        type: 'error', 
        title: 'Ошибка', 
        message: err.response?.data?.error || 'Не удалось добавить документ' 
      });
    }
  };

  const handleDeleteMaterial = async (materialId) => {
    setConfirmModal({
      isOpen: true,
      title: 'Удаление материала',
      message: 'Вы уверены, что хотите удалить этот материал?',
      variant: 'danger',
      confirmText: 'Удалить',
      onConfirm: async () => {
        try {
          await api.delete(`lesson-materials/${materialId}/`, withScheduleApiBase());
          addToast({ type: 'success', title: 'Успех', message: 'Материал удален' });
          loadMaterials();
        } catch (err) {
          addToast({ type: 'error', title: 'Ошибка', message: 'Не удалось удалить материал' });
        }
        setConfirmModal({ isOpen: false });
      }
    });
  };

  // Форматирование даты
  const formatDate = (dateStr) => {
    if (!dateStr) return '';
    return new Date(dateStr).toLocaleDateString('ru-RU', {
      day: '2-digit',
      month: '2-digit',
      year: 'numeric'
    });
  };

  // Опции для селектов
  const lessonOptions = [
    { value: '', label: '📚 Без привязки к уроку' },
    ...lessons.map(l => ({
      value: String(l.id),
      label: `${l.title || l.subject || 'Урок'} • ${l.group_name} (${formatDate(l.start_time)})`
    }))
  ];

  const visibilityOptions = [
    { value: 'all_teacher_groups', label: '👥 Все мои группы' },
    { value: 'lesson_group', label: '📖 Только группа урока' },
    { value: 'custom_groups', label: '✏️ Выбранные группы' }
  ];

  // Фильтрация
  const filterBySearch = (items, field = 'title') => {
    if (!searchTerm) return items;
    const term = searchTerm.toLowerCase();
    return items.filter(item => 
      (item[field] || '').toLowerCase().includes(term) ||
      (item.description || '').toLowerCase().includes(term)
    );
  };

  // Табы
  const tabs = [
    { id: 'recordings', label: '🎥 Записи', count: recordings.length },
    { id: 'miro', label: '🎨 Miro', count: materials.miro?.length || 0 },
    { id: 'notes', label: '📝 Конспекты', count: materials.notes?.length || 0 },
    { id: 'documents', label: '📄 Документы', count: (materials.document?.length || 0) + (materials.link?.length || 0) }
  ];

  if (loading) {
    return (
      <div className="materials-page">
        <div className="materials-loading">
          <div className="materials-spinner"></div>
          <p>Загрузка материалов...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="materials-page">
      <ToastContainer toasts={toasts} removeToast={removeToast} />
      
      {/* Header */}
      <header className="materials-header">
        <div className="materials-header-info">
          <h1>📚 Материалы уроков</h1>
          <p className="materials-subtitle">Записи, доски Miro, конспекты и документы</p>
        </div>
        
        <div className="materials-header-actions">
          <button className="materials-action-btn primary" onClick={() => setShowUploadModal(true)}>
            📤 Загрузить видео
          </button>
          <button className="materials-action-btn miro" onClick={() => setShowAddMiroModal(true)}>
            🎨 Добавить Miro
          </button>
          <button className="materials-action-btn notes" onClick={() => setShowAddNotesModal(true)}>
            📝 Добавить конспект
          </button>
          <button className="materials-action-btn doc" onClick={() => setShowAddDocModal(true)}>
            📎 Добавить документ
          </button>
        </div>
      </header>

      {/* Stats */}
      <div className="materials-stats">
        <div className="stat-card recordings">
          <span className="stat-icon">🎥</span>
          <div className="stat-info">
            <span className="stat-value">{recordings.length}</span>
            <span className="stat-label">Записей</span>
          </div>
        </div>
        <div className="stat-card miro">
          <span className="stat-icon">🎨</span>
          <div className="stat-info">
            <span className="stat-value">{materials.miro?.length || 0}</span>
            <span className="stat-label">Досок Miro</span>
          </div>
        </div>
        <div className="stat-card notes">
          <span className="stat-icon">📝</span>
          <div className="stat-info">
            <span className="stat-value">{materials.notes?.length || 0}</span>
            <span className="stat-label">Конспектов</span>
          </div>
        </div>
        <div className="stat-card documents">
          <span className="stat-icon">📄</span>
          <div className="stat-info">
            <span className="stat-value">{(materials.document?.length || 0) + (materials.link?.length || 0)}</span>
            <span className="stat-label">Документов</span>
          </div>
        </div>
      </div>

      {/* Search & Filters */}
      <div className="materials-filters">
        <div className="search-box">
          <span className="search-icon">🔍</span>
          <input
            type="text"
            placeholder="Поиск по названию..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
          />
        </div>
        
        <Select
          value={groupFilter}
          onChange={(e) => setGroupFilter(e.target.value)}
          options={[
            { value: 'all', label: 'Все группы' },
            ...groups.map(g => ({ value: String(g.id), label: g.name }))
          ]}
        />
      </div>

      {/* Tabs */}
      <div className="materials-tabs">
        {tabs.map(tab => (
          <button
            key={tab.id}
            className={`tab-btn ${activeTab === tab.id ? 'active' : ''}`}
            onClick={() => setActiveTab(tab.id)}
          >
            {tab.label}
            <span className="tab-count">{tab.count}</span>
          </button>
        ))}
      </div>

      {/* Content */}
      <div className="materials-content">
        {activeTab === 'recordings' && (
          <div className="recordings-grid">
            {filterBySearch(recordings, 'title').length === 0 ? (
              <div className="empty-state">
                <span className="empty-icon">🎥</span>
                <h3>Нет записей</h3>
                <p>Записи появятся автоматически после проведения уроков с включенной записью</p>
              </div>
            ) : (
              filterBySearch(recordings, 'title').map(recording => (
                <RecordingCard
                  key={recording.id}
                  recording={recording}
                  onPlay={() => setSelectedRecording(recording)}
                  onDelete={() => {}}
                  isTeacher={true}
                />
              ))
            )}
          </div>
        )}

        {activeTab === 'miro' && (
          <div className="miro-grid">
            {filterBySearch(materials.miro || []).length === 0 ? (
              <div className="empty-state">
                <span className="empty-icon">🎨</span>
                <h3>Нет досок Miro</h3>
                <p>Добавьте доску Miro по ссылке или создайте новую</p>
                <button className="add-btn" onClick={() => setShowAddMiroModal(true)}>
                  + Добавить доску
                </button>
              </div>
            ) : (
              filterBySearch(materials.miro || []).map(board => (
                <div key={board.id} className="material-card miro-card">
                  <div className="card-preview miro-preview">
                    {board.miro_embed_url ? (
                      <iframe
                        src={board.miro_embed_url}
                        frameBorder="0"
                        scrolling="no"
                        allow="fullscreen; clipboard-read; clipboard-write"
                        title={board.title}
                      />
                    ) : (
                      <div className="preview-placeholder">🎨</div>
                    )}
                  </div>
                  <div className="card-info">
                    <h3>{board.title}</h3>
                    {board.description && <p>{board.description}</p>}
                    <div className="card-meta">
                      {board.lesson_info && (
                        <span className="meta-item">📚 {board.lesson_info.title}</span>
                      )}
                      <span className="meta-item">👁 {board.views_count} просмотров</span>
                    </div>
                  </div>
                  <div className="card-actions">
                    <a 
                      href={board.miro_board_url} 
                      target="_blank" 
                      rel="noopener noreferrer"
                      className="action-btn primary"
                    >
                      Открыть в Miro
                    </a>
                    <button 
                      className="action-btn danger"
                      onClick={() => handleDeleteMaterial(board.id)}
                    >
                      Удалить
                    </button>
                  </div>
                </div>
              ))
            )}
          </div>
        )}

        {activeTab === 'notes' && (
          <div className="notes-grid">
            {filterBySearch(materials.notes || []).length === 0 ? (
              <div className="empty-state">
                <span className="empty-icon">📝</span>
                <h3>Нет конспектов</h3>
                <p>Создайте конспект урока для учеников</p>
                <button className="add-btn" onClick={() => setShowAddNotesModal(true)}>
                  + Создать конспект
                </button>
              </div>
            ) : (
              filterBySearch(materials.notes || []).map(note => (
                <div key={note.id} className="material-card notes-card">
                  <div className="card-icon">📝</div>
                  <div className="card-info">
                    <h3>{note.title}</h3>
                    {note.description && <p>{note.description}</p>}
                    {note.content && (
                      <div className="note-preview">
                        {note.content.substring(0, 200)}...
                      </div>
                    )}
                    <div className="card-meta">
                      {note.lesson_info && (
                        <span className="meta-item">📚 {note.lesson_info.title}</span>
                      )}
                      <span className="meta-item">👁 {note.views_count} просмотров</span>
                      <span className="meta-item">📅 {formatDate(note.created_at)}</span>
                    </div>
                  </div>
                  <div className="card-actions">
                    <button className="action-btn primary">Редактировать</button>
                    <button 
                      className="action-btn danger"
                      onClick={() => handleDeleteMaterial(note.id)}
                    >
                      Удалить
                    </button>
                  </div>
                </div>
              ))
            )}
          </div>
        )}

        {activeTab === 'documents' && (
          <div className="documents-grid">
            {filterBySearch([...(materials.document || []), ...(materials.link || [])]).length === 0 ? (
              <div className="empty-state">
                <span className="empty-icon">📄</span>
                <h3>Нет документов</h3>
                <p>Добавьте ссылки на документы, презентации или другие материалы</p>
                <button className="add-btn" onClick={() => setShowAddDocModal(true)}>
                  + Добавить документ
                </button>
              </div>
            ) : (
              filterBySearch([...(materials.document || []), ...(materials.link || [])]).map(doc => (
                <div key={doc.id} className="material-card doc-card">
                  <div className="card-icon">
                    {doc.material_type === 'link' ? '🔗' : '📄'}
                  </div>
                  <div className="card-info">
                    <h3>{doc.title}</h3>
                    {doc.description && <p>{doc.description}</p>}
                    <div className="card-meta">
                      {doc.file_size_mb && (
                        <span className="meta-item">💾 {doc.file_size_mb} MB</span>
                      )}
                      {doc.lesson_info && (
                        <span className="meta-item">📚 {doc.lesson_info.title}</span>
                      )}
                      <span className="meta-item">👁 {doc.views_count} просмотров</span>
                    </div>
                  </div>
                  <div className="card-actions">
                    <a 
                      href={doc.file_url} 
                      target="_blank" 
                      rel="noopener noreferrer"
                      className="action-btn primary"
                    >
                      Открыть
                    </a>
                    <button 
                      className="action-btn danger"
                      onClick={() => handleDeleteMaterial(doc.id)}
                    >
                      Удалить
                    </button>
                  </div>
                </div>
              ))
            )}
          </div>
        )}
      </div>

      {/* Recording Player Modal */}
      {selectedRecording && (
        <RecordingPlayer
          recording={selectedRecording}
          onClose={() => setSelectedRecording(null)}
        />
      )}

      {/* Add Miro Board Modal */}
      {showAddMiroModal && (
        <div className="modal-overlay" onClick={() => setShowAddMiroModal(false)}>
          <div className="modal-content" onClick={e => e.stopPropagation()}>
            <div className="modal-header">
              <h2>🎨 Добавить доску Miro</h2>
              <button className="modal-close" onClick={() => setShowAddMiroModal(false)}>✕</button>
            </div>
            <form onSubmit={handleAddMiroBoard} className="modal-form">
              <div className="form-field">
                <label>Ссылка на доску Miro *</label>
                <input
                  type="url"
                  value={miroForm.board_url}
                  onChange={(e) => setMiroForm({...miroForm, board_url: e.target.value})}
                  placeholder="https://miro.com/app/board/..."
                  required
                />
                <small>Скопируйте ссылку из адресной строки Miro</small>
              </div>
              
              <div className="form-field">
                <label>Название</label>
                <input
                  type="text"
                  value={miroForm.title}
                  onChange={(e) => setMiroForm({...miroForm, title: e.target.value})}
                  placeholder="Например: Разбор темы алгебры"
                />
              </div>
              
              <div className="form-field">
                <label>Описание</label>
                <textarea
                  value={miroForm.description}
                  onChange={(e) => setMiroForm({...miroForm, description: e.target.value})}
                  placeholder="Краткое описание содержимого доски"
                  rows={3}
                />
              </div>
              
              <div className="form-field">
                <label>Привязать к уроку</label>
                <Select
                  value={miroForm.lesson_id}
                  onChange={(e) => setMiroForm({...miroForm, lesson_id: e.target.value})}
                  options={lessonOptions}
                />
              </div>
              
              <div className="form-field">
                <label>Видимость</label>
                <Select
                  value={miroForm.visibility}
                  onChange={(e) => setMiroForm({...miroForm, visibility: e.target.value})}
                  options={visibilityOptions}
                />
              </div>
              
              <div className="modal-actions">
                <button type="button" onClick={() => setShowAddMiroModal(false)} className="btn-cancel">
                  Отмена
                </button>
                <button type="submit" className="btn-submit">
                  Добавить доску
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Add Notes Modal */}
      {showAddNotesModal && (
        <div className="modal-overlay" onClick={() => setShowAddNotesModal(false)}>
          <div className="modal-content large" onClick={e => e.stopPropagation()}>
            <div className="modal-header">
              <h2>📝 Создать конспект</h2>
              <button className="modal-close" onClick={() => setShowAddNotesModal(false)}>✕</button>
            </div>
            <form onSubmit={handleAddNotes} className="modal-form">
              <div className="form-field">
                <label>Название конспекта *</label>
                <input
                  type="text"
                  value={notesForm.title}
                  onChange={(e) => setNotesForm({...notesForm, title: e.target.value})}
                  placeholder="Например: Конспект урока по геометрии"
                  required
                />
              </div>
              
              <div className="form-field">
                <label>Краткое описание</label>
                <input
                  type="text"
                  value={notesForm.description}
                  onChange={(e) => setNotesForm({...notesForm, description: e.target.value})}
                  placeholder="О чем этот конспект"
                />
              </div>
              
              <div className="form-field">
                <label>Содержание конспекта</label>
                <textarea
                  value={notesForm.content}
                  onChange={(e) => setNotesForm({...notesForm, content: e.target.value})}
                  placeholder="Введите текст конспекта. Поддерживается Markdown."
                  rows={12}
                  className="notes-editor"
                />
                <small>Поддерживается Markdown разметка</small>
              </div>
              
              <div className="form-row">
                <div className="form-field">
                  <label>Привязать к уроку</label>
                  <Select
                    value={notesForm.lesson_id}
                    onChange={(e) => setNotesForm({...notesForm, lesson_id: e.target.value})}
                    options={lessonOptions}
                  />
                </div>
                
                <div className="form-field">
                  <label>Видимость</label>
                  <Select
                    value={notesForm.visibility}
                    onChange={(e) => setNotesForm({...notesForm, visibility: e.target.value})}
                    options={visibilityOptions}
                  />
                </div>
              </div>
              
              <div className="modal-actions">
                <button type="button" onClick={() => setShowAddNotesModal(false)} className="btn-cancel">
                  Отмена
                </button>
                <button type="submit" className="btn-submit">
                  Сохранить конспект
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Add Document Modal */}
      {showAddDocModal && (
        <div className="modal-overlay" onClick={() => setShowAddDocModal(false)}>
          <div className="modal-content" onClick={e => e.stopPropagation()}>
            <div className="modal-header">
              <h2>📎 Добавить документ</h2>
              <button className="modal-close" onClick={() => setShowAddDocModal(false)}>✕</button>
            </div>
            <form onSubmit={handleAddDocument} className="modal-form">
              <div className="form-field">
                <label>Название документа *</label>
                <input
                  type="text"
                  value={docForm.title}
                  onChange={(e) => setDocForm({...docForm, title: e.target.value})}
                  placeholder="Например: Презентация к уроку"
                  required
                />
              </div>
              
              <div className="form-field">
                <label>Ссылка на документ *</label>
                <input
                  type="url"
                  value={docForm.file_url}
                  onChange={(e) => setDocForm({...docForm, file_url: e.target.value})}
                  placeholder="https://drive.google.com/... или https://..."
                  required
                />
                <small>Google Drive, Dropbox, или любая другая ссылка</small>
              </div>
              
              <div className="form-field">
                <label>Описание</label>
                <textarea
                  value={docForm.description}
                  onChange={(e) => setDocForm({...docForm, description: e.target.value})}
                  placeholder="Краткое описание документа"
                  rows={2}
                />
              </div>
              
              <div className="form-field">
                <label>Тип материала</label>
                <Select
                  value={docForm.material_type}
                  onChange={(e) => setDocForm({...docForm, material_type: e.target.value})}
                  options={[
                    { value: 'document', label: '📄 Документ' },
                    { value: 'link', label: '🔗 Ссылка' },
                    { value: 'image', label: '🖼 Изображение' }
                  ]}
                />
              </div>
              
              <div className="form-row">
                <div className="form-field">
                  <label>Привязать к уроку</label>
                  <Select
                    value={docForm.lesson_id}
                    onChange={(e) => setDocForm({...docForm, lesson_id: e.target.value})}
                    options={lessonOptions}
                  />
                </div>
                
                <div className="form-field">
                  <label>Видимость</label>
                  <Select
                    value={docForm.visibility}
                    onChange={(e) => setDocForm({...docForm, visibility: e.target.value})}
                    options={visibilityOptions}
                  />
                </div>
              </div>
              
              <div className="modal-actions">
                <button type="button" onClick={() => setShowAddDocModal(false)} className="btn-cancel">
                  Отмена
                </button>
                <button type="submit" className="btn-submit">
                  Добавить документ
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Confirm Modal */}
      <ConfirmModal
        isOpen={confirmModal.isOpen}
        title={confirmModal.title}
        message={confirmModal.message}
        variant={confirmModal.variant}
        confirmText={confirmModal.confirmText}
        cancelText="Отмена"
        onConfirm={confirmModal.onConfirm}
        onCancel={() => setConfirmModal({ isOpen: false })}
      />
    </div>
  );
}

export default TeacherMaterialsPage;
