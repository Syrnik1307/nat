import React, { useEffect, useState, useRef } from 'react';
import { getTeacherStatsSummary, getLessons, getGroups, startQuickLesson, startLessonNew, updateLesson, endLesson } from '../apiService';
import { getCached, invalidateCache, TTL } from '../utils/dataCache';
import { Link } from 'react-router-dom';
import SubscriptionBanner from './SubscriptionBanner';
import TelegramReminderToast from './TelegramReminderToast';
import { Select, TeacherDashboardSkeleton } from '../shared/components';
import { useAuth } from '../auth';
import SupportWidget from './SupportWidget';
import { useDashboardTour } from '../hooks/useOnboarding';
import './TeacherHomePage.css';

/* =====================================================
   TEACHER HOME PAGE - Enterprise Indigo Theme
   Design: Professional SaaS, NO EMOJIS, SVG Icons Only
   ===================================================== */

// =====================================================
// SVG ICON COMPONENTS (Lucide-style)
// =====================================================

const IconVideo = ({ size = 24, className = '' }) => (
  <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className={className}>
    <path d="m22 8-6 4 6 4V8Z"/>
    <rect width="14" height="12" x="2" y="6" rx="2" ry="2"/>
  </svg>
);

const IconCalendar = ({ size = 24, className = '' }) => (
  <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className={className}>
    <rect width="18" height="18" x="3" y="4" rx="2" ry="2"/>
    <line x1="16" x2="16" y1="2" y2="6"/>
    <line x1="8" x2="8" y1="2" y2="6"/>
    <line x1="3" x2="21" y1="10" y2="10"/>
  </svg>
);

const IconUsers = ({ size = 24, className = '' }) => (
  <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className={className}>
    <path d="M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2"/>
    <circle cx="9" cy="7" r="4"/>
    <path d="M22 21v-2a4 4 0 0 0-3-3.87"/>
    <path d="M16 3.13a4 4 0 0 1 0 7.75"/>
  </svg>
);

const IconBarChart = ({ size = 24, className = '' }) => (
  <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className={className}>
    <line x1="12" x2="12" y1="20" y2="10"/>
    <line x1="18" x2="18" y1="20" y2="4"/>
    <line x1="6" x2="6" y1="20" y2="16"/>
  </svg>
);

const IconTarget = ({ size = 24, className = '' }) => (
  <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className={className}>
    <circle cx="12" cy="12" r="10"/>
    <circle cx="12" cy="12" r="6"/>
    <circle cx="12" cy="12" r="2"/>
  </svg>
);

const IconClock = ({ size = 24, className = '' }) => (
  <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className={className}>
    <circle cx="12" cy="12" r="10"/>
    <polyline points="12,6 12,12 16,14"/>
  </svg>
);

const IconUser = ({ size = 24, className = '' }) => (
  <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className={className}>
    <path d="M19 21v-2a4 4 0 0 0-4-4H9a4 4 0 0 0-4 4v2"/>
    <circle cx="12" cy="7" r="4"/>
  </svg>
);

const IconDisc = ({ size = 24, className = '' }) => (
  <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className={className}>
    <circle cx="12" cy="12" r="10"/>
    <circle cx="12" cy="12" r="2"/>
  </svg>
);

const IconTrendingUp = ({ size = 24, className = '' }) => (
  <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className={className}>
    <polyline points="23,6 13.5,15.5 8.5,10.5 1,18"/>
    <polyline points="17,6 23,6 23,12"/>
  </svg>
);

const IconChevronRight = ({ size = 24, className = '' }) => (
  <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className={className}>
    <path d="m9 18 6-6-6-6"/>
  </svg>
);

const IconPlay = ({ size = 24, className = '' }) => (
  <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className={className}>
    <polygon points="5,3 19,12 5,21 5,3"/>
  </svg>
);

const IconPencil = ({ size = 24, className = '' }) => (
  <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className={className}>
    <path d="M17 3a2.85 2.83 0 1 1 4 4L7.5 20.5 2 22l1.5-5.5Z"/>
    <path d="m15 5 4 4"/>
  </svg>
);

const IconCheck = ({ size = 24, className = '' }) => (
  <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className={className}>
    <polyline points="20 6 9 17 4 12"/>
  </svg>
);

const IconX = ({ size = 24, className = '' }) => (
  <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className={className}>
    <line x1="18" y1="6" x2="6" y2="18"/>
    <line x1="6" y1="6" x2="18" y2="18"/>
  </svg>
);

const IconBook = ({ size = 24, className = '' }) => (
  <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className={className}>
    <path d="M4 19.5v-15A2.5 2.5 0 0 1 6.5 2H20v20H6.5a2.5 2.5 0 0 1 0-5H20"/>
  </svg>
);

const IconFolder = ({ size = 24, className = '' }) => (
  <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className={className}>
    <path d="M22 19a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h5l2 3h9a2 2 0 0 1 2 2z"/>
  </svg>
);

const IconGraduationCap = ({ size = 24, className = '' }) => (
  <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className={className}>
    <path d="M22 10v6M2 10l10-5 10 5-10 5z"/>
    <path d="M6 12v5c3 3 9 3 12 0v-5"/>
  </svg>
);

const IconBeaker = ({ size = 24, className = '' }) => (
  <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className={className}>
    <path d="M4.5 3h15M6 3v15.4a2 2 0 0 0 .7 1.5l4.6 4.3a2 2 0 0 0 2.8 0l4.6-4.3a2 2 0 0 0 .7-1.5V3"/>
    <path d="M6 14h12"/>
  </svg>
);

const IconCalculator = ({ size = 24, className = '' }) => (
  <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className={className}>
    <rect width="16" height="20" x="4" y="2" rx="2"/>
    <line x1="8" x2="16" y1="6" y2="6"/>
    <line x1="16" x2="16" y1="14" y2="14"/>
    <path d="M16 10h.01M12 10h.01M8 10h.01M12 14h.01M8 14h.01M12 18h.01M8 18h.01"/>
  </svg>
);

const IconLanguages = ({ size = 24, className = '' }) => (
  <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className={className}>
    <path d="m5 8 6 6M4 14l6-6 2-3M2 5h12M7 2h1M22 22l-5-10-5 10M14 18h6"/>
  </svg>
);

const IconPalette = ({ size = 24, className = '' }) => (
  <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className={className}>
    <circle cx="13.5" cy="6.5" r=".5" fill="currentColor"/>
    <circle cx="17.5" cy="10.5" r=".5" fill="currentColor"/>
    <circle cx="8.5" cy="7.5" r=".5" fill="currentColor"/>
    <circle cx="6.5" cy="12.5" r=".5" fill="currentColor"/>
    <path d="M12 2C6.5 2 2 6.5 2 12s4.5 10 10 10c.926 0 1.648-.746 1.648-1.688 0-.437-.18-.835-.437-1.125-.29-.289-.438-.652-.438-1.125a1.64 1.64 0 0 1 1.668-1.668h1.996c3.051 0 5.555-2.503 5.555-5.554C21.965 6.012 17.461 2 12 2z"/>
  </svg>
);

const IconMusic = ({ size = 24, className = '' }) => (
  <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className={className}>
    <path d="M9 18V5l12-2v13"/>
    <circle cx="6" cy="18" r="3"/>
    <circle cx="18" cy="16" r="3"/>
  </svg>
);

const IconAtom = ({ size = 24, className = '' }) => (
  <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className={className}>
    <circle cx="12" cy="12" r="1"/>
    <path d="M20.2 20.2c2.04-2.03.02-7.36-4.5-11.9-4.54-4.52-9.87-6.54-11.9-4.5-2.04 2.03-.02 7.36 4.5 11.9 4.54 4.52 9.87 6.54 11.9 4.5Z"/>
    <path d="M15.7 15.7c4.52-4.54 6.54-9.87 4.5-11.9-2.03-2.04-7.36-.02-11.9 4.5-4.52 4.54-6.54 9.87-4.5 11.9 2.03 2.04 7.36.02 11.9-4.5Z"/>
  </svg>
);

const IconCode = ({ size = 24, className = '' }) => (
  <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className={className}>
    <polyline points="16 18 22 12 16 6"/>
    <polyline points="8 6 2 12 8 18"/>
  </svg>
);

// =====================================================
// MAIN COMPONENT
// =====================================================

const TeacherHomePage = () => {
  const { user } = useAuth();
  
  // Автозапуск онбординг-тура при первом входе
  useDashboardTour('teacher', user?.id);
  
  const [stats, setStats] = useState(null);
  const [lessons, setLessons] = useState([]);
  const [groups, setGroups] = useState([]);
  const [loading, setLoading] = useState(true);
  const [starting, setStarting] = useState(false);
  
  // Modal state for quick lesson start
  const [showStartModal, setShowStartModal] = useState(false);
  const [recordLesson, setRecordLesson] = useState(true);
  const [selectedGroupId, setSelectedGroupId] = useState('');
  const [startError, setStartError] = useState(null);
  const abortRef = useRef(null);
  
  // Modal state for scheduled lesson start
  const [showLessonStartModal, setShowLessonStartModal] = useState(false);
  const [selectedLesson, setSelectedLesson] = useState(null);
  const [lessonRecordEnabled, setLessonRecordEnabled] = useState(false);
  const [recordingTitle, setRecordingTitle] = useState('');
  const [lessonStartError, setLessonStartError] = useState(null);
  const [lessonStarting, setLessonStarting] = useState(false);
  
  // Modal state for platform selection
  const [showPlatformModal, setShowPlatformModal] = useState(false);
  const [selectedPlatform, setSelectedPlatform] = useState('zoom'); // 'zoom' | 'google_meet'
  const [platformModalContext, setPlatformModalContext] = useState(null); // 'quick' | 'scheduled'
  const [quickLessonTitle, setQuickLessonTitle] = useState(''); // Название быстрого урока
  
  // State for editing lesson topic inline
  const [editingTopicLessonId, setEditingTopicLessonId] = useState(null);
  const [editingTopicValue, setEditingTopicValue] = useState('');
  const [savingTopic, setSavingTopic] = useState(false);
  const [endingLessonId, setEndingLessonId] = useState(null);
  
  // Determine available platforms from user profile
  const zoomConnected = user?.zoom_connected || false;
  const googleMeetConnected = user?.google_meet_connected || false;
  const availablePlatforms = [];
  if (zoomConnected) availablePlatforms.push('zoom');
  if (googleMeetConnected) availablePlatforms.push('google_meet');

  useEffect(() => {
    const controller = new AbortController();
    abortRef.current = controller;

    const loadData = async () => {
      try {
        const now = new Date();
        const yyyy = String(now.getFullYear());
        const mm = String(now.getMonth() + 1).padStart(2, '0');
        const dd = String(now.getDate()).padStart(2, '0');
        const today = `${yyyy}-${mm}-${dd}`;
        
        const [statsData, lessonsData, groupsData] = await Promise.all([
          getCached('teacher:stats', async () => {
            const res = await getTeacherStatsSummary();
            return res.data;
          }, TTL.LONG),
          getCached(`teacher:lessons:${today}`, async () => {
            const res = await getLessons({ date: today, include_recurring: true, exclude_ended: true });
            return Array.isArray(res.data) ? res.data : res.data.results || [];
          }, TTL.SHORT),
          getCached('teacher:groups', async () => {
            const res = await getGroups();
            return Array.isArray(res.data) ? res.data : res.data.results || [];
          }, TTL.MEDIUM),
        ]);
        
        if (!controller.signal.aborted) {
          setStats(statsData);
          setLessons(lessonsData);
          setGroups(groupsData);
        }
      } catch (err) {
        if (!controller.signal.aborted) {
          console.error('Failed to load dashboard data:', err);
        }
      } finally {
        if (!controller.signal.aborted) {
          setLoading(false);
        }
      }
    };
    loadData();
    return () => controller.abort();
  }, []);

  // Determine if we need to show platform selection modal
  const needsPlatformSelection = zoomConnected && googleMeetConnected;
  
  // Get the only available platform if just one is connected
  const getSinglePlatform = () => {
    if (zoomConnected && !googleMeetConnected) return 'zoom';
    if (googleMeetConnected && !zoomConnected) return 'google_meet';
    return null;
  };

  const openStartModal = () => {
    setStartError(null);
    setRecordLesson(true);
    setSelectedGroupId(groups.length > 0 ? groups[0].id : '');
    
    // If both platforms connected, show platform selection first
    if (needsPlatformSelection) {
      setSelectedPlatform('zoom'); // Default to Zoom
      setPlatformModalContext('quick');
      setShowPlatformModal(true);
    } else {
      // Use the single available platform or default to zoom (fallback for pool)
      setSelectedPlatform(getSinglePlatform() || 'zoom');
      setShowStartModal(true);
    }
  };
  
  // Handle platform selection confirmation
  const handlePlatformConfirm = () => {
    setShowPlatformModal(false);
    if (platformModalContext === 'quick') {
      setShowStartModal(true);
    } else if (platformModalContext === 'scheduled') {
      setShowLessonStartModal(true);
    }
  };

  const handleQuickStart = async () => {
    if (starting) return;
    setStarting(true);
    setStartError(null);
    try {
      // Преобразуем 'zoom' → 'zoom_pool' для бэкенда
      const providerForBackend = selectedPlatform === 'zoom' ? 'zoom_pool' : selectedPlatform;
      const recordForBackend = providerForBackend === 'google_meet' ? false : recordLesson;
      
      const res = await startQuickLesson({
        record_lesson: recordForBackend,
        group_id: selectedGroupId || undefined,
        provider: providerForBackend,
        title: quickLessonTitle.trim() || undefined,
      });
      
      // Открываем ссылку СРАЗУ после получения ответа (как было раньше)
      if (res.data?.zoom_start_url) {
        // OPTIMISTIC UPDATE: добавляем урок в список сразу
        if (res.data?.id) {
          const newLesson = {
            id: res.data.id,
            title: quickLessonTitle.trim() || 'Быстрый урок',
            status: 'in_progress',
            zoom_start_url: res.data.zoom_start_url,
            group_name: groups.find(g => g.id === selectedGroupId)?.name,
            started_at: new Date().toISOString(),
          };
          setLessons(prev => [newLesson, ...prev]);
        }
        window.open(res.data.zoom_start_url, '_blank');
        setShowStartModal(false);
        // Инвалидируем кеш уроков - новый урок создан
        invalidateCache('teacher:lessons');
      } else if (res.data?.meet_link) {
        // OPTIMISTIC UPDATE для Google Meet
        if (res.data?.id) {
          const newLesson = {
            id: res.data.id,
            title: quickLessonTitle.trim() || 'Быстрый урок',
            status: 'in_progress',
            meet_link: res.data.meet_link,
            group_name: groups.find(g => g.id === selectedGroupId)?.name,
            started_at: new Date().toISOString(),
          };
          setLessons(prev => [newLesson, ...prev]);
        }
        window.open(res.data.meet_link, '_blank');
        setShowStartModal(false);
        invalidateCache('teacher:lessons');
      } else if (res.data?.start_url) {
        window.open(res.data.start_url, '_blank');
        setShowStartModal(false);
        invalidateCache('teacher:lessons');
      }
    } catch (err) {
      setStartError(err.response?.data?.detail || 'Ошибка запуска урока');
    } finally {
      setStarting(false);
    }
  };

  // Открыть модальное окно для запуска конкретного урока
  const openLessonStartModal = (lesson) => {
    setSelectedLesson(lesson);
    setLessonRecordEnabled(lesson.record_lesson || false);
    setRecordingTitle(lesson.display_name || lesson.title || lesson.group_name || '');
    setLessonStartError(null);
    
    // If both platforms connected, show platform selection first
    if (needsPlatformSelection) {
      setSelectedPlatform('zoom'); // Default to Zoom
      setPlatformModalContext('scheduled');
      setShowPlatformModal(true);
    } else {
      // Use the single available platform or default to zoom
      setSelectedPlatform(getSinglePlatform() || 'zoom');
      setShowLessonStartModal(true);
    }
  };
  
  // Начать редактирование темы урока
  const startEditTopic = (lesson) => {
    setEditingTopicLessonId(lesson.id);
    setEditingTopicValue(lesson.title || '');
  };
  
  // Сохранить тему урока
  const saveTopicEdit = async (lessonId) => {
    if (savingTopic) return;
    setSavingTopic(true);
    try {
      await updateLesson(lessonId, { title: editingTopicValue });
      // Обновляем локально
      setLessons(prev => prev.map(l => 
        l.id === lessonId 
          ? { ...l, title: editingTopicValue, display_name: editingTopicValue || l.group_name }
          : l
      ));
      setEditingTopicLessonId(null);
      setEditingTopicValue('');
    } catch (err) {
      console.error('Failed to save topic:', err);
    } finally {
      setSavingTopic(false);
    }
  };
  
  // Отменить редактирование темы
  const cancelEditTopic = () => {
    setEditingTopicLessonId(null);
    setEditingTopicValue('');
  };

  // Завершить урок
  const handleEndLesson = async (lessonId) => {
    if (endingLessonId) return;
    setEndingLessonId(lessonId);
    try {
      await endLesson(lessonId);
      // OPTIMISTIC UPDATE: убираем урок из списка (он теперь в архиве)
      setLessons(prev => prev.filter(l => l.id !== lessonId));
      // Инвалидируем кеш статистики и уроков
      invalidateCache('teacher:stats');
      invalidateCache('teacher:lessons');
    } catch (err) {
      console.error('Failed to end lesson:', err);
      // Если ошибка - перезагружаем уроки чтобы восстановить состояние
      invalidateCache('teacher:lessons');
    } finally {
      setEndingLessonId(null);
    }
  };

  // Запустить конкретный урок
  const handleStartScheduledLesson = async () => {
    if (lessonStarting || !selectedLesson) return;
    setLessonStarting(true);
    setLessonStartError(null);
    
    try {
      const providerForBackend = selectedPlatform === 'zoom' ? 'zoom_pool' : selectedPlatform;
      const recordForBackend = providerForBackend === 'google_meet' ? false : lessonRecordEnabled;

      // Если изменилось название или флаг записи - сначала обновляем урок
      const needsUpdate = 
        (recordForBackend !== selectedLesson.record_lesson) ||
        (recordingTitle && recordingTitle !== selectedLesson.title);
      
      if (needsUpdate) {
        await updateLesson(selectedLesson.id, {
          record_lesson: recordForBackend,
          title: recordingTitle || selectedLesson.title,
        });
      }
      
      const response = await startLessonNew(selectedLesson.id, {
        record_lesson: recordForBackend,
        force_new_meeting: needsUpdate && recordForBackend && Boolean(selectedLesson.zoom_meeting_id),
        provider: providerForBackend,
      });

      // Открываем ссылку СРАЗУ после получения ответа (как было раньше)
      if (response.data?.zoom_start_url) {
        window.open(response.data.zoom_start_url, '_blank');
        setShowLessonStartModal(false);
        // Обновляем список уроков
        setLessons(prev => prev.map(l => 
          l.id === selectedLesson.id 
            ? { ...l, zoom_start_url: response.data.zoom_start_url, zoom_join_url: response.data.zoom_join_url }
            : l
        ));
      } else if (response.data?.meet_link) {
        window.open(response.data.meet_link, '_blank');
        setShowLessonStartModal(false);
      } else if (response.data?.start_url) {
        window.open(response.data.start_url, '_blank');
        setShowLessonStartModal(false);
      }
    } catch (err) {
      if (err.response?.status === 503) {
        setLessonStartError('Все Zoom аккаунты заняты. Попробуйте позже.');
      } else if (err.response?.status === 400 || err.response?.status === 403) {
        setLessonStartError(err.response.data?.detail || 'Ошибка создания встречи');
      } else if (err.response?.status === 404) {
        setLessonStartError('Урок не найден или API endpoint недоступен');
      } else {
        setLessonStartError(err.response?.data?.detail || err.message || 'Не удалось начать занятие.');
      }
    } finally {
      setLessonStarting(false);
    }
  };

  const formatTime = (dateStr) => {
    const d = new Date(dateStr);
    return d.toLocaleTimeString('ru-RU', { hour: '2-digit', minute: '2-digit' });
  };

  const formatDate = (dateStr) => {
    const d = new Date(dateStr);
    return d.toLocaleDateString('ru-RU', { day: 'numeric', month: 'short' });
  };

  // Generate consistent color index for group based on name
  const getGroupColorIndex = (name) => {
    const hash = name.split('').reduce((acc, char) => acc + char.charCodeAt(0), 0);
    return hash % 6;
  };

  // Smart icon selection based on group name
  const getGroupIcon = (name) => {
    const lowerName = name.toLowerCase();
    
    // Математика
    if (lowerName.includes('математ') || lowerName.includes('алгебр') || lowerName.includes('геометр')) {
      return <IconCalculator size={28} className="group-cover-icon" />;
    }
    // Физика, Химия, Биология
    if (lowerName.includes('физик') || lowerName.includes('хими') || lowerName.includes('биолог')) {
      return <IconBeaker size={28} className="group-cover-icon" />;
    }
    // Информатика, Программирование
    if (lowerName.includes('информат') || lowerName.includes('программ') || lowerName.includes('it') || lowerName.includes('код')) {
      return <IconCode size={28} className="group-cover-icon" />;
    }
    // Языки
    if (lowerName.includes('язык') || lowerName.includes('english') || lowerName.includes('русск') || lowerName.includes('литерат')) {
      return <IconLanguages size={28} className="group-cover-icon" />;
    }
    // Музыка
    if (lowerName.includes('музык') || lowerName.includes('вокал') || lowerName.includes('гитар')) {
      return <IconMusic size={28} className="group-cover-icon" />;
    }
    // Искусство, Рисование
    if (lowerName.includes('рисован') || lowerName.includes('искусств') || lowerName.includes('живопис')) {
      return <IconPalette size={28} className="group-cover-icon" />;
    }
    // Физика (атом)
    if (lowerName.includes('атом') || lowerName.includes('ядерн')) {
      return <IconAtom size={28} className="group-cover-icon" />;
    }
    
    // По умолчанию - выпускной колпак
    return <IconGraduationCap size={28} className="group-cover-icon" />;
  };

  // Clean group name from emojis and decorative symbols
  const cleanGroupName = (name) => {
    if (!name) return '';
    // Keep only letters, numbers, whitespace and basic punctuation (Unicode aware)
    return name
      .replace(/[^\p{L}\p{N}\s.,!?()-]/gu, '')
      .replace(/\s+/g, ' ')
      .trim();
  };

  if (loading) {
    return (
      <div className="dashboard-container">
        <TelegramReminderToast />
        <TeacherDashboardSkeleton />
      </div>
    );
  }

  return (
    <div className="dashboard-container">

      {/* Онбординг тур - автозапуск при первом входе */}
      <TelegramReminderToast />
      
      {/* Subscription Banner */}
      <SubscriptionBanner />

      {/* Platform Selection Modal */}
      {showPlatformModal && (
        <>
          <div className="modal-overlay" onClick={() => setShowPlatformModal(false)} />
          <div className="platform-modal">
            <h3 className="platform-modal-title">Выберите платформу</h3>
            <p className="platform-modal-subtitle">Где вы хотите провести урок?</p>
            
            {/* Lesson Title Input - only for quick start */}
            {platformModalContext === 'quick' && (
              <div className="platform-modal-field">
                <label className="platform-modal-label">Название урока</label>
                <input
                  type="text"
                  className="platform-modal-input"
                  value={quickLessonTitle}
                  onChange={(e) => setQuickLessonTitle(e.target.value)}
                  placeholder="Например: Алгебра — квадратные уравнения"
                />
                <span className="platform-modal-hint">Это название будет отображаться в записи урока у учеников</span>
              </div>
            )}
            
            <div className="platform-options">
              <button
                type="button"
                className={`platform-option ${selectedPlatform === 'zoom' ? 'selected' : ''}`}
                onClick={() => {
                  setSelectedPlatform('zoom');
                }}
              >
                <div className="platform-option-icon zoom-icon">
                  <svg width="28" height="28" viewBox="0 0 24 24" fill="currentColor">
                    <path d="M4.5 4.5C3.12 4.5 2 5.62 2 7v10c0 1.38 1.12 2.5 2.5 2.5h11c1.38 0 2.5-1.12 2.5-2.5v-3.35l4 3V7.85l-4 3V7c0-1.38-1.12-2.5-2.5-2.5h-11z"/>
                  </svg>
                </div>
                <div className="platform-option-info">
                  <span className="platform-option-name">Zoom</span>
                  <span className="platform-option-desc">Видеоконференция через Zoom</span>
                </div>
                {selectedPlatform === 'zoom' && (
                  <div className="platform-option-check">
                    <IconCheck size={18} />
                  </div>
                )}
              </button>
              
              <button
                type="button"
                className={`platform-option ${selectedPlatform === 'google_meet' ? 'selected' : ''}`}
                onClick={() => {
                  setSelectedPlatform('google_meet');
                  if (platformModalContext === 'quick') {
                    setRecordLesson(false);
                  } else if (platformModalContext === 'scheduled') {
                    setLessonRecordEnabled(false);
                  }
                }}
              >
                <div className="platform-option-icon meet-icon">
                  <svg width="28" height="28" viewBox="0 0 24 24" fill="currentColor">
                    <path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm-2 15l-5-5 1.41-1.41L10 14.17l7.59-7.59L19 8l-9 9z"/>
                  </svg>
                </div>
                <div className="platform-option-info">
                  <span className="platform-option-name">Google Meet</span>
                  <span className="platform-option-desc">Видеоконференция через Google</span>
                </div>
                {selectedPlatform === 'google_meet' && (
                  <div className="platform-option-check">
                    <IconCheck size={18} />
                  </div>
                )}
              </button>
            </div>
            
            <div className="platform-modal-actions">
              <button
                className="platform-modal-btn primary"
                onClick={handlePlatformConfirm}
              >
                Продолжить
              </button>
              <button
                className="platform-modal-btn secondary"
                onClick={() => setShowPlatformModal(false)}
              >
                Отмена
              </button>
            </div>
          </div>
        </>
      )}

      {/* Start Lesson Modal */}
      {showStartModal && (
        <>
          <div className="modal-overlay" onClick={() => setShowStartModal(false)} />
          <div className="start-modal">
            <h3 className="start-modal-title">
              <IconVideo size={20} />
              <span>Настройки урока</span>
            </h3>

            {/* Group Selection */}
            <div className="start-modal-field">
              <label className="start-modal-label">Группа</label>
              <Select
                value={selectedGroupId}
                onChange={(e) => setSelectedGroupId(e.target.value)}
                options={[
                  { value: '', label: 'Без группы (индивидуальный)' },
                  ...groups.map((g) => ({ value: String(g.id), label: g.name }))
                ]}
                placeholder="Без группы (индивидуальный)"
              />
            </div>

            {/* Record Option (Zoom only) */}
            {selectedPlatform !== 'google_meet' ? (
              <>
                <label className={`start-modal-checkbox ${recordLesson ? 'checked' : ''}`}>
                  <input
                    type="checkbox"
                    checked={recordLesson}
                    onChange={(e) => setRecordLesson(e.target.checked)}
                  />
                  <IconDisc size={18} />
                  <span>Записывать урок</span>
                </label>

                {recordLesson && (
                  <div className="start-modal-hint">
                    <IconDisc size={14} />
                    <span>Запись будет доступна в разделе «Записи» после окончания</span>
                  </div>
                )}
              </>
            ) : (
              <div className="start-modal-hint" style={{ color: '#92400e' }}>
                <span>Запись доступна только для Zoom. Для Google Meet используйте запись в Google Meet вручную.</span>
              </div>
            )}

            {startError && (
              <div className="start-modal-error">{startError}</div>
            )}

            {starting && (
              <div className="start-modal-hint" style={{ color: '#0369a1', backgroundColor: '#f0f9ff', border: '1px solid #bae6fd' }}>
                <span>Подключение к Zoom... Это может занять до 30 секунд</span>
              </div>
            )}

            <div className="start-modal-actions">
              <button
                className="start-modal-btn primary"
                onClick={handleQuickStart}
                disabled={starting}
              >
                <IconPlay size={16} />
                <span>{starting ? 'Подключение...' : 'Начать урок'}</span>
              </button>
              <button
                className="start-modal-btn secondary"
                onClick={() => setShowStartModal(false)}
              >
                Отмена
              </button>
            </div>
          </div>
        </>
      )}

      {/* Scheduled Lesson Start Modal */}
      {showLessonStartModal && selectedLesson && (
        <>
          <div className="modal-overlay" onClick={() => setShowLessonStartModal(false)} />
          <div className="start-modal">
            <h3 className="start-modal-title">
              <IconVideo size={20} />
              <span>Запуск занятия</span>
            </h3>

            <div className="start-modal-lesson-info">
              <div className="start-modal-lesson-name">{selectedLesson.display_name || selectedLesson.group_name || 'Урок'}</div>
              <div className="start-modal-lesson-group">{selectedLesson.group_name || `Группа #${selectedLesson.group}`}</div>
              {selectedLesson.title && (
                <div className="start-modal-lesson-topic">Тема: {selectedLesson.title}</div>
              )}
            </div>

            {/* Record Option (Zoom only) */}
            {selectedPlatform !== 'google_meet' ? (
              <label className={`start-modal-checkbox ${lessonRecordEnabled ? 'checked' : ''}`}>
                <input
                  type="checkbox"
                  checked={lessonRecordEnabled}
                  onChange={(e) => setLessonRecordEnabled(e.target.checked)}
                />
                <IconDisc size={18} />
                <span>Записывать урок</span>
              </label>
            ) : (
              <div className="start-modal-hint" style={{ color: '#92400e' }}>
                <span>Запись доступна только для Zoom. Для Google Meet используйте запись в Google Meet вручную.</span>
              </div>
            )}

            {lessonRecordEnabled && (
              <>
                <div className="start-modal-field">
                  <label className="start-modal-label">Название записи</label>
                  <input
                    type="text"
                    className="start-modal-input"
                    placeholder="Введите название для записи"
                    value={recordingTitle}
                    onChange={(e) => setRecordingTitle(e.target.value)}
                  />
                </div>
                <label className="start-modal-use-topic-checkbox">
                  <input
                    type="checkbox"
                    checked={recordingTitle === (selectedLesson.display_name || selectedLesson.group_name)}
                    onChange={(e) => {
                      if (e.target.checked) {
                        setRecordingTitle(selectedLesson.display_name || selectedLesson.group_name || '');
                      }
                    }}
                  />
                  <span>Использовать название урока</span>
                </label>
                <div className="start-modal-hint">
                  <IconDisc size={14} />
                  <span>Запись сохранится с указанным названием</span>
                </div>
              </>
            )}

            {lessonStartError && (
              <div className="start-modal-error">{lessonStartError}</div>
            )}

            {lessonStarting && (
              <div className="start-modal-hint" style={{ color: '#0369a1', backgroundColor: '#f0f9ff', border: '1px solid #bae6fd' }}>
                <span>Подключение к Zoom... Это может занять до 30 секунд</span>
              </div>
            )}

            <div className="start-modal-actions">
              <button
                className="start-modal-btn primary"
                onClick={handleStartScheduledLesson}
                disabled={lessonStarting}
              >
                <IconPlay size={16} />
                <span>{lessonStarting ? 'Подключение...' : 'Начать занятие'}</span>
              </button>
              <button
                className="start-modal-btn secondary"
                onClick={() => setShowLessonStartModal(false)}
              >
                Отмена
              </button>
            </div>
          </div>
        </>
      )}

      {/* Main Grid - No page title, starts directly with content */}
      <div className="dashboard-grid">
        {/* LEFT COLUMN */}
        <div className="dashboard-left">
          {/* Hero: Start Lesson */}
          <div className="hero-card" data-tour="teacher-quick-start">
            <div className="hero-glow"></div>
            <div className="hero-pattern">
              <svg width="100%" height="100%" xmlns="http://www.w3.org/2000/svg">
                <defs>
                  <pattern id="hero-dots" x="0" y="0" width="20" height="20" patternUnits="userSpaceOnUse">
                    <circle cx="2" cy="2" r="1" fill="rgba(255,255,255,0.1)"/>
                  </pattern>
                </defs>
                <rect width="100%" height="100%" fill="url(#hero-dots)"/>
              </svg>
            </div>
            <div className="hero-content">
              <div className="hero-icon-wrapper">
                <IconVideo size={32} className="hero-icon" />
              </div>
              <h2 className="hero-title">Начать урок</h2>
              <p className="hero-subtitle">Мгновенный запуск видеоконференции для вашего следующего занятия</p>
              <button
                className="hero-button"
                onClick={openStartModal}
                disabled={starting}
              >
                <IconPlay size={18} />
                <span>Запустить урок</span>
              </button>
            </div>
          </div>

          {/* Schedule Section */}
          <div className="section-card" data-tour="teacher-schedule">
            <div className="section-header">
              <div className="section-title-group">
                <div className="section-icon-wrapper">
                  <IconCalendar size={18} />
                </div>
                <h3 className="section-title">Занятия на сегодня</h3>
              </div>
              <Link to="/recurring-lessons/manage" className="section-link">
                Все занятия
                <IconChevronRight size={16} />
              </Link>
            </div>
            <div className="schedule-list">
              {lessons.length > 0 ? (
                lessons.map((lesson) => {
                  const isEditing = editingTopicLessonId === lesson.id;
                  const isVirtualLesson = typeof lesson.id !== 'number'; // recurring virtual lessons have string IDs
                  
                  return (
                    <div key={lesson.id} className="schedule-item">
                      <div className="schedule-time-badge">
                        <span className="schedule-date">{formatDate(lesson.start_time)}</span>
                        <span className="schedule-hour">{formatTime(lesson.start_time)}</span>
                      </div>
                      <div className="schedule-info">
                        <div className="schedule-group-name">{lesson.group_name || `Группа #${lesson.group}`}</div>
                        <div className="schedule-topic-row">
                          {isEditing ? (
                            <div className="schedule-topic-edit">
                              <input
                                type="text"
                                className="schedule-topic-input"
                                value={editingTopicValue}
                                onChange={(e) => setEditingTopicValue(e.target.value)}
                                placeholder="Введите тему урока"
                                autoFocus
                                onKeyDown={(e) => {
                                  if (e.key === 'Enter') saveTopicEdit(lesson.id);
                                  if (e.key === 'Escape') cancelEditTopic();
                                }}
                              />
                              <button
                                className="schedule-topic-btn save"
                                onClick={() => saveTopicEdit(lesson.id)}
                                disabled={savingTopic}
                                title="Сохранить"
                              >
                                <IconCheck size={14} />
                              </button>
                              <button
                                className="schedule-topic-btn cancel"
                                onClick={cancelEditTopic}
                                title="Отмена"
                              >
                                <IconX size={14} />
                              </button>
                            </div>
                          ) : (
                            <>
                              <span className="schedule-topic">
                                {lesson.title ? (
                                  <>Тема: {lesson.title}</>
                                ) : (
                                  <span className="schedule-topic-empty">Тема не указана</span>
                                )}
                              </span>
                              {!isVirtualLesson && (
                                <button
                                  className="schedule-topic-edit-btn"
                                  onClick={() => startEditTopic(lesson)}
                                  title="Указать тему"
                                >
                                  <IconPencil size={12} />
                                </button>
                              )}
                            </>
                          )}
                        </div>
                      </div>
                      <div className="schedule-actions">
                        {lesson.ended_at ? (
                          <span className="schedule-ended-label">
                            <IconCheck size={14} />
                            <span>Закончен</span>
                          </span>
                        ) : (lesson.zoom_start_url || lesson.google_meet_link) ? (
                          <>
                            <a 
                              href={lesson.zoom_start_url || lesson.google_meet_link} 
                              target="_blank" 
                              rel="noopener noreferrer"
                              className="schedule-start-btn active"
                            >
                              <IconVideo size={14} />
                              <span>Продолжить</span>
                            </a>
                            <button
                              className="schedule-end-btn"
                              onClick={() => handleEndLesson(lesson.id)}
                              disabled={endingLessonId === lesson.id}
                              title="Закончить урок"
                            >
                              {endingLessonId === lesson.id ? '...' : <IconCheck size={14} />}
                            </button>
                          </>
                        ) : (
                          <button
                            className="schedule-start-btn"
                            onClick={() => openLessonStartModal(lesson)}
                          >
                            <IconPlay size={14} />
                            <span>Начать</span>
                          </button>
                        )}
                      </div>
                    </div>
                  );
                })
              ) : (
                <div className="empty-state">
                  <IconCalendar size={32} className="empty-icon" />
                  <p>Нет занятий на сегодня</p>
                </div>
              )}
            </div>
          </div>

          {/* Students & Groups Section */}
          <div className="section-card students-section" data-tour="teacher-students">
            <div className="section-header">
              <div className="section-title-group">
                <div className="section-icon-wrapper">
                  <IconUsers size={18} />
                </div>
                <h3 className="section-title">Ученики</h3>
                <span className="section-counter">{groups.length} групп</span>
              </div>
              <Link to="/groups/manage" className="section-link">
                Управление
                <IconChevronRight size={16} />
              </Link>
            </div>
            <div className="students-grid">
              {groups.length > 0 ? (
                groups.map((group) => {
                  const colorIndex = getGroupColorIndex(group.name);
                  const cleanName = cleanGroupName(group.name);
                  const studentCount = group.students?.length || 0;
                  return (
                    <Link
                      key={group.id}
                      to={`/attendance/${group.id}`}
                      className={`student-group-card color-${colorIndex}`}
                    >
                      <div className="student-group-icon">
                        {getGroupIcon(group.name)}
                      </div>
                      <div className="student-group-content">
                        <h4 className="student-group-name">{cleanName}</h4>
                        <div className="student-group-meta">
                          <span className="student-count-badge">
                            <IconUsers size={12} />
                            {studentCount} {studentCount === 1 ? 'ученик' : studentCount >= 2 && studentCount <= 4 ? 'ученика' : 'учеников'}
                          </span>
                        </div>
                      </div>
                      <div className="student-group-arrow">
                        <IconChevronRight size={18} />
                      </div>
                    </Link>
                  );
                })
              ) : (
                <div className="empty-state full-width">
                  <IconUsers size={40} className="empty-icon" />
                  <p>Нет групп</p>
                  <Link to="/groups/manage" className="empty-action">Создать группу</Link>
                </div>
              )}
            </div>
          </div>
        </div>

        {/* RIGHT COLUMN - Extended Stats */}
        <div className="dashboard-right">
          {/* Statistics Card - Extended */}
          <div className="stats-card stats-card-extended" data-tour="teacher-stats">
            <div className="stats-header">
              <div className="stats-icon-wrapper">
                <IconBarChart size={20} />
              </div>
              <h3 className="stats-title">Статистика</h3>
            </div>
            <div className="stats-grid stats-grid-extended">
              {/* Row 1: Основные */}
              <div className="stat-tile">
                <div className="stat-icon">
                  <IconBook size={20} />
                </div>
                <div className="stat-content">
                  <div className="stat-value">{stats?.total_lessons || 0}</div>
                  <div className="stat-label">Уроков проведено</div>
                </div>
              </div>
              <div className="stat-tile">
                <div className="stat-icon">
                  <IconUsers size={20} />
                </div>
                <div className="stat-content">
                  <div className="stat-value">{stats?.total_students || 0}</div>
                  <div className="stat-label">Учеников</div>
                </div>
              </div>
              <div className="stat-tile">
                <div className="stat-icon">
                  <IconFolder size={20} />
                </div>
                <div className="stat-content">
                  <div className="stat-value">{stats?.total_groups || 0}</div>
                  <div className="stat-label">Групп</div>
                </div>
              </div>
              <div className="stat-tile">
                <div className="stat-icon">
                  <IconCalendar size={20} />
                </div>
                <div className="stat-content">
                  <div className="stat-value">{stats?.upcoming_lessons?.length || 0}</div>
                  <div className="stat-label">Ближайшие</div>
                </div>
              </div>
              
              {/* Row 2: Homework Analytics */}
              <div className={`stat-tile ${
                (stats?.avg_grading_days || 0) > 14 ? 'stat-tile-danger' :
                (stats?.avg_grading_days || 0) > 7 ? 'stat-tile-warning' :
                (stats?.avg_grading_days || 0) > 3 ? 'stat-tile-lime' :
                (stats?.avg_grading_days || 0) > 0 ? 'stat-tile-success' : ''
              }`}>
                <div className="stat-icon">
                  <IconClock size={20} />
                </div>
                <div className="stat-content">
                  <div className="stat-value">{stats?.avg_grading_days || 0} дн.</div>
                  <div className="stat-label">Среднее время проверки</div>
                </div>
              </div>
              <div className="stat-tile">
                <div className="stat-icon">
                  <IconTarget size={20} />
                </div>
                <div className="stat-content">
                  <div className="stat-value">{stats?.pending_submissions || 0}</div>
                  <div className="stat-label">Ждут проверки</div>
                </div>
              </div>
              <div className="stat-tile">
                <div className="stat-icon">
                  <IconCheck size={20} />
                </div>
                <div className="stat-content">
                  <div className="stat-value">{stats?.graded_count_30d || 0}</div>
                  <div className="stat-label">Проверено за 30 дней</div>
                </div>
              </div>
              <div className="stat-tile stat-tile-with-tooltip">
                <div className="stat-icon stat-icon-auto">
                  <IconTrendingUp size={20} />
                </div>
                <div className="stat-content">
                  <div className="stat-value">{stats?.auto_graded_answers || 0}</div>
                  <div className="stat-label">Автопроверка</div>
                </div>
                <button
                  type="button"
                  className="stat-tooltip-hint"
                  aria-label={`Сэкономлено времени: ${stats?.time_saved_minutes || 0} мин.`}
                >
                  <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                    <circle cx="12" cy="12" r="10"/>
                    <path d="M12 16v-4M12 8h.01"/>
                  </svg>
                </button>
                <div className="stat-tooltip" role="tooltip">
                  <div className="stat-tooltip-title">Сэкономлено времени</div>
                  <div className="stat-tooltip-value">
                    {stats?.time_saved_minutes || 0} мин.
                    <span className="stat-tooltip-sep">•</span>
                    {Math.round(((stats?.time_saved_minutes || 0) / 60) * 10) / 10} ч.
                  </div>
                </div>
              </div>
              
              {/* Row 3: Additional */}
              <div className="stat-tile stat-tile-wide">
                <div className="stat-icon">
                  <IconGraduationCap size={20} />
                </div>
                <div className="stat-content">
                  <div className="stat-value">{stats?.on_time_percent || 0}%</div>
                  <div className="stat-label">Учеников сдают ДЗ вовремя</div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
            <SupportWidget />
    </div>
  );
};

/* CSS styles are now in TeacherHomePage.css for better performance */

export default TeacherHomePage;
