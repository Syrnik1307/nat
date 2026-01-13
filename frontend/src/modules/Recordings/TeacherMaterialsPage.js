import React, { useState, useEffect, useCallback } from 'react';
import './TeacherMaterialsPage.css';
import api, { withScheduleApiBase } from '../../apiService';
import { ConfirmModal, Select, ToastContainer, Modal } from '../../shared/components';

/**
 * TeacherMaterialsPage - Страница материалов урока
 * Записи, доски Miro, конспекты и документы
 */
function TeacherMaterialsPage() {
  const [activeTab, setActiveTab] = useState('miro');
  
  // Данные
  const [materials, setMaterials] = useState({ miro: [], notes: [], document: [], link: [] });
  const [lessons, setLessons] = useState([]);
  const [groups, setGroups] = useState([]);
  
  // UI State
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [searchTerm, setSearchTerm] = useState('');
  const [groupFilter, setGroupFilter] = useState('all');
  
  // Модальные окна
  const [showAddMiroModal, setShowAddMiroModal] = useState(false);
  const [showAddNotesModal, setShowAddNotesModal] = useState(false);
  const [showAddDocModal, setShowAddDocModal] = useState(false);
  
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

  // Toasts & Confirm
  const [toasts, setToasts] = useState([]);
  const [confirmModal, setConfirmModal] = useState({ isOpen: false });
  
  // Miro status
  const [miroStatus, setMiroStatus] = useState(null);
  const [miroBoards, setMiroBoards] = useState([]);

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
    checkMiroCallback();
  }, []);

  const checkMiroCallback = () => {
    const params = new URLSearchParams(window.location.search);
    if (params.get('miro_connected') === 'true') {
      window.history.replaceState({}, '', window.location.pathname);
      addToast({ type: 'success', title: 'Miro подключен', message: 'Теперь вы можете добавлять доски из аккаунта' });
      loadMiroStatus();
    } else if (params.get('miro_error')) {
      window.history.replaceState({}, '', window.location.pathname);
      addToast({ type: 'error', title: 'Ошибка Miro', message: params.get('miro_error') });
    }
  };

  const loadAllData = async () => {
    setLoading(true);
    try {
      await Promise.all([
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

  const loadMaterials = async () => {
    try {
      const response = await api.get('lesson-materials/teacher_materials/', withScheduleApiBase());
      if (response.data.materials) {
        setMaterials(response.data.materials);
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
      const pastWindow = new Date(now.getTime() - 60 * 24 * 60 * 60 * 1000);
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
      const response = await api.get('miro/oauth/status/', withScheduleApiBase());
      setMiroStatus(response.data);
      if (response.data?.user_connected) {
        loadMiroBoards();
      }
    } catch (err) {
      console.error('Error loading Miro status:', err);
      try {
        const fallback = await api.get('miro/status/', withScheduleApiBase());
        setMiroStatus(fallback.data);
      } catch (err2) {
        console.error('Error loading Miro fallback:', err2);
      }
    }
  };

  const loadMiroBoards = async () => {
    try {
      const response = await api.get('miro/oauth/boards/', withScheduleApiBase());
      setMiroBoards(response.data?.boards || []);
    } catch (err) {
      console.error('Error loading Miro boards:', err);
    }
  };

  const handleConnectMiro = async () => {
    try {
      const response = await api.get('miro/oauth/start/', withScheduleApiBase());
      if (response.data?.auth_url) {
        window.location.href = response.data.auth_url;
      } else {
        addToast({ type: 'error', title: 'Ошибка', message: 'Не удалось получить ссылку авторизации' });
      }
    } catch (err) {
      addToast({ type: 'error', title: 'Ошибка', message: 'Не удалось начать авторизацию' });
    }
  };

  const handleDisconnectMiro = async () => {
    setConfirmModal({
      isOpen: true,
      title: 'Отключение Miro',
      message: 'Отключить интеграцию с Miro?',
      variant: 'warning',
      confirmText: 'Отключить',
      onConfirm: async () => {
        try {
          await api.post('miro/oauth/disconnect/', {}, withScheduleApiBase());
          addToast({ type: 'success', title: 'Готово', message: 'Miro отключен' });
          setMiroStatus(prev => ({ ...prev, user_connected: false }));
          setMiroBoards([]);
        } catch (err) {
          addToast({ type: 'error', title: 'Ошибка', message: 'Не удалось отключить' });
        }
        setConfirmModal({ isOpen: false });
      }
    });
  };

  const handleImportMiroBoard = async (board) => {
    try {
      await api.post('miro/oauth/import-board/', {
        board_id: board.id,
        title: board.name,
        description: board.description || '',
        visibility: 'all_teacher_groups'
      }, withScheduleApiBase());
      addToast({ type: 'success', title: 'Готово', message: `Доска "${board.name}" добавлена` });
      loadMaterials();
    } catch (err) {
      addToast({ type: 'error', title: 'Ошибка', message: 'Не удалось импортировать доску' });
    }
  };

  const handleAddMiroBoard = async (e) => {
    e.preventDefault();
    if (!miroForm.board_url) {
      addToast({ type: 'warning', title: 'Внимание', message: 'Введите URL доски' });
      return;
    }
    try {
      await api.post('miro/add-board/', miroForm, withScheduleApiBase());
      addToast({ type: 'success', title: 'Готово', message: 'Доска добавлена' });
      setShowAddMiroModal(false);
      setMiroForm({ board_url: '', title: '', description: '', lesson_id: '', visibility: 'all_teacher_groups' });
      loadMaterials();
    } catch (err) {
      addToast({ type: 'error', title: 'Ошибка', message: err.response?.data?.error || 'Не удалось добавить' });
    }
  };

  const handleAddNotes = async (e) => {
    e.preventDefault();
    if (!notesForm.title) {
      addToast({ type: 'warning', title: 'Внимание', message: 'Введите название' });
      return;
    }
    try {
      await api.post('materials/add-notes/', notesForm, withScheduleApiBase());
      addToast({ type: 'success', title: 'Готово', message: 'Конспект добавлен' });
      setShowAddNotesModal(false);
      setNotesForm({ title: '', content: '', description: '', lesson_id: '', visibility: 'all_teacher_groups' });
      loadMaterials();
    } catch (err) {
      addToast({ type: 'error', title: 'Ошибка', message: err.response?.data?.error || 'Не удалось добавить' });
    }
  };

  const handleAddDocument = async (e) => {
    e.preventDefault();
    if (!docForm.title || !docForm.file_url) {
      addToast({ type: 'warning', title: 'Внимание', message: 'Заполните название и ссылку' });
      return;
    }
    try {
      await api.post('materials/add-document/', docForm, withScheduleApiBase());
      addToast({ type: 'success', title: 'Готово', message: 'Документ добавлен' });
      setShowAddDocModal(false);
      setDocForm({ title: '', file_url: '', description: '', lesson_id: '', material_type: 'document', visibility: 'all_teacher_groups' });
      loadMaterials();
    } catch (err) {
      addToast({ type: 'error', title: 'Ошибка', message: err.response?.data?.error || 'Не удалось добавить' });
    }
  };

  const handleDeleteMaterial = async (materialId) => {
    setConfirmModal({
      isOpen: true,
      title: 'Удаление',
      message: 'Удалить этот материал?',
      variant: 'danger',
      confirmText: 'Удалить',
      onConfirm: async () => {
        try {
          await api.delete(`lesson-materials/${materialId}/`, withScheduleApiBase());
          addToast({ type: 'success', title: 'Готово', message: 'Материал удален' });
          loadMaterials();
        } catch (err) {
          addToast({ type: 'error', title: 'Ошибка', message: 'Не удалось удалить' });
        }
        setConfirmModal({ isOpen: false });
      }
    });
  };

  const formatDate = (dateStr) => {
    if (!dateStr) return '';
    return new Date(dateStr).toLocaleDateString('ru-RU', {
      day: '2-digit',
      month: '2-digit',
      year: 'numeric'
    });
  };

  const lessonOptions = [
    { value: '', label: 'Без привязки к уроку' },
    ...lessons.map(l => ({
      value: String(l.id),
      label: `${l.title || l.subject || 'Урок'} — ${l.group_name} (${formatDate(l.start_time)})`
    }))
  ];

  const visibilityOptions = [
    { value: 'all_teacher_groups', label: 'Все мои группы' },
    { value: 'lesson_group', label: 'Только группа урока' },
    { value: 'custom_groups', label: 'Выбранные группы' }
  ];

  const filterBySearch = (items, field = 'title') => {
    if (!searchTerm) return items;
    const term = searchTerm.toLowerCase();
    return items.filter(item => 
      (item[field] || '').toLowerCase().includes(term) ||
      (item.description || '').toLowerCase().includes(term)
    );
  };

  const tabs = [
    { id: 'miro', label: 'Miro', count: materials.miro?.length || 0 },
    { id: 'notes', label: 'Конспекты', count: materials.notes?.length || 0 },
    { id: 'documents', label: 'Документы', count: (materials.document?.length || 0) + (materials.link?.length || 0) }
  ];

  if (loading) {
    return (
      <div className="materials-page">
        <div className="materials-loading">
          <div className="spinner"></div>
          <p>Загрузка...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="materials-page">
      <ToastContainer toasts={toasts} removeToast={removeToast} />
      
      {/* Header */}
      <header className="materials-header">
        <div className="header-left">
          <h1>Материалы</h1>
          <p className="subtitle">Доски Miro, конспекты и документы</p>
        </div>
        
        <div className="header-actions">
          <button className="btn btn-secondary" onClick={() => setShowAddMiroModal(true)}>
            Добавить Miro
          </button>
          <button className="btn btn-secondary" onClick={() => setShowAddNotesModal(true)}>
            Добавить конспект
          </button>
          <button className="btn btn-secondary" onClick={() => setShowAddDocModal(true)}>
            Добавить документ
          </button>
        </div>
      </header>

      {/* Filters */}
      <div className="materials-filters">
        <div className="search-input">
          <svg className="search-icon" viewBox="0 0 20 20" fill="currentColor">
            <path fillRule="evenodd" d="M8 4a4 4 0 100 8 4 4 0 000-8zM2 8a6 6 0 1110.89 3.476l4.817 4.817a1 1 0 01-1.414 1.414l-4.816-4.816A6 6 0 012 8z" clipRule="evenodd" />
          </svg>
          <input
            type="text"
            placeholder="Поиск..."
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
            {tab.count > 0 && <span className="tab-count">{tab.count}</span>}
          </button>
        ))}
      </div>

      {/* Content */}
      <div className="materials-content">

        {/* Miro Tab */}
        {activeTab === 'miro' && (
          <div className="miro-content">
            {/* Connection Status */}
            <div className="miro-status-bar">
              {miroStatus?.user_connected ? (
                <>
                  <span className="status-badge connected">Miro подключен</span>
                  <button className="link-btn" onClick={handleDisconnectMiro}>Отключить</button>
                </>
              ) : miroStatus?.oauth_configured ? (
                <>
                  <span className="status-text">Подключите Miro для доступа к доскам</span>
                  <button className="btn btn-primary btn-sm" onClick={handleConnectMiro}>
                    Подключить Miro
                  </button>
                </>
              ) : (
                <span className="status-text">Добавляйте доски по ссылке</span>
              )}
            </div>

            {/* User's Miro Boards */}
            {miroStatus?.user_connected && miroBoards.length > 0 && (
              <div className="miro-section">
                <div className="section-header">
                  <h3>Мои доски в Miro</h3>
                  <button className="link-btn" onClick={loadMiroBoards}>Обновить</button>
                </div>
                <div className="boards-list">
                  {miroBoards.map(board => (
                    <div key={board.id} className="board-item">
                      <div className="board-thumb">
                        {board.picture ? (
                          <img src={board.picture} alt="" />
                        ) : (
                          <div className="thumb-placeholder" />
                        )}
                      </div>
                      <div className="board-info">
                        <h4>{board.name}</h4>
                        <span className="board-date">
                          {new Date(board.modified_at).toLocaleDateString('ru-RU')}
                        </span>
                      </div>
                      <div className="board-actions">
                        <a href={board.view_link} target="_blank" rel="noopener noreferrer" className="link-btn">
                          Открыть
                        </a>
                        <button className="btn btn-sm btn-primary" onClick={() => handleImportMiroBoard(board)}>
                          Добавить
                        </button>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Added Boards */}
            <div className="miro-section">
              <div className="section-header">
                <h3>Добавленные доски</h3>
                <button className="btn btn-sm btn-secondary" onClick={() => setShowAddMiroModal(true)}>
                  Добавить по ссылке
                </button>
              </div>
              
              <div className="materials-grid">
                {filterBySearch(materials.miro || []).length === 0 ? (
                  <div className="empty-state small">
                    <p>Нет добавленных досок</p>
                  </div>
                ) : (
                  filterBySearch(materials.miro || []).map(board => (
                    <div key={board.id} className="material-card">
                      <div className="card-preview miro">
                        {board.miro_embed_url ? (
                          <iframe
                            src={board.miro_embed_url}
                            frameBorder="0"
                            scrolling="no"
                            allow="fullscreen; clipboard-read; clipboard-write"
                            title={board.title}
                          />
                        ) : (
                          <div className="preview-placeholder" />
                        )}
                      </div>
                      <div className="card-body">
                        <h4>{board.title}</h4>
                        {board.description && <p className="card-desc">{board.description}</p>}
                        <div className="card-meta">
                          {board.lesson_info && <span>{board.lesson_info.title}</span>}
                          <span>{board.views_count || 0} просмотров</span>
                        </div>
                      </div>
                      <div className="card-actions">
                        <a href={board.miro_board_url} target="_blank" rel="noopener noreferrer" className="btn btn-sm btn-secondary">
                          Открыть
                        </a>
                        <button className="btn btn-sm btn-danger" onClick={() => handleDeleteMaterial(board.id)}>
                          Удалить
                        </button>
                      </div>
                    </div>
                  ))
                )}
              </div>
            </div>
          </div>
        )}

        {/* Notes Tab */}
        {activeTab === 'notes' && (
          <div className="materials-grid">
            {filterBySearch(materials.notes || []).length === 0 ? (
              <div className="empty-state">
                <h3>Нет конспектов</h3>
                <p>Создайте конспект урока для учеников</p>
                <button className="btn btn-primary" onClick={() => setShowAddNotesModal(true)}>
                  Создать конспект
                </button>
              </div>
            ) : (
              filterBySearch(materials.notes || []).map(note => (
                <div key={note.id} className="material-card">
                  <div className="card-body">
                    <h4>{note.title}</h4>
                    {note.description && <p className="card-desc">{note.description}</p>}
                    {note.content && (
                      <div className="note-preview">
                        {note.content.substring(0, 150)}...
                      </div>
                    )}
                    <div className="card-meta">
                      {note.lesson_info && <span>{note.lesson_info.title}</span>}
                      <span>{note.views_count || 0} просмотров</span>
                      <span>{formatDate(note.created_at)}</span>
                    </div>
                  </div>
                  <div className="card-actions">
                    <button className="btn btn-sm btn-secondary">Редактировать</button>
                    <button className="btn btn-sm btn-danger" onClick={() => handleDeleteMaterial(note.id)}>
                      Удалить
                    </button>
                  </div>
                </div>
              ))
            )}
          </div>
        )}

        {/* Documents Tab */}
        {activeTab === 'documents' && (
          <div className="materials-grid">
            {filterBySearch([...(materials.document || []), ...(materials.link || [])]).length === 0 ? (
              <div className="empty-state">
                <h3>Нет документов</h3>
                <p>Добавьте ссылки на документы или презентации</p>
                <button className="btn btn-primary" onClick={() => setShowAddDocModal(true)}>
                  Добавить документ
                </button>
              </div>
            ) : (
              filterBySearch([...(materials.document || []), ...(materials.link || [])]).map(doc => (
                <div key={doc.id} className="material-card">
                  <div className="card-body">
                    <div className="card-type">{doc.material_type === 'link' ? 'Ссылка' : 'Документ'}</div>
                    <h4>{doc.title}</h4>
                    {doc.description && <p className="card-desc">{doc.description}</p>}
                    <div className="card-meta">
                      {doc.file_size_mb && <span>{doc.file_size_mb} MB</span>}
                      {doc.lesson_info && <span>{doc.lesson_info.title}</span>}
                      <span>{doc.views_count || 0} просмотров</span>
                    </div>
                  </div>
                  <div className="card-actions">
                    <a href={doc.file_url} target="_blank" rel="noopener noreferrer" className="btn btn-sm btn-secondary">
                      Открыть
                    </a>
                    <button className="btn btn-sm btn-danger" onClick={() => handleDeleteMaterial(doc.id)}>
                      Удалить
                    </button>
                  </div>
                </div>
              ))
            )}
          </div>
        )}
      </div>

      {/* Add Miro Modal */}
      {showAddMiroModal && (
        <Modal isOpen={true} onClose={() => setShowAddMiroModal(false)} title="Добавить доску Miro">
          <form onSubmit={handleAddMiroBoard} className="modal-form">
            <div className="form-group">
              <label>Ссылка на доску *</label>
              <input
                type="url"
                value={miroForm.board_url}
                onChange={(e) => setMiroForm({...miroForm, board_url: e.target.value})}
                placeholder="https://miro.com/app/board/..."
                required
              />
              <small>Скопируйте ссылку из адресной строки Miro</small>
            </div>
            
            <div className="form-group">
              <label>Название</label>
              <input
                type="text"
                value={miroForm.title}
                onChange={(e) => setMiroForm({...miroForm, title: e.target.value})}
                placeholder="Название доски"
              />
            </div>
            
            <div className="form-group">
              <label>Описание</label>
              <textarea
                value={miroForm.description}
                onChange={(e) => setMiroForm({...miroForm, description: e.target.value})}
                placeholder="Краткое описание"
                rows={2}
              />
            </div>
            
            <div className="form-group">
              <label>Привязать к уроку</label>
              <Select
                value={miroForm.lesson_id}
                onChange={(e) => setMiroForm({...miroForm, lesson_id: e.target.value})}
                options={lessonOptions}
              />
            </div>
            
            <div className="form-group">
              <label>Видимость</label>
              <Select
                value={miroForm.visibility}
                onChange={(e) => setMiroForm({...miroForm, visibility: e.target.value})}
                options={visibilityOptions}
              />
            </div>
            
            <div className="modal-footer">
              <button type="button" onClick={() => setShowAddMiroModal(false)} className="btn btn-secondary">
                Отмена
              </button>
              <button type="submit" className="btn btn-primary">
                Добавить
              </button>
            </div>
          </form>
        </Modal>
      )}

      {/* Add Notes Modal */}
      {showAddNotesModal && (
        <Modal isOpen={true} onClose={() => setShowAddNotesModal(false)} title="Создать конспект" size="large">
          <form onSubmit={handleAddNotes} className="modal-form">
            <div className="form-group">
              <label>Название *</label>
              <input
                type="text"
                value={notesForm.title}
                onChange={(e) => setNotesForm({...notesForm, title: e.target.value})}
                placeholder="Название конспекта"
                required
              />
            </div>
            
            <div className="form-group">
              <label>Краткое описание</label>
              <input
                type="text"
                value={notesForm.description}
                onChange={(e) => setNotesForm({...notesForm, description: e.target.value})}
                placeholder="О чем этот конспект"
              />
            </div>
            
            <div className="form-group">
              <label>Содержание</label>
              <textarea
                value={notesForm.content}
                onChange={(e) => setNotesForm({...notesForm, content: e.target.value})}
                placeholder="Текст конспекта (поддерживается Markdown)"
                rows={10}
              />
            </div>
            
            <div className="form-row">
              <div className="form-group">
                <label>Привязать к уроку</label>
                <Select
                  value={notesForm.lesson_id}
                  onChange={(e) => setNotesForm({...notesForm, lesson_id: e.target.value})}
                  options={lessonOptions}
                />
              </div>
              <div className="form-group">
                <label>Видимость</label>
                <Select
                  value={notesForm.visibility}
                  onChange={(e) => setNotesForm({...notesForm, visibility: e.target.value})}
                  options={visibilityOptions}
                />
              </div>
            </div>
            
            <div className="modal-footer">
              <button type="button" onClick={() => setShowAddNotesModal(false)} className="btn btn-secondary">
                Отмена
              </button>
              <button type="submit" className="btn btn-primary">
                Сохранить
              </button>
            </div>
          </form>
        </Modal>
      )}

      {/* Add Document Modal */}
      {showAddDocModal && (
        <Modal isOpen={true} onClose={() => setShowAddDocModal(false)} title="Добавить документ">
          <form onSubmit={handleAddDocument} className="modal-form">
            <div className="form-group">
              <label>Название *</label>
              <input
                type="text"
                value={docForm.title}
                onChange={(e) => setDocForm({...docForm, title: e.target.value})}
                placeholder="Название документа"
                required
              />
            </div>
            
            <div className="form-group">
              <label>Ссылка *</label>
              <input
                type="url"
                value={docForm.file_url}
                onChange={(e) => setDocForm({...docForm, file_url: e.target.value})}
                placeholder="https://..."
                required
              />
              <small>Google Drive, Dropbox или любая другая ссылка</small>
            </div>
            
            <div className="form-group">
              <label>Описание</label>
              <textarea
                value={docForm.description}
                onChange={(e) => setDocForm({...docForm, description: e.target.value})}
                placeholder="Краткое описание"
                rows={2}
              />
            </div>
            
            <div className="form-group">
              <label>Тип</label>
              <Select
                value={docForm.material_type}
                onChange={(e) => setDocForm({...docForm, material_type: e.target.value})}
                options={[
                  { value: 'document', label: 'Документ' },
                  { value: 'link', label: 'Ссылка' },
                  { value: 'image', label: 'Изображение' }
                ]}
              />
            </div>
            
            <div className="form-row">
              <div className="form-group">
                <label>Привязать к уроку</label>
                <Select
                  value={docForm.lesson_id}
                  onChange={(e) => setDocForm({...docForm, lesson_id: e.target.value})}
                  options={lessonOptions}
                />
              </div>
              <div className="form-group">
                <label>Видимость</label>
                <Select
                  value={docForm.visibility}
                  onChange={(e) => setDocForm({...docForm, visibility: e.target.value})}
                  options={visibilityOptions}
                />
              </div>
            </div>
            
            <div className="modal-footer">
              <button type="button" onClick={() => setShowAddDocModal(false)} className="btn btn-secondary">
                Отмена
              </button>
              <button type="submit" className="btn btn-primary">
                Добавить
              </button>
            </div>
          </form>
        </Modal>
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
