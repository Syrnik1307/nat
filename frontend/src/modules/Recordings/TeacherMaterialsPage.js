import React, { useState, useEffect, useCallback, useMemo, lazy, Suspense } from 'react';
import './TeacherMaterialsPage.css';
import api, { withScheduleApiBase } from '../../apiService';
import { ConfirmModal, Select, SearchableSelect, ToastContainer, Modal } from '../../shared/components';
import { getCached } from '../../utils/dataCache';

// Ленивая загрузка RichTextEditor - он используется только в модалках
const RichTextEditor = lazy(() => import('../../shared/components').then(m => ({ default: m.RichTextEditor })));

/**
 * TeacherMaterialsPage - Страница материалов урока
 * Доски Miro и конспекты
 */
function TeacherMaterialsPage() {
  const [activeTab, setActiveTab] = useState('miro');
  
  // Данные
  const [materials, setMaterials] = useState({ miro: [], notes: [] });
  const [lessons, setLessons] = useState([]);
  const [groups, setGroups] = useState([]);
  const [students, setStudents] = useState([]);
  
  // UI State
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [searchTerm, setSearchTerm] = useState('');
  const [groupFilter, setGroupFilter] = useState('all');
  
  // Модальные окна
  const [showAddMiroModal, setShowAddMiroModal] = useState(false);
  const [showAddNotesModal, setShowAddNotesModal] = useState(false);
  const [previewNote, setPreviewNote] = useState(null);
  const [editingNoteId, setEditingNoteId] = useState(null);
  
  // Формы
  const [miroForm, setMiroForm] = useState({
    board_url: '',
    title: '',
    description: '',
    lesson_id: '',
    visibility: 'all_teacher_groups',
    allowed_groups: [],
    allowed_students: []
  });
  
  const [notesForm, setNotesForm] = useState({
    title: '',
    content: '',
    description: '',
    lesson_id: '',
    visibility: 'all_teacher_groups',
    allowed_groups: [],
    allowed_students: [],
    mode: 'rich',
    file_url: '',
    file_name: '',
    file_size_bytes: 0
  });

  // Toasts & Confirm
  const [toasts, setToasts] = useState([]);
  const [confirmModal, setConfirmModal] = useState({ isOpen: false });
  const [notesFileUploading, setNotesFileUploading] = useState(false);
  const [uploadProgress, setUploadProgress] = useState({ current: 0, total: 0 });
  
  // Miro status
  const [miroStatus, setMiroStatus] = useState(null);
  const [miroBoards, setMiroBoards] = useState([]);
  
  // Поиск в списках групп/учеников
  const [groupSearchQuery, setGroupSearchQuery] = useState('');
  const [studentSearchQuery, setStudentSearchQuery] = useState('');

  const removeToast = useCallback((id) => {
    setToasts(prev => prev.filter(t => t.id !== id));
  }, []);

  const addToast = useCallback((toast) => {
    const id = Date.now() + Math.random();
    setToasts(prev => [...prev, { id, ...toast }]);
    setTimeout(() => removeToast(id), 5000);
    return id;
  }, [removeToast]);

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
    setError(null);
    try {
      const results = await Promise.allSettled([
        loadMaterials(),
        loadLessons(),
        loadGroups()
        // loadStudents() - отложена до клика на модаль (оптимизация рендера)
      ]);
      
      // Проверяем, есть ли критические ошибки
      const failures = results.filter(r => r.status === 'rejected');
      if (failures.length > 0) {
        console.error('Some data failed to load:', failures);
        addToast({ type: 'warning', title: 'Внимание', message: 'Часть данных не удалось загрузить' });
      }
    } catch (err) {
      console.error('Error loading data:', err);
      setError('Не удалось загрузить данные. Проверьте подключение к интернету.');
      addToast({ type: 'error', title: 'Ошибка', message: 'Не удалось загрузить данные' });
    } finally {
      setLoading(false);
    }
  };

  const loadMaterials = async () => {
    const cachedMaterials = await getCached('teacher:materials', async () => {
      const response = await api.get('lesson-materials/teacher_materials/', withScheduleApiBase());
      if (response.data.materials) {
        const m = response.data.materials;
        return {
          miro: m.miro || [],
          notes: m.notes || [],
        };
      }
      return { miro: [], notes: [] };
    }, 30000); // кэш на 30 сек
    
    setMaterials(cachedMaterials);
  };

  const uploadAsset = async (file, assetType) => {
    const formData = new FormData();
    formData.append('file', file);
    formData.append('asset_type', assetType);

    const response = await api.post('materials/upload-asset/', formData, {
      ...withScheduleApiBase(),
      headers: { 'Content-Type': 'multipart/form-data' }
    });

    return response.data;
  };

  const uploadImage = async (file) => {
    try {
      const data = await uploadAsset(file, 'image');
      return { url: data?.url, name: data?.file_name };
    } catch (err) {
      addToast({ type: 'error', title: 'Ошибка', message: err.response?.data?.error || err.response?.data?.detail || 'Не удалось загрузить изображение' });
      return null;
    }
  };

  const uploadFile = async (file) => {
    try {
      const data = await uploadAsset(file, 'file');
      return { url: data?.url, name: data?.file_name };
    } catch (err) {
      addToast({ type: 'error', title: 'Ошибка', message: err.response?.data?.error || err.response?.data?.detail || 'Не удалось загрузить файл' });
      return null;
    }
  };

  const loadLessons = async () => {
    const cachedLessons = await getCached('teacher:lessons', async () => {
      const response = await api.get('lessons', withScheduleApiBase());
      const data = response.data.results || response.data;
      const now = new Date();
      const pastWindow = new Date(now.getTime() - 60 * 24 * 60 * 60 * 1000);
      const filtered = (Array.isArray(data) ? data : []).filter(l => {
        const dt = l.start_time ? new Date(l.start_time) : null;
        return dt && dt >= pastWindow;
      });
      return filtered;
    }, 30000); // кэш на 30 сек
    
    setLessons(cachedLessons);
  };

  const loadGroups = async () => {
    const cachedGroups = await getCached('teacher:groups', async () => {
      const response = await api.get('groups', withScheduleApiBase());
      const data = response.data.results || response.data;
      return Array.isArray(data) ? data : [];
    }, 30000); // кэш на 30 сек
    
    setGroups(cachedGroups);
  };

  const loadStudents = async () => {
    const cachedStudents = await getCached('teacher:students', async () => {
      const response = await api.get('groups/all_students/', withScheduleApiBase());
      const data = response.data || [];
      return Array.isArray(data) ? data : [];
    }, 30000); // кэш на 30 сек
    
    setStudents(cachedStudents);
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
      setMiroForm({ board_url: '', title: '', description: '', lesson_id: '', visibility: 'all_teacher_groups', allowed_groups: [], allowed_students: [] });
      loadMaterials();
    } catch (err) {
      addToast({ type: 'error', title: 'Ошибка', message: err.response?.data?.error || 'Не удалось добавить' });
    }
  };

  const fileInputRef = React.useRef(null);

  const resetNotesForm = () => {
    setNotesForm({
      title: '',
      content: '',
      description: '',
      lesson_id: '',
      visibility: 'all_teacher_groups',
      allowed_groups: [],
      allowed_students: [],
      mode: 'rich',
      files: [] // Массив файлов: [{url, name, size}]
    });
    setEditingNoteId(null);
  };

  const handleRemoveFile = (indexToRemove) => {
    setNotesForm(prev => ({
      ...prev,
      files: prev.files.filter((_, index) => index !== indexToRemove)
    }));
  };

  const handleRemoveAllFiles = () => {
    setNotesForm(prev => ({ ...prev, files: [] }));
    if (fileInputRef.current) {
      fileInputRef.current.value = '';
    }
  };

  const getFileIcon = (fileName) => {
    const ext = fileName?.split('.').pop()?.toLowerCase();
    // Возвращаем расширение файла в верхнем регистре как текстовый бейдж
    const extMap = {
      pdf: 'PDF',
      doc: 'DOC',
      docx: 'DOCX',
      ppt: 'PPT',
      pptx: 'PPTX',
      xls: 'XLS',
      xlsx: 'XLSX',
      zip: 'ZIP',
      rar: 'RAR',
      jpg: 'JPG',
      jpeg: 'JPEG',
      png: 'PNG',
      gif: 'GIF',
      mp4: 'MP4',
      mp3: 'MP3',
      txt: 'TXT'
    };
    return extMap[ext] || ext?.toUpperCase() || 'FILE';
  };

  const handleNotesFileChange = async (e) => {
    const selectedFiles = Array.from(e.target.files || []);
    console.log('Выбрано файлов:', selectedFiles.length);
    
    if (selectedFiles.length === 0) {
      console.log('Нет файлов для загрузки');
      return;
    }

    setNotesFileUploading(true);
    setUploadProgress({ current: 0, total: selectedFiles.length });
    
    // Параллельная загрузка с ограничением concurrency (3 файла одновременно)
    const CONCURRENCY = 3;
    const uploadedFiles = [];
    let completedCount = 0;
    
    const uploadSingleFile = async (file, index) => {
      console.log(`Загружаю файл ${index + 1}/${selectedFiles.length}: ${file.name} (${(file.size / (1024 * 1024)).toFixed(2)} МБ)`);
      
      try {
        const data = await uploadAsset(file, 'file');
        console.log('Файл загружен:', data);
        
        return {
          success: true,
          file: {
            url: data?.url || '',
            name: data?.file_name || file.name,
            size: data?.size_bytes || file.size || 0
          }
        };
      } catch (err) {
        console.error(`Ошибка загрузки ${file.name}:`, err);
        addToast({ 
          type: 'error', 
          title: 'Ошибка', 
          message: `Не удалось загрузить ${file.name}: ${err.message || 'Неизвестная ошибка'}` 
        });
        return { success: false, file: null };
      } finally {
        completedCount++;
        setUploadProgress({ current: completedCount, total: selectedFiles.length });
      }
    };
    
    // Разбиваем на батчи для параллельной загрузки
    for (let i = 0; i < selectedFiles.length; i += CONCURRENCY) {
      const batch = selectedFiles.slice(i, i + CONCURRENCY);
      const results = await Promise.all(
        batch.map((file, batchIdx) => uploadSingleFile(file, i + batchIdx))
      );
      
      results.forEach(result => {
        if (result.success && result.file) {
          uploadedFiles.push(result.file);
        }
      });
    }

    console.log(`Итого загружено: ${uploadedFiles.length} файлов`);

    if (uploadedFiles.length > 0) {
      setNotesForm(prev => ({
        ...prev,
        files: [...prev.files, ...uploadedFiles]
      }));
      addToast({ 
        type: 'success', 
        title: 'Готово', 
        message: `Загружено файлов: ${uploadedFiles.length} из ${selectedFiles.length}` 
      });
    } else {
      addToast({ 
        type: 'error', 
        title: 'Ошибка', 
        message: 'Не удалось загрузить ни одного файла. Проверьте консоль браузера (F12)' 
      });
    }

    setNotesFileUploading(false);
    setUploadProgress({ current: 0, total: 0 });
    e.target.value = '';
  };

  const handleSaveNotes = async (e) => {
    e.preventDefault();
    if (!notesForm.title) {
      addToast({ type: 'warning', title: 'Внимание', message: 'Введите название' });
      return;
    }
    if (notesForm.mode === 'rich' && !notesForm.content) {
      addToast({ type: 'warning', title: 'Внимание', message: 'Добавьте текст конспекта' });
      return;
    }
    if (notesForm.mode === 'file' && (!notesForm.files || notesForm.files.length === 0)) {
      addToast({ type: 'warning', title: 'Внимание', message: 'Прикрепите хотя бы один файл' });
      return;
    }
    try {
      if (editingNoteId) {
        // Редактирование - пока поддерживаем только один файл
        const firstFile = notesForm.files[0] || {};
        const payload = {
          title: notesForm.title,
          description: notesForm.description,
          content: notesForm.mode === 'rich' ? notesForm.content : '',
          lesson: notesForm.lesson_id || null,
          visibility: notesForm.visibility,
          allowed_groups: notesForm.allowed_groups,
          allowed_students: notesForm.allowed_students,
          file_url: notesForm.mode === 'file' && firstFile.url ? firstFile.url : '',
          file_name: notesForm.mode === 'file' && firstFile.name ? firstFile.name : '',
          file_size_bytes: notesForm.mode === 'file' && firstFile.size ? firstFile.size : 0,
        };
        await api.patch(`lesson-materials/${editingNoteId}/`, payload, withScheduleApiBase());
        addToast({ type: 'success', title: 'Готово', message: 'Конспект обновлен' });
      } else {
        // Создание - если несколько файлов, создаём несколько конспектов
        if (notesForm.mode === 'file' && notesForm.files.length > 0) {
          let successCount = 0;
          for (const file of notesForm.files) {
            const payload = {
              title: notesForm.files.length > 1 
                ? `${notesForm.title} - ${file.name}` 
                : notesForm.title,
              description: notesForm.description,
              content: '',
              lesson_id: notesForm.lesson_id || null,
              visibility: notesForm.visibility,
              allowed_groups: notesForm.allowed_groups,
              allowed_students: notesForm.allowed_students,
              file_url: file.url,
              file_name: file.name,
              file_size_bytes: file.size,
            };
            try {
              await api.post('materials/add-notes/', payload, withScheduleApiBase());
              successCount++;
            } catch (err) {
              console.error(`Ошибка создания конспекта для ${file.name}:`, err);
            }
          }
          addToast({ 
            type: 'success', 
            title: 'Готово', 
            message: `Создано конспектов: ${successCount} из ${notesForm.files.length}` 
          });
        } else {
          // Режим текста
          const payload = {
            ...notesForm,
            content: notesForm.mode === 'rich' ? notesForm.content : '',
            file_url: '',
            file_name: '',
            file_size_bytes: 0,
          };
          await api.post('materials/add-notes/', payload, withScheduleApiBase());
          addToast({ type: 'success', title: 'Готово', message: 'Конспект добавлен' });
        }
      }
      setShowAddNotesModal(false);
      resetNotesForm();
      loadMaterials();
    } catch (err) {
      addToast({ type: 'error', title: 'Ошибка', message: err.response?.data?.error || 'Не удалось добавить' });
    }
  };

  // Ленивая загрузка студентов при открытии модала
  const ensureStudentsLoaded = async () => {
    if (students.length === 0) {
      await loadStudents();
    }
  };

  const openCreateNotes = async () => {
    await ensureStudentsLoaded();
    setEditingNoteId(null);
    resetNotesForm();
    setShowAddNotesModal(true);
  };

  const openEditNotes = async (note) => {
    await ensureStudentsLoaded();
    setEditingNoteId(note.id);
    const hasFile = !!note.file_url;
    const hasContent = !!note.content;
    const files = hasFile ? [{
      url: note.file_url,
      name: note.file_name || 'Файл',
      size: note.file_size_bytes || 0
    }] : [];
    setNotesForm({
      title: note.title || '',
      content: note.content || '',
      description: note.description || '',
      lesson_id: note.lesson_info?.id ? String(note.lesson_info.id) : '',
      visibility: note.visibility || 'all_teacher_groups',
      allowed_groups: (note.access_groups || []).map(g => g.id),
      allowed_students: (note.access_students || []).map(s => s.id),
      mode: hasFile && !hasContent ? 'file' : 'rich',
      files: files
    });
    setShowAddNotesModal(true);
  };

  const stripHtml = (html) => {
    if (!html) return '';
    const div = document.createElement('div');
    div.innerHTML = html;
    return (div.textContent || div.innerText || '').trim();
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

  // Группировка уроков по прошедшим/предстоящим для удобного поиска
  const lessonSelectOptions = useMemo(() => {
    const now = new Date();
    const pastLessons = lessons.filter(l => new Date(l.start_time) < now);
    const futureLessons = lessons.filter(l => new Date(l.start_time) >= now);
    const fmt = (dateStr) => {
      const d = new Date(dateStr);
      return d.toLocaleDateString('ru-RU', { day: '2-digit', month: '2-digit', year: 'numeric' });
    };

    const result = [{ value: '', label: 'Без привязки к уроку' }];

    if (pastLessons.length > 0) {
      result.push({ type: 'group', label: 'Прошедшие уроки' });
      pastLessons
        .slice()
        .sort((a, b) => new Date(b.start_time) - new Date(a.start_time))
        .forEach((lesson) => {
          result.push({
            value: String(lesson.id),
            label: `${lesson.title || lesson.subject || 'Урок'} • ${lesson.group_name} (${fmt(lesson.start_time)})`
          });
        });
    }

    if (futureLessons.length > 0) {
      result.push({ type: 'group', label: 'Предстоящие уроки' });
      futureLessons
        .slice()
        .sort((a, b) => new Date(a.start_time) - new Date(b.start_time))
        .forEach((lesson) => {
          result.push({
            value: String(lesson.id),
            label: `${lesson.title || lesson.subject || 'Урок'} • ${lesson.group_name} (${fmt(lesson.start_time)})`
          });
        });
    }

    return result;
  }, [lessons]);

  // Фильтрация групп и учеников по поиску
  const filteredGroups = useMemo(() => {
    if (!groupSearchQuery.trim()) return groups;
    const query = groupSearchQuery.toLowerCase();
    return groups.filter(g => g.name?.toLowerCase().includes(query));
  }, [groups, groupSearchQuery]);

  const filteredStudents = useMemo(() => {
    if (!studentSearchQuery.trim()) return students;
    const query = studentSearchQuery.toLowerCase();
    return students.filter(s => {
      const fullName = (s.full_name || s.name || '').toLowerCase();
      const email = (s.email || '').toLowerCase();
      return fullName.includes(query) || email.includes(query);
    });
  }, [students, studentSearchQuery]);

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
    { id: 'notes', label: 'Конспекты', count: materials.notes?.length || 0 }
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

  if (error) {
    return (
      <div className="materials-page">
        <div className="empty-state">
          <h3>Ошибка загрузки</h3>
          <p>{error}</p>
          <button className="btn btn-primary" onClick={loadAllData}>
            Попробовать снова
          </button>
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
          <p className="subtitle">Доски Miro и конспекты для учеников</p>
        </div>
        
        <div className="header-actions">
          {activeTab === 'miro' && (
            <button className="btn btn-primary" onClick={() => setShowAddMiroModal(true)}>
              Добавить доску Miro
            </button>
          )}
          {activeTab === 'notes' && (
            <button className="btn btn-primary" onClick={openCreateNotes}>
              Создать конспект
            </button>
          )}
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
                <button className="btn btn-primary" onClick={openCreateNotes}>
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
                        {stripHtml(note.content).substring(0, 150)}...
                      </div>
                    )}
                    {note.file_url && (
                      <div className="note-file-badge">Файл: {note.file_name || 'Документ'}</div>
                    )}
                    <div className="card-meta">
                      {note.lesson_info && <span>{note.lesson_info.title}</span>}
                      <span>{note.views_count || 0} просмотров</span>
                      <span>{formatDate(note.created_at)}</span>
                    </div>
                  </div>
                  <div className="card-actions">
                    <button className="btn btn-sm btn-secondary" onClick={() => setPreviewNote(note)}>
                      Открыть
                    </button>
                    <button className="btn btn-sm btn-secondary" onClick={() => openEditNotes(note)}>
                      Редактировать
                    </button>
                    <button className="btn btn-sm btn-danger" onClick={() => handleDeleteMaterial(note.id)}>
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
              <SearchableSelect
                value={miroForm.lesson_id}
                onChange={(e) => setMiroForm({...miroForm, lesson_id: e.target.value})}
                options={lessonSelectOptions}
                placeholder="Без привязки к уроку"
                searchPlaceholder="Поиск по названию урока..."
              />
            </div>
            
            <div className="form-group">
              <label>Видимость</label>
              <div className="teacher-privacy-tabs">
                <button
                  type="button"
                  className={`teacher-privacy-tab ${miroForm.visibility === 'all_teacher_groups' ? 'active' : ''}`}
                  onClick={() => setMiroForm({...miroForm, visibility: 'all_teacher_groups', allowed_groups: [], allowed_students: []})}
                >
                  Все ученики
                </button>
                <button
                  type="button"
                  className={`teacher-privacy-tab ${miroForm.visibility === 'custom_groups' ? 'active' : ''}`}
                  onClick={() => setMiroForm({...miroForm, visibility: 'custom_groups', allowed_students: []})}
                >
                  Выбрать группы
                </button>
                <button
                  type="button"
                  className={`teacher-privacy-tab ${miroForm.visibility === 'custom_students' ? 'active' : ''}`}
                  onClick={() => setMiroForm({...miroForm, visibility: 'custom_students', allowed_groups: []})}
                >
                  Выбрать учеников
                </button>
              </div>
            </div>
            
            {miroForm.visibility === 'custom_groups' && (
              <div className="form-group">
                <p className="teacher-privacy-hint">Выберите группы, которые смогут видеть доску:</p>
                <div className="teacher-privacy-search">
                  <input
                    type="text"
                    value={groupSearchQuery}
                    onChange={(e) => setGroupSearchQuery(e.target.value)}
                    placeholder="Поиск группы..."
                    className="teacher-privacy-search-input"
                  />
                  {groupSearchQuery && (
                    <button 
                      type="button" 
                      className="teacher-privacy-search-clear"
                      onClick={() => setGroupSearchQuery('')}
                    >
                      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                        <path d="M18 6L6 18M6 6l12 12"/>
                      </svg>
                    </button>
                  )}
                </div>
                <div className="teacher-checkbox-list">
                  {filteredGroups.map(group => (
                    <label key={group.id} className="teacher-checkbox-item">
                      <input
                        type="checkbox"
                        checked={miroForm.allowed_groups.includes(group.id)}
                        onChange={(e) => {
                          const newGroups = e.target.checked
                            ? [...miroForm.allowed_groups, group.id]
                            : miroForm.allowed_groups.filter(id => id !== group.id);
                          setMiroForm({...miroForm, allowed_groups: newGroups});
                        }}
                      />
                      <span>{group.name} ({group.student_count || 0} учеников)</span>
                    </label>
                  ))}
                  {filteredGroups.length === 0 && (
                    <div className="teacher-privacy-empty">Группы не найдены</div>
                  )}
                </div>
              </div>
            )}
            
            {miroForm.visibility === 'custom_students' && (
              <div className="form-group">
                <p className="teacher-privacy-hint">Выберите учеников, которые смогут видеть доску:</p>
                <div className="teacher-privacy-search">
                  <input
                    type="text"
                    value={studentSearchQuery}
                    onChange={(e) => setStudentSearchQuery(e.target.value)}
                    placeholder="Поиск ученика..."
                    className="teacher-privacy-search-input"
                  />
                  {studentSearchQuery && (
                    <button 
                      type="button" 
                      className="teacher-privacy-search-clear"
                      onClick={() => setStudentSearchQuery('')}
                    >
                      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                        <path d="M18 6L6 18M6 6l12 12"/>
                      </svg>
                    </button>
                  )}
                </div>
                <div className="teacher-checkbox-list">
                  {filteredStudents.map(student => (
                    <label key={student.id} className="teacher-checkbox-item">
                      <input
                        type="checkbox"
                        checked={miroForm.allowed_students.includes(student.id)}
                        onChange={(e) => {
                          const newStudents = e.target.checked
                            ? [...miroForm.allowed_students, student.id]
                            : miroForm.allowed_students.filter(id => id !== student.id);
                          setMiroForm({...miroForm, allowed_students: newStudents});
                        }}
                      />
                      <span>{student.full_name || student.name || student.email} {student.group_name && <small>({student.group_name})</small>}</span>
                    </label>
                  ))}
                  {filteredStudents.length === 0 && (
                    <div className="teacher-privacy-empty">Ученики не найдены</div>
                  )}
                </div>
              </div>
            )}
            
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
        <Modal
          isOpen={true}
          onClose={() => {
            setShowAddNotesModal(false);
            resetNotesForm();
          }}
          title={editingNoteId ? 'Редактировать конспект' : 'Создать конспект'}
          size="large"
        >
          <form onSubmit={handleSaveNotes} className="modal-form">
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
              <label>Формат конспекта</label>
              <div className="notes-mode-toggle">
                <button
                  type="button"
                  className={`notes-mode-btn ${notesForm.mode === 'rich' ? 'active' : ''}`}
                  onClick={() => setNotesForm(prev => ({ ...prev, mode: 'rich' }))}
                >
                  Текст с редактором
                </button>
                <button
                  type="button"
                  className={`notes-mode-btn ${notesForm.mode === 'file' ? 'active' : ''}`}
                  onClick={() => setNotesForm(prev => ({ ...prev, mode: 'file' }))}
                >
                  Файл (PDF/PPT/DOC)
                </button>
              </div>
              <small>Можно выбрать один формат для конспекта</small>
            </div>
            
            {notesForm.mode === 'rich' && (
              <div className="form-group">
                <label>Содержание</label>
                <Suspense fallback={<div className="editor-loading">Загрузка редактора...</div>}>
                  <RichTextEditor
                    value={notesForm.content}
                    onChange={(html) => setNotesForm({ ...notesForm, content: html })}
                    placeholder="Напишите конспект…"
                    onUploadImage={uploadImage}
                    onUploadFile={uploadFile}
                  />
                </Suspense>
                <small>Можно вставлять изображения и прикреплять файлы прямо в текст</small>
              </div>
            )}

            {notesForm.mode === 'file' && (
              <div className="form-group">
                <label>Файлы конспектов</label>
                
                <div className="notes-file-upload-zone">
                  <input
                    ref={fileInputRef}
                    type="file"
                    onChange={handleNotesFileChange}
                    disabled={notesFileUploading}
                    multiple
                    style={{ display: 'none' }}
                  />
                  <button
                    type="button"
                    className="btn btn-secondary file-select-btn"
                    onClick={() => fileInputRef.current?.click()}
                    disabled={notesFileUploading}
                  >
                    {notesFileUploading ? 'Загрузка...' : 'Выбрать файлы'}
                  </button>
                  <div className="notes-file-hint">
                    {notesFileUploading 
                      ? 'Загружаем файлы, пожалуйста подождите...'
                      : 'Можно выбрать несколько файлов. Любой формат, до 1 ГБ каждый'}
                  </div>
                </div>

                {notesFileUploading && (
                  <div className="upload-progress">
                    <div className="upload-spinner"></div>
                    <div className="upload-progress-text">
                      <span>Загружаем файлы... ({uploadProgress.current} из {uploadProgress.total})</span>
                      <div className="upload-progress-bar">
                        <div 
                          className="upload-progress-fill" 
                          style={{ width: `${(uploadProgress.current / uploadProgress.total) * 100}%` }}
                        ></div>
                      </div>
                    </div>
                  </div>
                )}

                {notesForm.files && notesForm.files.length > 0 && (
                  <div className="notes-files-list">
                    <div className="files-list-header">
                      <span>Прикреплено файлов: {notesForm.files.length}</span>
                      <button
                        type="button"
                        className="btn btn-sm btn-danger"
                        onClick={handleRemoveAllFiles}
                      >
                        Удалить все
                      </button>
                    </div>
                    {notesForm.files.map((file, index) => (
                      <div key={index} className="notes-file-preview">
                        <div className="notes-file-icon">{getFileIcon(file.name)}</div>
                        <div className="notes-file-meta">
                          <div className="notes-file-name">{file.name}</div>
                          {file.size > 0 && (
                            <div className="notes-file-size">
                              {(file.size / (1024 * 1024)).toFixed(2)} МБ
                            </div>
                          )}
                        </div>
                        <div className="notes-file-actions">
                          {file.url && (
                            <a
                              href={file.url}
                              target="_blank"
                              rel="noopener noreferrer"
                              className="btn btn-sm btn-secondary"
                            >
                              Открыть
                            </a>
                          )}
                          <button
                            type="button"
                            className="btn btn-sm btn-danger"
                            onClick={() => handleRemoveFile(index)}
                          >
                            Удалить
                          </button>
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            )}
            
            <div className="form-group">
              <label>Привязать к уроку</label>
              <SearchableSelect
                value={notesForm.lesson_id}
                onChange={(e) => setNotesForm({...notesForm, lesson_id: e.target.value})}
                options={lessonSelectOptions}
                placeholder="Без привязки к уроку"
                searchPlaceholder="Поиск по названию урока..."
              />
            </div>
            
            <div className="form-group">
              <label>Видимость</label>
              <div className="teacher-privacy-tabs">
                <button
                  type="button"
                  className={`teacher-privacy-tab ${notesForm.visibility === 'all_teacher_groups' ? 'active' : ''}`}
                  onClick={() => setNotesForm({...notesForm, visibility: 'all_teacher_groups', allowed_groups: [], allowed_students: []})}
                >
                  Все ученики
                </button>
                <button
                  type="button"
                  className={`teacher-privacy-tab ${notesForm.visibility === 'custom_groups' ? 'active' : ''}`}
                  onClick={() => setNotesForm({...notesForm, visibility: 'custom_groups', allowed_students: []})}
                >
                  Выбрать группы
                </button>
                <button
                  type="button"
                  className={`teacher-privacy-tab ${notesForm.visibility === 'custom_students' ? 'active' : ''}`}
                  onClick={() => setNotesForm({...notesForm, visibility: 'custom_students', allowed_groups: []})}
                >
                  Выбрать учеников
                </button>
              </div>
            </div>
            
            {notesForm.visibility === 'custom_groups' && (
              <div className="form-group">
                <p className="teacher-privacy-hint">Выберите группы, которые смогут видеть этот конспект:</p>
                <div className="teacher-privacy-search">
                  <input
                    type="text"
                    value={groupSearchQuery}
                    onChange={(e) => setGroupSearchQuery(e.target.value)}
                    placeholder="Поиск группы..."
                    className="teacher-privacy-search-input"
                  />
                  {groupSearchQuery && (
                    <button 
                      type="button" 
                      className="teacher-privacy-search-clear"
                      onClick={() => setGroupSearchQuery('')}
                    >
                      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                        <path d="M18 6L6 18M6 6l12 12"/>
                      </svg>
                    </button>
                  )}
                </div>
                <div className="teacher-checkbox-list">
                  {filteredGroups.map(group => (
                    <label key={group.id} className="teacher-checkbox-item">
                      <input
                        type="checkbox"
                        checked={notesForm.allowed_groups.includes(group.id)}
                        onChange={(e) => {
                          const newGroups = e.target.checked
                            ? [...notesForm.allowed_groups, group.id]
                            : notesForm.allowed_groups.filter(id => id !== group.id);
                          setNotesForm({...notesForm, allowed_groups: newGroups});
                        }}
                      />
                      <span>{group.name} ({group.student_count || 0} учеников)</span>
                    </label>
                  ))}
                  {filteredGroups.length === 0 && (
                    <div className="teacher-privacy-empty">Группы не найдены</div>
                  )}
                </div>
              </div>
            )}
            
            {notesForm.visibility === 'custom_students' && (
              <div className="form-group">
                <p className="teacher-privacy-hint">Выберите учеников, которые смогут видеть этот конспект:</p>
                <div className="teacher-privacy-search">
                  <input
                    type="text"
                    value={studentSearchQuery}
                    onChange={(e) => setStudentSearchQuery(e.target.value)}
                    placeholder="Поиск ученика..."
                    className="teacher-privacy-search-input"
                  />
                  {studentSearchQuery && (
                    <button 
                      type="button" 
                      className="teacher-privacy-search-clear"
                      onClick={() => setStudentSearchQuery('')}
                    >
                      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                        <path d="M18 6L6 18M6 6l12 12"/>
                      </svg>
                    </button>
                  )}
                </div>
                <div className="teacher-checkbox-list">
                  {filteredStudents.map(student => (
                    <label key={student.id} className="teacher-checkbox-item">
                      <input
                        type="checkbox"
                        checked={notesForm.allowed_students.includes(student.id)}
                        onChange={(e) => {
                          const newStudents = e.target.checked
                            ? [...notesForm.allowed_students, student.id]
                            : notesForm.allowed_students.filter(id => id !== student.id);
                          setNotesForm({...notesForm, allowed_students: newStudents});
                        }}
                      />
                      <span>{student.full_name || student.name || student.email} {student.group_name && <small>({student.group_name})</small>}</span>
                    </label>
                  ))}
                  {filteredStudents.length === 0 && (
                    <div className="teacher-privacy-empty">Ученики не найдены</div>
                  )}
                </div>
              </div>
            )}
            
            <div className="modal-footer">
              <button type="button" onClick={() => {
                setShowAddNotesModal(false);
                resetNotesForm();
              }} className="btn btn-secondary">
                Отмена
              </button>
              <button type="submit" className="btn btn-primary">
                {editingNoteId ? 'Сохранить изменения' : 'Сохранить'}
              </button>
            </div>
          </form>
        </Modal>
      )}

      {/* Preview Notes Modal */}
      {previewNote && (
        <Modal
          isOpen={true}
          onClose={() => setPreviewNote(null)}
          title={previewNote.title}
          size="large"
        >
          <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
            {previewNote.description && <div style={{ color: 'var(--text-secondary)' }}>{previewNote.description}</div>}
            {previewNote.file_url && (
              <div className="notes-file-preview">
                <div className="notes-file-meta">
                  <div className="notes-file-name">{previewNote.file_name || 'Документ'}</div>
                  {previewNote.file_size_bytes > 0 && (
                    <div className="notes-file-size">{Math.round(previewNote.file_size_bytes / 1024)} KB</div>
                  )}
                </div>
                <div className="notes-file-actions">
                  <a href={previewNote.file_url} target="_blank" rel="noopener noreferrer" className="link-btn">
                    Открыть файл
                  </a>
                </div>
              </div>
            )}
            <Suspense fallback={<div className="editor-loading">Загрузка редактора...</div>}>
              {previewNote.content ? (
                <RichTextEditor value={previewNote.content || ''} readOnly={true} />
              ) : (
                <div className="notes-empty-preview">Текст конспекта отсутствует</div>
              )}
            </Suspense>
          </div>
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
