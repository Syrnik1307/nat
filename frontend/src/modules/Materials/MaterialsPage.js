import React, { useState, useEffect, useCallback } from 'react';
import api, { withScheduleApiBase } from '../../apiService';
import RecordingCard from '../Recordings/RecordingCard';
import RecordingPlayer from '../Recordings/RecordingPlayer';
import './MaterialsPage.css';

/**
 * Страница материалов учителя.
 * Объединяет: Записи, Доски Miro, Конспекты, Документы.
 */
function MaterialsPage() {
  // Активный таб
  const [activeTab, setActiveTab] = useState('recordings');
  
  // Записи
  const [recordings, setRecordings] = useState([]);
  const [selectedRecording, setSelectedRecording] = useState(null);
  
  // Материалы
  const [materials, setMaterials] = useState({
    miro: [],
    notes: [],
    document: [],
    link: [],
  });
  const [stats, setStats] = useState({});
  
  // Miro OAuth статус
  const [miroStatus, setMiroStatus] = useState({
    oauth_configured: false,
    user_connected: false,
    auth_url: null,
  });
  const [miroBoards, setMiroBoards] = useState([]);
  
  // UI состояние
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [searchTerm, setSearchTerm] = useState('');
  const [showAddModal, setShowAddModal] = useState(false);
  const [addModalType, setAddModalType] = useState('miro');
  
  // Группы для фильтрации
  const [groups, setGroups] = useState([]);
  const [groupFilter, setGroupFilter] = useState('all');

  // Загрузка данных при монтировании
  useEffect(() => {
    loadAllData();
    checkMiroCallback();
  }, []);

  // Проверяем callback от Miro OAuth
  const checkMiroCallback = () => {
    const params = new URLSearchParams(window.location.search);
    if (params.get('miro_connected') === 'true') {
      // Убираем параметр из URL
      window.history.replaceState({}, '', window.location.pathname);
      // Показываем уведомление
      alert('Miro успешно подключен!');
    } else if (params.get('miro_error')) {
      const error = params.get('miro_error');
      window.history.replaceState({}, '', window.location.pathname);
      alert(`Ошибка подключения Miro: ${error}`);
    }
  };

  const loadAllData = async () => {
    setLoading(true);
    setError(null);
    
    try {
      await Promise.all([
        loadRecordings(),
        loadMaterials(),
        loadMiroStatus(),
        loadGroups(),
      ]);
    } catch (err) {
      console.error('Failed to load data:', err);
      setError('Не удалось загрузить данные');
    } finally {
      setLoading(false);
    }
  };

  const loadRecordings = async () => {
    try {
      const response = await api.get('recordings/teacher/', withScheduleApiBase());
      const data = response?.data;
      const arr = Array.isArray(data?.results) ? data.results : (Array.isArray(data) ? data : []);
      setRecordings(arr);
    } catch (err) {
      console.error('Failed to load recordings:', err);
    }
  };

  const loadMaterials = async () => {
    try {
      const response = await api.get('api/lesson-materials/teacher_materials/', withScheduleApiBase());
      const data = response?.data;
      if (data?.materials) {
        setMaterials(data.materials);
      }
      if (data?.stats) {
        setStats(data.stats);
      }
    } catch (err) {
      console.error('Failed to load materials:', err);
    }
  };

  const loadMiroStatus = async () => {
    try {
      const response = await api.get('api/miro/oauth/status/', withScheduleApiBase());
      setMiroStatus(response.data);
      
      // Если подключен - загружаем доски
      if (response.data?.user_connected) {
        loadMiroBoards();
      }
    } catch (err) {
      console.error('Failed to load miro status:', err);
    }
  };

  const loadMiroBoards = async () => {
    try {
      const response = await api.get('api/miro/oauth/boards/', withScheduleApiBase());
      setMiroBoards(response.data?.boards || []);
    } catch (err) {
      console.error('Failed to load miro boards:', err);
    }
  };

  const loadGroups = async () => {
    try {
      const response = await api.get('groups/');
      const data = response?.data;
      const arr = Array.isArray(data?.results) ? data.results : (Array.isArray(data) ? data : []);
      setGroups(arr);
    } catch (err) {
      console.error('Failed to load groups:', err);
    }
  };

  // Подключение Miro
  const connectMiro = () => {
    if (miroStatus.auth_url) {
      window.location.href = miroStatus.auth_url;
    } else {
      // Получаем URL для авторизации
      api.get('api/miro/oauth/start/', withScheduleApiBase())
        .then(res => {
          if (res.data?.auth_url) {
            window.location.href = res.data.auth_url;
          }
        })
        .catch(err => {
          console.error('Failed to get auth URL:', err);
          alert('Не удалось получить ссылку для авторизации Miro');
        });
    }
  };

  const disconnectMiro = async () => {
    if (!window.confirm('Отключить интеграцию с Miro?')) return;
    
    try {
      await api.post('api/miro/oauth/disconnect/', {}, withScheduleApiBase());
      setMiroStatus(prev => ({ ...prev, user_connected: false }));
      setMiroBoards([]);
    } catch (err) {
      console.error('Failed to disconnect Miro:', err);
    }
  };

  // Открыть модальное окно добавления
  const openAddModal = (type) => {
    setAddModalType(type);
    setShowAddModal(true);
  };

  // Получить количество для таба
  const getTabCount = (tab) => {
    switch (tab) {
      case 'recordings': return recordings.length;
      case 'miro': return materials.miro?.length || 0;
      case 'notes': return materials.notes?.length || 0;
      case 'documents': return (materials.document?.length || 0) + (materials.link?.length || 0);
      default: return 0;
    }
  };

  // Фильтрация по поиску
  const filterItems = (items) => {
    if (!searchTerm.trim()) return items;
    const search = searchTerm.toLowerCase();
    return items.filter(item => 
      item.title?.toLowerCase().includes(search) ||
      item.description?.toLowerCase().includes(search) ||
      item.lesson_info?.title?.toLowerCase().includes(search)
    );
  };

  const openRecordingPlayer = (recording) => {
    setSelectedRecording(recording);
    api.post(`recordings/${recording.id}/view/`, {}, withScheduleApiBase()).catch(() => {});
  };

  const closePlayer = () => {
    setSelectedRecording(null);
  };

  const deleteRecording = async (recording) => {
    if (!window.confirm(`Удалить запись "${recording.lesson_info?.title || 'Без названия'}"?`)) return;
    
    try {
      await api.delete(`recordings/${recording.id}/delete/`, withScheduleApiBase());
      setRecordings(prev => prev.filter(r => r.id !== recording.id));
    } catch (err) {
      console.error('Failed to delete recording:', err);
      alert('Не удалось удалить запись');
    }
  };

  const deleteMaterial = async (material) => {
    if (!window.confirm(`Удалить "${material.title}"?`)) return;
    
    try {
      await api.delete(`api/lesson-materials/${material.id}/`, withScheduleApiBase());
      // Обновляем список
      setMaterials(prev => ({
        ...prev,
        [material.material_type]: prev[material.material_type]?.filter(m => m.id !== material.id) || []
      }));
    } catch (err) {
      console.error('Failed to delete material:', err);
      alert('Не удалось удалить материал');
    }
  };

  if (loading) {
    return (
      <div className="materials-page">
        <div className="loading-container">
          <div className="spinner"></div>
          <p>Загрузка материалов...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="materials-page">
      {/* Заголовок */}
      <div className="materials-header">
        <div className="header-content">
          <h1>📚 Материалы</h1>
          <p className="subtitle">Записи, доски Miro, конспекты и документы</p>
        </div>
        
        <div className="header-actions">
          <button className="btn btn-primary" onClick={() => openAddModal(activeTab === 'recordings' ? 'miro' : activeTab)}>
            <span className="btn-icon">+</span>
            Добавить
          </button>
        </div>
      </div>

      {error && (
        <div className="error-banner">
          <span>⚠️</span> {error}
          <button onClick={loadAllData}>Повторить</button>
        </div>
      )}

      {/* Табы */}
      <div className="materials-tabs">
        <button 
          className={`tab ${activeTab === 'recordings' ? 'active' : ''}`}
          onClick={() => setActiveTab('recordings')}
        >
          <span className="tab-icon">🎥</span>
          Записи
          <span className="tab-count">{getTabCount('recordings')}</span>
        </button>
        
        <button 
          className={`tab ${activeTab === 'miro' ? 'active' : ''}`}
          onClick={() => setActiveTab('miro')}
        >
          <span className="tab-icon">🎨</span>
          Miro
          <span className="tab-count">{getTabCount('miro')}</span>
        </button>
        
        <button 
          className={`tab ${activeTab === 'notes' ? 'active' : ''}`}
          onClick={() => setActiveTab('notes')}
        >
          <span className="tab-icon">📝</span>
          Конспекты
          <span className="tab-count">{getTabCount('notes')}</span>
        </button>
        
        <button 
          className={`tab ${activeTab === 'documents' ? 'active' : ''}`}
          onClick={() => setActiveTab('documents')}
        >
          <span className="tab-icon">📄</span>
          Документы
          <span className="tab-count">{getTabCount('documents')}</span>
        </button>
      </div>

      {/* Фильтры и поиск */}
      <div className="materials-filters">
        <div className="search-box">
          <input
            type="text"
            placeholder="Поиск по названию..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            className="search-input"
          />
        </div>
        
        <div className="filter-group">
          <label>Группа:</label>
          <select
            value={groupFilter}
            onChange={(e) => setGroupFilter(e.target.value)}
            className="filter-select"
          >
            <option value="all">Все группы</option>
            {groups.map(g => (
              <option key={g.id} value={g.id}>{g.name}</option>
            ))}
          </select>
        </div>
      </div>

      {/* Контент табов */}
      <div className="tab-content">
        {/* Записи */}
        {activeTab === 'recordings' && (
          <RecordingsTab
            recordings={filterItems(recordings)}
            onPlay={openRecordingPlayer}
            onDelete={deleteRecording}
          />
        )}
        
        {/* Miro */}
        {activeTab === 'miro' && (
          <MiroTab
            materials={filterItems(materials.miro || [])}
            miroStatus={miroStatus}
            miroBoards={miroBoards}
            onConnect={connectMiro}
            onDisconnect={disconnectMiro}
            onDelete={deleteMaterial}
            onAdd={() => openAddModal('miro')}
            onRefresh={loadAllData}
          />
        )}
        
        {/* Конспекты */}
        {activeTab === 'notes' && (
          <NotesTab
            materials={filterItems(materials.notes || [])}
            onDelete={deleteMaterial}
            onAdd={() => openAddModal('notes')}
          />
        )}
        
        {/* Документы */}
        {activeTab === 'documents' && (
          <DocumentsTab
            documents={filterItems([...(materials.document || []), ...(materials.link || [])])}
            onDelete={deleteMaterial}
            onAdd={() => openAddModal('document')}
          />
        )}
      </div>

      {/* Модальное окно добавления */}
      {showAddModal && (
        <AddMaterialModal
          type={addModalType}
          groups={groups}
          miroStatus={miroStatus}
          miroBoards={miroBoards}
          onClose={() => setShowAddModal(false)}
          onSuccess={() => {
            setShowAddModal(false);
            loadAllData();
          }}
        />
      )}

      {/* Плеер записи */}
      {selectedRecording && (
        <RecordingPlayer
          recording={selectedRecording}
          onClose={closePlayer}
        />
      )}
    </div>
  );
}


// === Таб с записями ===
function RecordingsTab({ recordings, onPlay, onDelete }) {
  if (recordings.length === 0) {
    return (
      <div className="empty-state">
        <div className="empty-icon">🎥</div>
        <h3>Нет записей</h3>
        <p>Записи уроков появятся здесь после проведения занятий</p>
      </div>
    );
  }

  return (
    <div className="recordings-grid">
      {recordings.map(rec => (
        <RecordingCard
          key={rec.id}
          recording={rec}
          onPlay={() => onPlay(rec)}
          onDelete={() => onDelete(rec)}
        />
      ))}
    </div>
  );
}


// === Таб с Miro ===
function MiroTab({ materials, miroStatus, miroBoards, onConnect, onDisconnect, onDelete, onAdd, onRefresh }) {
  const [selectedBoard, setSelectedBoard] = useState(null);

  return (
    <div className="miro-tab">
      {/* Статус подключения */}
      <div className="miro-connection-status">
        {miroStatus.user_connected ? (
          <div className="connected">
            <span className="status-icon">✅</span>
            <span>Miro подключен</span>
            <button className="btn btn-link" onClick={onDisconnect}>Отключить</button>
          </div>
        ) : miroStatus.oauth_configured ? (
          <div className="not-connected">
            <span className="status-icon">🔗</span>
            <span>Подключите Miro для доступа к своим доскам</span>
            <button className="btn btn-primary" onClick={onConnect}>Подключить Miro</button>
          </div>
        ) : (
          <div className="info-message">
            <span className="status-icon">ℹ️</span>
            <span>Вы можете добавлять доски Miro по ссылке</span>
          </div>
        )}
      </div>

      {/* Мои доски из Miro (если подключен) */}
      {miroStatus.user_connected && miroBoards.length > 0 && (
        <div className="miro-boards-section">
          <h3>Мои доски в Miro <button className="btn-refresh" onClick={onRefresh}>🔄</button></h3>
          <div className="miro-boards-list">
            {miroBoards.map(board => (
              <div key={board.id} className="miro-board-item">
                <div className="board-preview">
                  {board.picture ? (
                    <img src={board.picture} alt={board.name} />
                  ) : (
                    <div className="placeholder">🎨</div>
                  )}
                </div>
                <div className="board-info">
                  <h4>{board.name}</h4>
                  <p className="board-meta">
                    Изменено: {new Date(board.modified_at).toLocaleDateString('ru-RU')}
                  </p>
                </div>
                <div className="board-actions">
                  <a href={board.view_link} target="_blank" rel="noopener noreferrer" className="btn btn-sm">
                    Открыть
                  </a>
                  <button 
                    className="btn btn-sm btn-primary"
                    onClick={() => setSelectedBoard(board)}
                  >
                    Добавить
                  </button>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Добавленные доски */}
      <div className="added-materials-section">
        <div className="section-header">
          <h3>Добавленные доски</h3>
          <button className="btn btn-primary btn-sm" onClick={onAdd}>
            + Добавить доску
          </button>
        </div>
        
        {materials.length === 0 ? (
          <div className="empty-state small">
            <div className="empty-icon">🎨</div>
            <p>Нет добавленных досок Miro</p>
          </div>
        ) : (
          <div className="materials-grid">
            {materials.map(material => (
              <MiroBoardCard
                key={material.id}
                material={material}
                onDelete={() => onDelete(material)}
              />
            ))}
          </div>
        )}
      </div>

      {/* Модальное окно импорта доски */}
      {selectedBoard && (
        <ImportMiroBoardModal
          board={selectedBoard}
          onClose={() => setSelectedBoard(null)}
          onSuccess={() => {
            setSelectedBoard(null);
            onRefresh();
          }}
        />
      )}
    </div>
  );
}


// === Карточка доски Miro ===
function MiroBoardCard({ material, onDelete }) {
  const [showEmbed, setShowEmbed] = useState(false);

  return (
    <div className="material-card miro-card">
      <div className="card-preview" onClick={() => setShowEmbed(true)}>
        {material.miro_thumbnail_url ? (
          <img src={material.miro_thumbnail_url} alt={material.title} />
        ) : (
          <div className="placeholder">
            <span className="icon">🎨</span>
          </div>
        )}
        <div className="overlay">
          <span>Открыть</span>
        </div>
      </div>
      
      <div className="card-content">
        <h4>{material.title}</h4>
        {material.description && <p className="description">{material.description}</p>}
        {material.lesson_info && (
          <p className="lesson-link">📅 {material.lesson_info.title}</p>
        )}
        <p className="meta">
          Добавлено: {new Date(material.uploaded_at).toLocaleDateString('ru-RU')}
        </p>
      </div>
      
      <div className="card-actions">
        <a 
          href={material.miro_board_url} 
          target="_blank" 
          rel="noopener noreferrer"
          className="btn btn-sm"
        >
          Открыть в Miro
        </a>
        <button className="btn btn-sm btn-danger" onClick={onDelete}>
          Удалить
        </button>
      </div>

      {/* Модальное окно с embed */}
      {showEmbed && (
        <div className="modal-overlay" onClick={() => setShowEmbed(false)}>
          <div className="modal-content embed-modal" onClick={e => e.stopPropagation()}>
            <div className="modal-header">
              <h3>{material.title}</h3>
              <button className="close-btn" onClick={() => setShowEmbed(false)}>×</button>
            </div>
            <div className="embed-container">
              <iframe
                src={material.miro_embed_url}
                frameBorder="0"
                scrolling="no"
                allowFullScreen
                title={material.title}
              />
            </div>
          </div>
        </div>
      )}
    </div>
  );
}


// === Таб с конспектами ===
function NotesTab({ materials, onDelete, onAdd }) {
  const [viewingNote, setViewingNote] = useState(null);

  return (
    <div className="notes-tab">
      <div className="section-header">
        <h3>Конспекты</h3>
        <button className="btn btn-primary btn-sm" onClick={onAdd}>
          + Добавить конспект
        </button>
      </div>

      {materials.length === 0 ? (
        <div className="empty-state">
          <div className="empty-icon">📝</div>
          <h3>Нет конспектов</h3>
          <p>Добавьте конспекты для ваших уроков</p>
          <button className="btn btn-primary" onClick={onAdd}>Создать конспект</button>
        </div>
      ) : (
        <div className="notes-list">
          {materials.map(note => (
            <div key={note.id} className="note-card" onClick={() => setViewingNote(note)}>
              <div className="note-icon">📝</div>
              <div className="note-content">
                <h4>{note.title}</h4>
                {note.description && <p className="description">{note.description}</p>}
                {note.lesson_info && (
                  <p className="lesson-link">📅 {note.lesson_info.title}</p>
                )}
                <p className="meta">
                  {new Date(note.uploaded_at).toLocaleDateString('ru-RU')}
                </p>
              </div>
              <div className="note-actions" onClick={e => e.stopPropagation()}>
                <button className="btn btn-sm btn-danger" onClick={() => onDelete(note)}>
                  Удалить
                </button>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Просмотр конспекта */}
      {viewingNote && (
        <NoteViewerModal
          note={viewingNote}
          onClose={() => setViewingNote(null)}
        />
      )}
    </div>
  );
}


// === Модальное окно просмотра конспекта ===
function NoteViewerModal({ note, onClose }) {
  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-content note-viewer" onClick={e => e.stopPropagation()}>
        <div className="modal-header">
          <h3>{note.title}</h3>
          <button className="close-btn" onClick={onClose}>×</button>
        </div>
        <div className="note-body">
          {note.content ? (
            <div 
              className="note-content-rendered"
              dangerouslySetInnerHTML={{ __html: note.content }}
            />
          ) : (
            <p className="empty-content">Содержимое отсутствует</p>
          )}
        </div>
        {note.lesson_info && (
          <div className="note-footer">
            <span>📅 Урок: {note.lesson_info.title}</span>
          </div>
        )}
      </div>
    </div>
  );
}


// === Таб с документами ===
function DocumentsTab({ documents, onDelete, onAdd }) {
  const getFileIcon = (type, url) => {
    if (type === 'link') return '🔗';
    if (url?.includes('.pdf')) return '📕';
    if (url?.includes('.doc')) return '📘';
    if (url?.includes('.xls')) return '📗';
    if (url?.includes('.ppt')) return '📙';
    return '📄';
  };

  return (
    <div className="documents-tab">
      <div className="section-header">
        <h3>Документы и ссылки</h3>
        <button className="btn btn-primary btn-sm" onClick={onAdd}>
          + Добавить
        </button>
      </div>

      {documents.length === 0 ? (
        <div className="empty-state">
          <div className="empty-icon">📄</div>
          <h3>Нет документов</h3>
          <p>Добавьте документы и ссылки для ваших уроков</p>
          <button className="btn btn-primary" onClick={onAdd}>Добавить документ</button>
        </div>
      ) : (
        <div className="documents-list">
          {documents.map(doc => (
            <div key={doc.id} className="document-card">
              <div className="doc-icon">{getFileIcon(doc.material_type, doc.file_url)}</div>
              <div className="doc-content">
                <h4>{doc.title}</h4>
                {doc.description && <p className="description">{doc.description}</p>}
                {doc.file_size_mb && (
                  <span className="file-size">{doc.file_size_mb} MB</span>
                )}
                {doc.lesson_info && (
                  <p className="lesson-link">📅 {doc.lesson_info.title}</p>
                )}
              </div>
              <div className="doc-actions">
                <a 
                  href={doc.file_url} 
                  target="_blank" 
                  rel="noopener noreferrer"
                  className="btn btn-sm"
                >
                  Открыть
                </a>
                <button className="btn btn-sm btn-danger" onClick={() => onDelete(doc)}>
                  Удалить
                </button>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}


// === Модальное окно добавления материала ===
function AddMaterialModal({ type, groups, miroStatus, miroBoards, onClose, onSuccess }) {
  const [activeType, setActiveType] = useState(type);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  
  // Общие поля
  const [title, setTitle] = useState('');
  const [description, setDescription] = useState('');
  const [lessonId, setLessonId] = useState('');
  const [visibility, setVisibility] = useState('all_teacher_groups');
  
  // Miro
  const [boardUrl, setBoardUrl] = useState('');
  const [selectedBoardId, setSelectedBoardId] = useState('');
  
  // Конспект
  const [content, setContent] = useState('');
  
  // Документ
  const [fileUrl, setFileUrl] = useState('');

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError(null);

    try {
      let endpoint = '';
      let payload = {};

      switch (activeType) {
        case 'miro':
          if (selectedBoardId) {
            // Импорт из списка досок
            endpoint = 'api/miro/oauth/import-board/';
            payload = {
              board_id: selectedBoardId,
              title,
              description,
              lesson_id: lessonId || null,
              visibility,
            };
          } else if (boardUrl) {
            // Добавление по URL
            endpoint = 'api/miro/add-board/';
            payload = {
              board_url: boardUrl,
              title,
              description,
              lesson_id: lessonId || null,
              visibility,
            };
          } else {
            setError('Укажите URL доски или выберите из списка');
            setLoading(false);
            return;
          }
          break;

        case 'notes':
          if (!title.trim()) {
            setError('Укажите название конспекта');
            setLoading(false);
            return;
          }
          endpoint = 'api/materials/add-notes/';
          payload = {
            title,
            description,
            content,
            lesson_id: lessonId || null,
            visibility,
          };
          break;

        case 'document':
        case 'link':
          if (!title.trim() || !fileUrl.trim()) {
            setError('Укажите название и ссылку');
            setLoading(false);
            return;
          }
          endpoint = 'api/materials/add-document/';
          payload = {
            title,
            description,
            file_url: fileUrl,
            material_type: activeType,
            lesson_id: lessonId || null,
            visibility,
          };
          break;

        default:
          setError('Неизвестный тип материала');
          setLoading(false);
          return;
      }

      await api.post(endpoint, payload, withScheduleApiBase());
      onSuccess();
    } catch (err) {
      console.error('Failed to add material:', err);
      setError(err.response?.data?.error || 'Не удалось добавить материал');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-content add-material-modal" onClick={e => e.stopPropagation()}>
        <div className="modal-header">
          <h3>Добавить материал</h3>
          <button className="close-btn" onClick={onClose}>×</button>
        </div>

        {/* Выбор типа */}
        <div className="type-tabs">
          <button 
            className={activeType === 'miro' ? 'active' : ''}
            onClick={() => setActiveType('miro')}
          >
            🎨 Miro
          </button>
          <button 
            className={activeType === 'notes' ? 'active' : ''}
            onClick={() => setActiveType('notes')}
          >
            📝 Конспект
          </button>
          <button 
            className={activeType === 'document' ? 'active' : ''}
            onClick={() => setActiveType('document')}
          >
            📄 Документ
          </button>
          <button 
            className={activeType === 'link' ? 'active' : ''}
            onClick={() => setActiveType('link')}
          >
            🔗 Ссылка
          </button>
        </div>

        <form onSubmit={handleSubmit}>
          {error && <div className="form-error">{error}</div>}

          {/* Miro */}
          {activeType === 'miro' && (
            <>
              {miroStatus.user_connected && miroBoards.length > 0 && (
                <div className="form-group">
                  <label>Выбрать из моих досок:</label>
                  <select 
                    value={selectedBoardId}
                    onChange={(e) => {
                      setSelectedBoardId(e.target.value);
                      if (e.target.value) {
                        const board = miroBoards.find(b => b.id === e.target.value);
                        if (board && !title) setTitle(board.name);
                      }
                    }}
                  >
                    <option value="">— Или введите URL ниже —</option>
                    {miroBoards.map(b => (
                      <option key={b.id} value={b.id}>{b.name}</option>
                    ))}
                  </select>
                </div>
              )}
              
              {!selectedBoardId && (
                <div className="form-group">
                  <label>URL доски Miro *</label>
                  <input
                    type="url"
                    value={boardUrl}
                    onChange={(e) => setBoardUrl(e.target.value)}
                    placeholder="https://miro.com/app/board/..."
                    required={!selectedBoardId}
                  />
                </div>
              )}
            </>
          )}

          {/* Конспект */}
          {activeType === 'notes' && (
            <div className="form-group">
              <label>Содержимое (Markdown/HTML)</label>
              <textarea
                value={content}
                onChange={(e) => setContent(e.target.value)}
                rows={8}
                placeholder="Введите текст конспекта..."
              />
            </div>
          )}

          {/* Документ/Ссылка */}
          {(activeType === 'document' || activeType === 'link') && (
            <div className="form-group">
              <label>URL {activeType === 'link' ? 'ссылки' : 'файла'} *</label>
              <input
                type="url"
                value={fileUrl}
                onChange={(e) => setFileUrl(e.target.value)}
                placeholder="https://..."
                required
              />
            </div>
          )}

          {/* Общие поля */}
          <div className="form-group">
            <label>Название {activeType !== 'miro' || !selectedBoardId ? '*' : ''}</label>
            <input
              type="text"
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              placeholder="Название материала"
              required={activeType !== 'miro' || !selectedBoardId}
            />
          </div>

          <div className="form-group">
            <label>Описание</label>
            <textarea
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              rows={2}
              placeholder="Краткое описание (опционально)"
            />
          </div>

          <div className="form-group">
            <label>Доступ</label>
            <select value={visibility} onChange={(e) => setVisibility(e.target.value)}>
              <option value="all_teacher_groups">Все мои группы</option>
              <option value="lesson_group">Только группа урока</option>
              <option value="custom_groups">Выбранные группы</option>
            </select>
          </div>

          <div className="form-actions">
            <button type="button" className="btn btn-secondary" onClick={onClose}>
              Отмена
            </button>
            <button type="submit" className="btn btn-primary" disabled={loading}>
              {loading ? 'Сохранение...' : 'Добавить'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}


// === Модальное окно импорта доски Miro ===
function ImportMiroBoardModal({ board, onClose, onSuccess }) {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [title, setTitle] = useState(board.name);
  const [description, setDescription] = useState(board.description || '');

  const handleImport = async () => {
    setLoading(true);
    setError(null);

    try {
      await api.post('api/miro/oauth/import-board/', {
        board_id: board.id,
        title,
        description,
        visibility: 'all_teacher_groups',
      }, withScheduleApiBase());
      
      onSuccess();
    } catch (err) {
      console.error('Failed to import board:', err);
      setError(err.response?.data?.error || 'Не удалось импортировать доску');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-content import-modal" onClick={e => e.stopPropagation()}>
        <div className="modal-header">
          <h3>Добавить доску</h3>
          <button className="close-btn" onClick={onClose}>×</button>
        </div>

        <div className="board-preview">
          {board.picture ? (
            <img src={board.picture} alt={board.name} />
          ) : (
            <div className="placeholder">🎨</div>
          )}
        </div>

        {error && <div className="form-error">{error}</div>}

        <div className="form-group">
          <label>Название</label>
          <input
            type="text"
            value={title}
            onChange={(e) => setTitle(e.target.value)}
          />
        </div>

        <div className="form-group">
          <label>Описание</label>
          <textarea
            value={description}
            onChange={(e) => setDescription(e.target.value)}
            rows={2}
          />
        </div>

        <div className="form-actions">
          <button className="btn btn-secondary" onClick={onClose}>Отмена</button>
          <button className="btn btn-primary" onClick={handleImport} disabled={loading}>
            {loading ? 'Добавление...' : 'Добавить в материалы'}
          </button>
        </div>
      </div>
    </div>
  );
}


export default MaterialsPage;
