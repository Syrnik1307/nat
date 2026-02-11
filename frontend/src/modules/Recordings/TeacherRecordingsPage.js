import React, { useState, useEffect, useCallback } from 'react';
import './TeacherRecordingsPage.css';
import api, { withScheduleApiBase } from '../../apiService';
import RecordingCard from './RecordingCard';
import FastVideoModal from './FastVideoModal';
import { ConfirmModal, Select, SearchableSelect, ToastContainer } from '../../shared/components';

function TeacherRecordingsPage() {
  const [recordings, setRecordings] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [selectedRecording, setSelectedRecording] = useState(null);
  const [searchTerm, setSearchTerm] = useState('');
  const [groupFilter, setGroupFilter] = useState('all');
  const [statusFilter, setStatusFilter] = useState('all');
  const [groups, setGroups] = useState([]);
  const [stats, setStats] = useState({
    total: 0,
    ready: 0,
    processing: 0,
    failed: 0
  });
  const [showUploadModal, setShowUploadModal] = useState(false);
  const [uploadForm, setUploadForm] = useState({
    lessonId: '',
    title: '',
    file: null,
    privacyType: 'all', // 'all', 'groups', 'students'
    selectedGroups: [],
    selectedStudents: []
  });
  const [lessons, setLessons] = useState([]);
  const [students, setStudents] = useState([]);
  const [dragActive, setDragActive] = useState(false);
  const [groupSearchQuery, setGroupSearchQuery] = useState('');
  const [studentSearchQuery, setStudentSearchQuery] = useState('');
  const [confirmModal, setConfirmModal] = useState({
    isOpen: false,
    title: '',
    message: '',
    onConfirm: null,
    variant: 'warning',
    confirmText: 'Да',
    cancelText: 'Отмена'
  });

  // Toast уведомления для фоновой загрузки
  const [toasts, setToasts] = useState([]);
  
  // Ref для хранения AbortControllers (чтобы избежать проблем с closures)
  const uploadControllersRef = React.useRef({});

  // Функции для toast
  const addToast = useCallback((toast) => {
    const id = Date.now() + Math.random();
    setToasts(prev => [...prev, { id, ...toast }]);
    return id;
  }, []);

  const removeToast = useCallback((id) => {
    setToasts(prev => prev.filter(t => t.id !== id));
    // Также удаляем контроллер если есть
    delete uploadControllersRef.current[id];
  }, []);

  const updateToast = useCallback((id, updates) => {
    setToasts(prev => prev.map(t => t.id === id ? { ...t, ...updates } : t));
  }, []);

  // Функция отмены загрузки
  const cancelUpload = useCallback((toastId) => {
    const controller = uploadControllersRef.current[toastId];
    if (controller) {
      controller.abort();
    }
  }, []);

  useEffect(() => {
    loadRecordings();
    loadGroups();
    loadLessons();
    loadStudents();
  }, []);

  const loadLessons = async () => {
    try {
      const response = await api.get('lessons', withScheduleApiBase());
      const lessonsData = response.data.results || response.data;
      const now = new Date();
      const pastWindow = new Date(now.getTime() - 30 * 24 * 60 * 60 * 1000); // 30 дней назад
      const filteredLessons = (Array.isArray(lessonsData) ? lessonsData : []).filter((l) => {
        const dt = l.start_time ? new Date(l.start_time) : null;
        if (!dt || dt < pastWindow) return false;
        const title = (l.title || '').toLowerCase();
        return !title.includes('smoke');
      });
      setLessons(filteredLessons);
    } catch (err) {
      console.error('Error loading lessons:', err);
    }
  };

  const loadStudents = async () => {
    try {
      const response = await api.get('groups', withScheduleApiBase());
      const rawData = response.data.results || response.data;
      const groupsData = Array.isArray(rawData) ? rawData : [];
      const allStudents = [];
      groupsData.forEach(group => {
        if (group.students && Array.isArray(group.students)) {
          group.students.forEach(student => {
            if (!allStudents.find(s => s.id === student.id)) {
              allStudents.push(student);
            }
          });
        }
      });
      setStudents(allStudents);
    } catch (err) {
      console.error('Error loading students:', err);
    }
  };

  const loadRecordings = async () => {
    try {
      setLoading(true);
      setError(null);
      const response = await api.get('recordings/teacher/', withScheduleApiBase());
      const rawData = response.data.results || response.data;
      const recordingsData = Array.isArray(rawData) ? rawData : [];
      setRecordings(recordingsData);
      
      // Подсчитываем статистику
      const stats = {
        total: recordingsData.length,
        ready: recordingsData.filter(r => r.status === 'ready').length,
        processing: recordingsData.filter(r => r.status === 'processing').length,
        failed: recordingsData.filter(r => r.status === 'failed').length
      };
      setStats(stats);
    } catch (err) {
      console.error('Error loading recordings:', err);
      setError('Не удалось загрузить записи. Попробуйте позже.');
    } finally {
      setLoading(false);
    }
  };

  const loadGroups = async () => {
    try {
      const response = await api.get('groups', withScheduleApiBase());
      const groupsData = response.data.results || response.data;
      setGroups(Array.isArray(groupsData) ? groupsData : []);
    } catch (err) {
      console.error('Error loading groups:', err);
    }
  };

  const openPlayer = async (recording) => {
    setSelectedRecording(recording);
    // Трекаем просмотр
    try {
      await api.post(`recordings/${recording.id}/view/`, {}, withScheduleApiBase());
    } catch (err) {
      console.error('Error tracking view:', err);
    }
  };

  const closePlayer = () => {
    setSelectedRecording(null);
    // Обновляем список чтобы показать новый счетчик просмотров
    loadRecordings();
  };

  const handleDelete = async (recordingId) => {
    setConfirmModal({
      isOpen: true,
      title: 'Удаление записи',
      message: 'Вы уверены, что хотите удалить эту запись? Это действие необратимо.',
      variant: 'danger',
      confirmText: 'Удалить',
      cancelText: 'Отмена',
      onConfirm: async () => {
        try {
          await api.delete(`recordings/${recordingId}/`, withScheduleApiBase());
          setRecordings(recordings.filter(r => r.id !== recordingId));
          addToast({
            type: 'success',
            title: 'Запись удалена',
            message: 'Запись успешно удалена'
          });
        } catch (err) {
          console.error('Error deleting recording:', err);
          addToast({
            type: 'error',
            title: 'Ошибка удаления',
            message: 'Не удалось удалить запись. Попробуйте позже.'
          });
        }
        setConfirmModal({ ...confirmModal, isOpen: false });
      }
    });
  };

  const handleRename = async (recordingId, newTitle) => {
    try {
      const response = await api.patch(`recordings/${recordingId}/`, { title: newTitle }, withScheduleApiBase());
      // Обновляем локальное состояние
      setRecordings(recordings.map(r => 
        r.id === recordingId ? { ...r, title: response.data.title || newTitle } : r
      ));
      addToast({
        type: 'success',
        title: 'Название изменено',
        message: 'Название записи успешно обновлено'
      });
    } catch (err) {
      console.error('Error renaming recording:', err);
      const errorMsg = err.response?.data?.error || 'Не удалось изменить название';
      addToast({
        type: 'error',
        title: 'Ошибка',
        message: errorMsg
      });
      throw err; // Чтобы RecordingCard знал об ошибке
    }
  };

  const closeUploadModal = () => {
    setShowUploadModal(false);
    setGroupSearchQuery('');
    setStudentSearchQuery('');
  };

  const handleUploadSubmit = async (e) => {
    e.preventDefault();
    
    if (!uploadForm.file) {
      addToast({
        type: 'warning',
        title: 'Внимание',
        message: 'Пожалуйста, выберите видео файл'
      });
      return;
    }

    if (!uploadForm.lessonId && !uploadForm.title.trim()) {
      addToast({
        type: 'warning',
        title: 'Внимание',
        message: 'Укажите название видео или выберите урок'
      });
      return;
    }

    if (uploadForm.privacyType === 'groups' && uploadForm.selectedGroups.length === 0) {
      addToast({
        type: 'warning',
        title: 'Внимание',
        message: 'Выберите хотя бы одну группу'
      });
      return;
    }

    if (uploadForm.privacyType === 'students' && uploadForm.selectedStudents.length === 0) {
      addToast({
        type: 'warning',
        title: 'Внимание',
        message: 'Выберите хотя бы одного ученика'
      });
      return;
    }

    // Закрываем модальное окно сразу - загрузка будет в фоне
    const fileName = uploadForm.file.name;
    const fileToUpload = uploadForm.file;
    const formDataToSend = { ...uploadForm };
    
    closeUploadModal();
    setUploadForm({
      lessonId: '',
      title: '',
      file: null,
      privacyType: 'all',
      selectedGroups: [],
      selectedStudents: []
    });

    // Добавляем toast с прогрессом
    const toastId = addToast({
      type: 'progress',
      title: 'Загрузка видео',
      message: fileName,
      progress: 0
    });

    try {
      const formData = new FormData();
      formData.append('video', fileToUpload);
      formData.append('privacy_type', formDataToSend.privacyType);
      
      if (formDataToSend.lessonId) {
        formData.append('lesson_id', formDataToSend.lessonId);
      }
      
      if (formDataToSend.title.trim()) {
        formData.append('title', formDataToSend.title.trim());
      }
      
      if (formDataToSend.privacyType === 'groups') {
        formData.append('allowed_groups', JSON.stringify(formDataToSend.selectedGroups));
      } else if (formDataToSend.privacyType === 'students') {
        formData.append('allowed_students', JSON.stringify(formDataToSend.selectedStudents));
      }
      
      const endpoint = formDataToSend.lessonId 
        ? `lessons/${formDataToSend.lessonId}/upload_recording/`
        : 'lessons/upload_standalone_recording/';

      // Создаём AbortController для отмены загрузки
      const abortController = new AbortController();
      uploadControllersRef.current[toastId] = abortController;
      
      // Добавляем функцию отмены в toast
      updateToast(toastId, { 
        onCancel: () => cancelUpload(toastId)
      });
      
      const response = await api.post(
        endpoint,
        formData,
        {
          ...withScheduleApiBase(),
          headers: {
            'Content-Type': 'multipart/form-data'
          },
          timeout: 600000, // 10 минут для больших файлов
          signal: abortController.signal,
          onUploadProgress: (progressEvent) => {
            const percentCompleted = Math.round((progressEvent.loaded * 100) / progressEvent.total);
            updateToast(toastId, { progress: percentCompleted });
          }
        }
      );
      
      // Сервер принял файл и поставил задачу на загрузку в облако
      // Обновляем toast — файл принят, обработка в фоне
      removeToast(toastId);
      addToast({
        type: 'success',
        title: 'Видео принято',
        message: `${fileName} — загрузка в облако идёт в фоне`
      });
      
      // Обновляем список — новая запись появится со статусом "processing"
      loadRecordings();
      
      // Запускаем поллинг, чтобы обновить статус когда запись будет готова
      const recordingId = response?.data?.recording?.id;
      if (recordingId && response?.data?.recording?.status === 'processing') {
        pollRecordingStatus(recordingId);
      }
    } catch (err) {
      console.error('Error uploading video:', err);
      
      // Ошибка - заменяем toast
      removeToast(toastId);
      
      // Если отменено пользователем - показываем соответствующее сообщение
      if (err.name === 'CanceledError' || err.code === 'ERR_CANCELED') {
        addToast({
          type: 'warning',
          title: 'Загрузка отменена',
          message: fileName
        });
        return;
      }
      
      let errorMessage = 'Не удалось загрузить видео';
      if (err.code === 'ECONNABORTED' || err.message?.includes('timeout')) {
        errorMessage = 'Превышено время ожидания. Попробуйте загрузить файл меньшего размера или проверьте интернет-соединение.';
      } else if (err.response?.data?.detail) {
        errorMessage = err.response.data.detail;
      }
      
      addToast({
        type: 'error',
        title: 'Ошибка загрузки',
        message: errorMessage,
        duration: 10000 // 10 секунд для ошибок
      });
    }
  };

  // Поллинг статуса записи (ждём пока Celery загрузит на GDrive)
  const pollRecordingStatus = useCallback((recordingId) => {
    let attempts = 0;
    const maxAttempts = 60; // 5 минут макс (60 * 5s)
    
    const poll = setInterval(async () => {
      attempts++;
      if (attempts > maxAttempts) {
        clearInterval(poll);
        return;
      }
      
      try {
        const response = await api.get('recordings/teacher/', withScheduleApiBase());
        const rawData = response.data.results || response.data;
        const allRecordings = Array.isArray(rawData) ? rawData : [];
        const target = allRecordings.find(r => r.id === recordingId);
        
        if (target && target.status !== 'processing') {
          clearInterval(poll);
          setRecordings(allRecordings);
          
          // Обновляем статистику
          setStats({
            total: allRecordings.length,
            ready: allRecordings.filter(r => r.status === 'ready').length,
            processing: allRecordings.filter(r => r.status === 'processing').length,
            failed: allRecordings.filter(r => r.status === 'failed').length
          });
          
          if (target.status === 'ready') {
            addToast({
              type: 'success',
              title: 'Видео готово',
              message: target.title || 'Запись доступна для просмотра'
            });
          } else if (target.status === 'failed') {
            addToast({
              type: 'error',
              title: 'Ошибка обработки',
              message: `Не удалось обработать: ${target.title || 'запись'}`,
              duration: 10000
            });
          }
        }
      } catch (err) {
        // Ошибка поллинга — не критично
        console.debug('Polling error:', err);
      }
    }, 5000); // Каждые 5 секунд
    
    return () => clearInterval(poll);
  }, [addToast]);

  const handleDrag = (e) => {
    e.preventDefault();
    e.stopPropagation();
    if (e.type === 'dragenter' || e.type === 'dragover') {
      setDragActive(true);
    } else if (e.type === 'dragleave') {
      setDragActive(false);
    }
  };

  const handleDrop = (e) => {
    e.preventDefault();
    e.stopPropagation();
    setDragActive(false);
    
    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      const file = e.dataTransfer.files[0];
      if (file.type.startsWith('video/')) {
        setUploadForm({...uploadForm, file});
      } else {
        addToast({
          type: 'warning',
          title: 'Неверный формат',
          message: 'Пожалуйста, выберите видео файл'
        });
      }
    }
  };

  const handleFileInput = (e) => {
    if (e.target.files && e.target.files[0]) {
      const file = e.target.files[0];
      if (file.type.startsWith('video/')) {
        setUploadForm({...uploadForm, file});
      } else {
        addToast({
          type: 'warning',
          title: 'Неверный формат',
          message: 'Пожалуйста, выберите видео файл'
        });
      }
    }
  };

  const getRecordingAccessGroupIds = (recording) => {
    if (Array.isArray(recording.access_groups) && recording.access_groups.length > 0) {
      return recording.access_groups.map(group => group.id);
    }
    const fallbackId = recording.lesson_info?.group_id;
    return fallbackId ? [fallbackId] : [];
  };

  // Фильтрация записей
  const filteredRecordings = recordings.filter(recording => {
    const lessonInfo = recording.lesson_info || {};
    const normalizedSearch = searchTerm.trim().toLowerCase();
    const lessonTitle = (lessonInfo.title || '').toLowerCase();
    const lessonSubject = (lessonInfo.subject || '').toLowerCase();
    const lessonGroupName = (lessonInfo.group_name || lessonInfo.group || '').toLowerCase();
    const matchesSearch = !normalizedSearch 
      || lessonTitle.includes(normalizedSearch)
      || lessonSubject.includes(normalizedSearch)
      || lessonGroupName.includes(normalizedSearch)
      || (Array.isArray(recording.access_groups) && recording.access_groups
        .some(group => (group.name || '').toLowerCase().includes(normalizedSearch)));

    const accessGroupIds = getRecordingAccessGroupIds(recording);
    const matchesGroup = groupFilter === 'all' 
      || accessGroupIds.includes(Number(groupFilter));

    const matchesStatus = statusFilter === 'all' || recording.status === statusFilter;
    
    return matchesSearch && matchesGroup && matchesStatus;
  });

  const groupFilterOptions = [
    { value: 'all', label: 'Все группы' },
    ...groups.map(group => ({ value: String(group.id), label: group.name }))
  ];

  const statusFilterOptions = [
    { value: 'all', label: 'Все статусы' },
    { value: 'ready', label: 'Готово' },
    { value: 'processing', label: 'Обрабатывается' },
    { value: 'failed', label: 'Ошибка' },
    { value: 'archived', label: 'Архивировано' }
  ];

  // Количество активных загрузок (toasts с типом progress)
  const activeUploadsCount = toasts.filter(t => t.type === 'progress').length;

  const lessonSelectOptions = (() => {
    const now = new Date();
    const pastLessons = lessons.filter(l => new Date(l.start_time) < now);
    const futureLessons = lessons.filter(l => new Date(l.start_time) >= now);
    const formatDate = (dateStr) => {
      const d = new Date(dateStr);
      return d.toLocaleDateString('ru-RU', { day: '2-digit', month: '2-digit', year: 'numeric' });
    };

    const result = [{ value: '', label: '📹 Самостоятельное видео' }];

    if (pastLessons.length > 0) {
      result.push({ type: 'group', label: '📚 Прошедшие уроки' });
      pastLessons
        .slice()
        .sort((a, b) => new Date(b.start_time) - new Date(a.start_time))
        .forEach((lesson) => {
          result.push({
            value: String(lesson.id),
            label: `${lesson.title || lesson.subject} • ${lesson.group_name} (${formatDate(lesson.start_time)})`
          });
        });
    }

    if (futureLessons.length > 0) {
      result.push({ type: 'group', label: '📅 Предстоящие уроки' });
      futureLessons
        .slice()
        .sort((a, b) => new Date(a.start_time) - new Date(b.start_time))
        .forEach((lesson) => {
          result.push({
            value: String(lesson.id),
            label: `${lesson.title || lesson.subject} • ${lesson.group_name} (${formatDate(lesson.start_time)})`
          });
        });
    }

    return result;
  })();

  return (
    <div className="teacher-recordings-page">
      <div className="teacher-recordings-header">
        <div>
          <h1>Записи моих уроков</h1>
          <p className="teacher-recordings-subtitle">Управление и просмотр записей занятий</p>
        </div>
        <button 
          className="teacher-upload-btn"
          onClick={() => setShowUploadModal(true)}
          data-tour="rec-upload"
        >
          Загрузить видео
        </button>
      </div>

      {/* Статистика */}
      <div className="teacher-stats-grid" data-tour="rec-stats">
        <div className="teacher-stat-card">
          <div className="teacher-stat-icon"></div>
          <div className="teacher-stat-info">
            <div className="teacher-stat-value">{stats.total + activeUploadsCount}</div>
            <div className="teacher-stat-label">Всего записей</div>
          </div>
        </div>
        <div className="teacher-stat-card teacher-stat-success">
          <div className="teacher-stat-icon"></div>
          <div className="teacher-stat-info">
            <div className="teacher-stat-value">{stats.ready}</div>
            <div className="teacher-stat-label">Готово</div>
          </div>
        </div>
        <div className="teacher-stat-card teacher-stat-warning">
          <div className="teacher-stat-icon"></div>
          <div className="teacher-stat-info">
            <div className="teacher-stat-value">{stats.processing + activeUploadsCount}</div>
            <div className="teacher-stat-label">Обрабатывается</div>
          </div>
        </div>
        <div className="teacher-stat-card teacher-stat-danger">
          <div className="teacher-stat-icon"></div>
          <div className="teacher-stat-info">
            <div className="teacher-stat-value">{stats.failed}</div>
            <div className="teacher-stat-label">Ошибка</div>
          </div>
        </div>
      </div>

      {/* Фильтры */}
      <div className="teacher-recordings-filters" data-tour="rec-filters">
        <div className="teacher-search-box">
          <input
            type="text"
            placeholder="Поиск по предмету или группе..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            className="teacher-search-input"
          />
        </div>

        <div className="teacher-filter-group">
          <label>Группа:</label>
          <Select
            value={groupFilter}
            onChange={(e) => setGroupFilter(e.target.value)}
            options={groupFilterOptions}
            placeholder="Все группы"
          />
        </div>

        <div className="teacher-filter-group">
          <label>Статус:</label>
          <Select
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value)}
            options={statusFilterOptions}
            placeholder="Все статусы"
          />
        </div>

        <button onClick={loadRecordings} className="teacher-refresh-btn">
          Обновить
        </button>
      </div>

      {/* Контент */}
      {loading ? (
        <div className="teacher-recordings-loading">
          <div className="teacher-spinner"></div>
          <p>Загрузка записей...</p>
        </div>
      ) : error ? (
        <div className="teacher-recordings-error">
          <p>{error}</p>
          <button onClick={loadRecordings} className="teacher-retry-btn">
            Попробовать снова
          </button>
        </div>
      ) : filteredRecordings.length === 0 ? (
        <div className="teacher-recordings-empty">
          <div className="teacher-empty-icon"></div>
          <h3>Записей не найдено</h3>
          <p>
            {recordings.length === 0
              ? 'Пока нет записанных уроков. Включите запись при создании урока.'
              : 'Попробуйте изменить фильтры или поисковый запрос.'}
          </p>
        </div>
      ) : (
        <>
          <div className="teacher-recordings-count">
            Найдено записей: <strong>{filteredRecordings.length}</strong>
          </div>
          <div className="teacher-recordings-grid" data-tour="rec-card">
            {filteredRecordings.map(recording => (
              <RecordingCard
                key={recording.id}
                recording={recording}
                onPlay={openPlayer}
                onDelete={handleDelete}
                onRename={handleRename}
                showDelete={true}
                showEdit={true}
              />
            ))}
          </div>
        </>
      )}

      <ConfirmModal
        isOpen={confirmModal.isOpen}
        onClose={() => setConfirmModal({ ...confirmModal, isOpen: false })}
        onConfirm={confirmModal.onConfirm}
        title={confirmModal.title}
        message={confirmModal.message}
        variant={confirmModal.variant}
        confirmText={confirmModal.confirmText}
        cancelText={confirmModal.cancelText}
      />

      {/* Toast уведомления */}
      <ToastContainer toasts={toasts} onRemove={removeToast} />

      {/* Плеер */}
      {selectedRecording && (
        <FastVideoModal
          recording={selectedRecording}
          onClose={closePlayer}
        />
      )}

      {/* Модальное окно загрузки */}
      {showUploadModal && (
        <div className="teacher-upload-modal-overlay" onClick={closeUploadModal}>
          <div className="teacher-upload-modal" onClick={(e) => e.stopPropagation()}>
            <div className="teacher-upload-modal-header">
              <h2>Загрузить видео урока</h2>
              <button className="teacher-modal-close" onClick={closeUploadModal}>×</button>
            </div>
            <form onSubmit={handleUploadSubmit} className="teacher-upload-form" noValidate>
              <div className="teacher-upload-field">
                <label>Привязать к уроку (необязательно)</label>
                <SearchableSelect
                  value={uploadForm.lessonId}
                  onChange={(e) => setUploadForm({ ...uploadForm, lessonId: e.target.value })}
                  options={lessonSelectOptions}
                  placeholder="Самостоятельное видео"
                  searchPlaceholder="Поиск по названию урока..."
                />
                <small className="teacher-upload-hint">
                  Выберите урок для привязки или оставьте "Самостоятельное видео" для дополнительных материалов
                </small>
              </div>

              <div className="teacher-upload-field">
                <label>Название видео {!uploadForm.lessonId && '*'}</label>
                <input
                  type="text"
                  value={uploadForm.title}
                  onChange={(e) => setUploadForm({...uploadForm, title: e.target.value})}
                  placeholder="Например: Дополнительный материал по теме..."
                  className="teacher-upload-input"
                />
                <small className="teacher-upload-hint">
                  {uploadForm.lessonId 
                    ? 'Необязательно - будет использовано название урока' 
                    : 'Обязательно для самостоятельных видео'}
                </small>
              </div>

              <div className="teacher-upload-field">
                <label>Видео файл *</label>
                <div 
                  className={`teacher-dropzone ${dragActive ? 'teacher-dropzone-active' : ''}`}
                  onDragEnter={handleDrag}
                  onDragLeave={handleDrag}
                  onDragOver={handleDrag}
                  onDrop={handleDrop}
                >
                  {uploadForm.file ? (
                    <div className="teacher-file-preview">
                      <div className="teacher-file-icon"></div>
                      <div className="teacher-file-info">
                        <div className="teacher-file-name">{uploadForm.file.name}</div>
                        <div className="teacher-file-size">
                          {(uploadForm.file.size / (1024 * 1024)).toFixed(2)} MB
                        </div>
                      </div>
                      <button
                        type="button"
                        className="teacher-file-remove"
                        onClick={() => setUploadForm({...uploadForm, file: null})}
                      >
                        ✕
                      </button>
                    </div>
                  ) : (
                    <>
                      <div className="teacher-dropzone-icon"></div>
                      <p className="teacher-dropzone-text">
                        Перетащите видео сюда или
                      </p>
                      <label className="teacher-file-input-label">
                        <input
                          type="file"
                          accept="video/*"
                          onChange={handleFileInput}
                          className="teacher-file-input-hidden"
                        />
                        <span className="teacher-file-input-btn">Выберите файл</span>
                      </label>
                      <p className="teacher-dropzone-hint">
                        Поддерживаются: MP4, AVI, MOV, MKV
                      </p>
                    </>
                  )}
                </div>
              </div>

              <div className="teacher-upload-field" data-tour="rec-privacy">
                <label>Приватность *</label>
                <div className="teacher-privacy-tabs">
                  <button
                    type="button"
                    className={`teacher-privacy-tab ${uploadForm.privacyType === 'all' ? 'active' : ''}`}
                    onClick={() => setUploadForm({...uploadForm, privacyType: 'all'})}
                  >
                    Все ученики
                  </button>
                  <button
                    type="button"
                    className={`teacher-privacy-tab ${uploadForm.privacyType === 'groups' ? 'active' : ''}`}
                    onClick={() => setUploadForm({...uploadForm, privacyType: 'groups'})}
                  >
                    Выбрать группы
                  </button>
                  <button
                    type="button"
                    className={`teacher-privacy-tab ${uploadForm.privacyType === 'students' ? 'active' : ''}`}
                    onClick={() => setUploadForm({...uploadForm, privacyType: 'students'})}
                  >
                    Выбрать учеников
                  </button>
                </div>

                {uploadForm.privacyType === 'groups' && (
                  <div className="teacher-privacy-selector">
                    <p className="teacher-privacy-hint">Выберите группы, которые смогут видеть это видео:</p>
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
                      {groups
                        .filter(group => {
                          if (!groupSearchQuery.trim()) return true;
                          const query = groupSearchQuery.toLowerCase();
                          return group.name?.toLowerCase().includes(query);
                        })
                        .map(group => (
                        <label key={group.id} className="teacher-checkbox-item">
                          <input
                            type="checkbox"
                            checked={uploadForm.selectedGroups.includes(group.id)}
                            onChange={(e) => {
                              if (e.target.checked) {
                                setUploadForm({
                                  ...uploadForm,
                                  selectedGroups: [...uploadForm.selectedGroups, group.id]
                                });
                              } else {
                                setUploadForm({
                                  ...uploadForm,
                                  selectedGroups: uploadForm.selectedGroups.filter(id => id !== group.id)
                                });
                              }
                            }}
                          />
                          <span>{group.name} ({group.student_count || 0} учеников)</span>
                        </label>
                      ))}
                      {groups.filter(g => !groupSearchQuery.trim() || g.name?.toLowerCase().includes(groupSearchQuery.toLowerCase())).length === 0 && (
                        <div className="teacher-privacy-empty">Группы не найдены</div>
                      )}
                    </div>
                  </div>
                )}

                {uploadForm.privacyType === 'students' && (
                  <div className="teacher-privacy-selector">
                    <p className="teacher-privacy-hint">Выберите учеников, которые смогут видеть это видео:</p>
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
                      {students
                        .filter(student => {
                          if (!studentSearchQuery.trim()) return true;
                          const query = studentSearchQuery.toLowerCase();
                          const fullName = `${student.first_name} ${student.last_name}`.toLowerCase();
                          return fullName.includes(query) || student.email?.toLowerCase().includes(query);
                        })
                        .map(student => (
                        <label key={student.id} className="teacher-checkbox-item">
                          <input
                            type="checkbox"
                            checked={uploadForm.selectedStudents.includes(student.id)}
                            onChange={(e) => {
                              if (e.target.checked) {
                                setUploadForm({
                                  ...uploadForm,
                                  selectedStudents: [...uploadForm.selectedStudents, student.id]
                                });
                              } else {
                                setUploadForm({
                                  ...uploadForm,
                                  selectedStudents: uploadForm.selectedStudents.filter(id => id !== student.id)
                                });
                              }
                            }}
                          />
                          <span>{student.first_name} {student.last_name} ({student.email})</span>
                        </label>
                      ))}
                      {students.filter(s => {
                        if (!studentSearchQuery.trim()) return true;
                        const query = studentSearchQuery.toLowerCase();
                        const fullName = `${s.first_name} ${s.last_name}`.toLowerCase();
                        return fullName.includes(query) || s.email?.toLowerCase().includes(query);
                      }).length === 0 && (
                        <div className="teacher-privacy-empty">Ученики не найдены</div>
                      )}
                    </div>
                  </div>
                )}
              </div>

              <div className="teacher-upload-actions">
                <button 
                  type="button" 
                  onClick={closeUploadModal}
                  className="teacher-cancel-btn"
                >
                  Отмена
                </button>
                <button 
                  type="submit" 
                  className="teacher-submit-btn"
                >
                  Загрузить
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}

export default TeacherRecordingsPage;
