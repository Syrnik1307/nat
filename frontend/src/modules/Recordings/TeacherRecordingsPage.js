import React, { useState, useEffect } from 'react';
import './TeacherRecordingsPage.css';
import api, { withScheduleApiBase } from '../../apiService';
import RecordingCard from './RecordingCard';
import RecordingPlayer from './RecordingPlayer';
import { ConfirmModal } from '../../shared/components';

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
  const [uploading, setUploading] = useState(false);
  const [uploadProgress, setUploadProgress] = useState(0);
  const [dragActive, setDragActive] = useState(false);
  const [confirmModal, setConfirmModal] = useState({
    isOpen: false,
    title: '',
    message: '',
    onConfirm: null,
    variant: 'warning',
    confirmText: 'Да',
    cancelText: 'Отмена'
  });
  const [alertModal, setAlertModal] = useState({
    isOpen: false,
    title: '',
    message: '',
    variant: 'info'
  });

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
      setLessons(Array.isArray(lessonsData) ? lessonsData : []);
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
          setAlertModal({
            isOpen: true,
            title: 'Успех',
            message: 'Запись успешно удалена',
            variant: 'info'
          });
        } catch (err) {
          console.error('Error deleting recording:', err);
          setAlertModal({
            isOpen: true,
            title: 'Ошибка',
            message: 'Не удалось удалить запись. Попробуйте позже.',
            variant: 'danger'
          });
        }
        setConfirmModal({ ...confirmModal, isOpen: false });
      }
    });
  };

  const handleUploadSubmit = async (e) => {
    e.preventDefault();
    
    if (!uploadForm.file) {
      setAlertModal({
        isOpen: true,
        title: 'Внимание',
        message: 'Пожалуйста, выберите видео файл',
        variant: 'warning'
      });
      return;
    }

    if (!uploadForm.lessonId && !uploadForm.title.trim()) {
      setAlertModal({
        isOpen: true,
        title: 'Внимание',
        message: 'Укажите название видео или выберите урок',
        variant: 'warning'
      });
      return;
    }

    if (uploadForm.privacyType === 'groups' && uploadForm.selectedGroups.length === 0) {
      setAlertModal({
        isOpen: true,
        title: 'Внимание',
        message: 'Выберите хотя бы одну группу',
        variant: 'warning'
      });
      return;
    }

    if (uploadForm.privacyType === 'students' && uploadForm.selectedStudents.length === 0) {
      setAlertModal({
        isOpen: true,
        title: 'Внимание',
        message: 'Выберите хотя бы одного ученика',
        variant: 'warning'
      });
      return;
    }

    try {
      setUploading(true);
      setUploadProgress(0);
      
      const formData = new FormData();
      formData.append('video', uploadForm.file);
      formData.append('privacy_type', uploadForm.privacyType);
      
      if (uploadForm.lessonId) {
        formData.append('lesson_id', uploadForm.lessonId);
      }
      
      if (uploadForm.title.trim()) {
        formData.append('title', uploadForm.title.trim());
      }
      
      if (uploadForm.privacyType === 'groups') {
        formData.append('allowed_groups', JSON.stringify(uploadForm.selectedGroups));
      } else if (uploadForm.privacyType === 'students') {
        formData.append('allowed_students', JSON.stringify(uploadForm.selectedStudents));
      }
      
      const endpoint = uploadForm.lessonId 
        ? `lessons/${uploadForm.lessonId}/upload_recording/`
        : 'lessons/upload_standalone_recording/';
      
      await api.post(
        endpoint,
        formData,
        {
          ...withScheduleApiBase(),
          headers: {
            'Content-Type': 'multipart/form-data'
          },
          onUploadProgress: (progressEvent) => {
            const percentCompleted = Math.round((progressEvent.loaded * 100) / progressEvent.total);
            setUploadProgress(percentCompleted);
          }
        }
      );
      
      setAlertModal({
        isOpen: true,
        title: 'Успех',
        message: 'Видео успешно загружено!',
        variant: 'info'
      });
      setShowUploadModal(false);
      setUploadForm({
        lessonId: '',
        title: '',
        file: null,
        privacyType: 'all',
        selectedGroups: [],
        selectedStudents: []
      });
      setUploadProgress(0);
      loadRecordings();
    } catch (err) {
      console.error('Error uploading video:', err);
      setAlertModal({
        isOpen: true,
        title: 'Ошибка',
        message: err.response?.data?.detail || 'Не удалось загрузить видео. Попробуйте позже.',
        variant: 'danger'
      });
    } finally {
      setUploading(false);
    }
  };

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
        setAlertModal({
          isOpen: true,
          title: 'Внимание',
          message: 'Пожалуйста, выберите видео файл',
          variant: 'warning'
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
        setAlertModal({
          isOpen: true,
          title: 'Внимание',
          message: 'Пожалуйста, выберите видео файл',
          variant: 'warning'
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
        >
          Загрузить видео
        </button>
      </div>

      {/* Статистика */}
      <div className="teacher-stats-grid">
        <div className="teacher-stat-card">
          <div className="teacher-stat-icon"></div>
          <div className="teacher-stat-info">
            <div className="teacher-stat-value">{stats.total}</div>
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
            <div className="teacher-stat-value">{stats.processing}</div>
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
      <div className="teacher-recordings-filters">
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
          <select
            value={groupFilter}
            onChange={(e) => setGroupFilter(e.target.value)}
            className="teacher-filter-select"
          >
            <option value="all">Все группы</option>
            {groups.map(group => (
              <option key={group.id} value={group.id}>{group.name}</option>
            ))}
          </select>
        </div>

        <div className="teacher-filter-group">
          <label>Статус:</label>
          <select
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value)}
            className="teacher-filter-select"
          >
            <option value="all">Все статусы</option>
            <option value="ready">Готово</option>
            <option value="processing">Обрабатывается</option>
            <option value="failed">Ошибка</option>
            <option value="archived">Архивировано</option>
          </select>
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
          <div className="teacher-recordings-grid">
            {filteredRecordings.map(recording => (
              <RecordingCard
                key={recording.id}
                recording={recording}
                onPlay={openPlayer}
                onDelete={handleDelete}
                showDelete={true}
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

      <ConfirmModal
        isOpen={alertModal.isOpen}
        onClose={() => setAlertModal({ ...alertModal, isOpen: false })}
        onConfirm={() => setAlertModal({ ...alertModal, isOpen: false })}
        title={alertModal.title}
        message={alertModal.message}
        variant={alertModal.variant}
        confirmText="OK"
        cancelText=""
      />

      {/* Плеер */}
      {selectedRecording && (
        <RecordingPlayer
          recording={selectedRecording}
          onClose={closePlayer}
        />
      )}

      {/* Модальное окно загрузки */}
      {showUploadModal && (
        <div className="teacher-upload-modal-overlay" onClick={() => setShowUploadModal(false)}>
          <div className="teacher-upload-modal" onClick={(e) => e.stopPropagation()}>
            <div className="teacher-upload-modal-header">
              <h2>Загрузить видео урока</h2>
              <button className="teacher-modal-close" onClick={() => setShowUploadModal(false)}>✕</button>
            </div>
            <form onSubmit={handleUploadSubmit} className="teacher-upload-form" noValidate>
              <div className="teacher-upload-field">
                <label>Привязать к уроку (необязательно)</label>
                <select
                  value={uploadForm.lessonId}
                  onChange={(e) => setUploadForm({...uploadForm, lessonId: e.target.value})}
                  className="teacher-upload-select"
                >
                  <option value="">📹 Самостоятельное видео</option>
                  {(() => {
                    const now = new Date();
                    const pastLessons = lessons.filter(l => new Date(l.start_time) < now);
                    const futureLessons = lessons.filter(l => new Date(l.start_time) >= now);
                    const formatDate = (dateStr) => {
                      const d = new Date(dateStr);
                      return d.toLocaleDateString('ru-RU', { day: '2-digit', month: '2-digit', year: 'numeric' });
                    };
                    return (
                      <>
                        {pastLessons.length > 0 && (
                          <optgroup label="📚 Прошедшие уроки">
                            {pastLessons.sort((a, b) => new Date(b.start_time) - new Date(a.start_time)).map(lesson => (
                              <option key={lesson.id} value={lesson.id}>
                                {lesson.title || lesson.subject} • {lesson.group_name} ({formatDate(lesson.start_time)})
                              </option>
                            ))}
                          </optgroup>
                        )}
                        {futureLessons.length > 0 && (
                          <optgroup label="📅 Предстоящие уроки">
                            {futureLessons.sort((a, b) => new Date(a.start_time) - new Date(b.start_time)).map(lesson => (
                              <option key={lesson.id} value={lesson.id}>
                                {lesson.title || lesson.subject} • {lesson.group_name} ({formatDate(lesson.start_time)})
                              </option>
                            ))}
                          </optgroup>
                        )}
                      </>
                    );
                  })()}
                </select>
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

              <div className="teacher-upload-field">
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
                    <div className="teacher-checkbox-list">
                      {groups.map(group => (
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
                    </div>
                  </div>
                )}

                {uploadForm.privacyType === 'students' && (
                  <div className="teacher-privacy-selector">
                    <p className="teacher-privacy-hint">Выберите учеников, которые смогут видеть это видео:</p>
                    <div className="teacher-checkbox-list">
                      {students.map(student => (
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
                    </div>
                  </div>
                )}
              </div>

              {uploading && (
                <div className="teacher-upload-progress">
                  <div className="teacher-progress-bar">
                    <div 
                      className="teacher-progress-fill"
                      style={{width: `${uploadProgress}%`}}
                    />
                  </div>
                  <p className="teacher-progress-text">{uploadProgress}%</p>
                </div>
              )}

              <div className="teacher-upload-actions">
                <button 
                  type="button" 
                  onClick={() => setShowUploadModal(false)}
                  className="teacher-cancel-btn"
                  disabled={uploading}
                >
                  Отмена
                </button>
                <button 
                  type="submit" 
                  className="teacher-submit-btn"
                  disabled={uploading}
                >
                  {uploading ? `Загрузка... ${uploadProgress}%` : 'Загрузить'}
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
