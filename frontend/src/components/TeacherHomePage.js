import React, { useEffect, useState, useRef } from 'react';
import { getTeacherStatsSummary, getLessons, getGroups, startQuickLesson, startLessonNew, updateLesson } from '../apiService';
import { getCached } from '../utils/dataCache';
import { Link } from 'react-router-dom';
import SubscriptionBanner from './SubscriptionBanner';
import { Select, TeacherDashboardSkeleton } from '../shared/components';
import { useAuth } from '../auth';
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
  
  // State for editing lesson topic inline
  const [editingTopicLessonId, setEditingTopicLessonId] = useState(null);
  const [editingTopicValue, setEditingTopicValue] = useState('');
  const [savingTopic, setSavingTopic] = useState(false);
  const initialLoadDone = useRef(false);
  
  // Determine available platforms from user profile
  const zoomConnected = user?.zoom_connected || false;
  const googleMeetConnected = user?.google_meet_connected || false;
  const availablePlatforms = [];
  if (zoomConnected) availablePlatforms.push('zoom');
  if (googleMeetConnected) availablePlatforms.push('google_meet');

  useEffect(() => {
    const loadData = async () => {
      const cacheTTL = 30000; // 30 секунд
      
      try {
        // ВАЖНО: не используем toISOString() (UTC), иначе день может сдвигаться назад.
        // Backend поддерживает параметр `date=YYYY-MM-DD` и сам строит диапазон в локальной TZ.
        const now = new Date();
        const yyyy = String(now.getFullYear());
        const mm = String(now.getMonth() + 1).padStart(2, '0');
        const dd = String(now.getDate()).padStart(2, '0');
        const today = `${yyyy}-${mm}-${dd}`;
        
        // Используем кэш для мгновенного отображения при навигации
        const useCache = initialLoadDone.current;
        initialLoadDone.current = true;
        
        if (useCache) {
          const [statsData, lessonsData, groupsData] = await Promise.all([
            getCached('teacher:stats', async () => {
              const res = await getTeacherStatsSummary();
              console.log('[TeacherHomePage] Stats fetched (for cache):', res.data);
              return res.data;
            }, cacheTTL),
            getCached(`teacher:lessons:${today}`, async () => {
              const res = await getLessons({ date: today, include_recurring: true });
              return Array.isArray(res.data) ? res.data : res.data.results || [];
            }, cacheTTL),
            getCached('teacher:groups', async () => {
              const res = await getGroups();
              return Array.isArray(res.data) ? res.data : res.data.results || [];
            }, cacheTTL),
          ]);
          
          console.log('[TeacherHomePage] Stats from cache:', statsData);
          setStats(statsData);
          setLessons(lessonsData);
          setGroups(groupsData);
          setLoading(false);
          return;
        }

        const [statsRes, lessonsRes, groupsRes] = await Promise.all([
          getTeacherStatsSummary(),
          getLessons({ date: today, include_recurring: true }),
          getGroups(),
        ]);

        console.log('[TeacherHomePage] Stats received:', statsRes.data);
        setStats(statsRes.data);
        const lessonList = Array.isArray(lessonsRes.data) ? lessonsRes.data : lessonsRes.data.results || [];
        // Показываем все уроки на сегодня (без ограничения)
        setLessons(lessonList);
        setGroups(Array.isArray(groupsRes.data) ? groupsRes.data : groupsRes.data.results || []);
      } catch (err) {
        console.error('Failed to load dashboard data:', err);
      } finally {
        setLoading(false);
      }
    };
    loadData();
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
      const res = await startQuickLesson({
        record_lesson: recordLesson,
        group_id: selectedGroupId || undefined,
      });
      if (res.data?.zoom_start_url) {
        window.open(res.data.zoom_start_url, '_blank');
        setShowStartModal(false);
      } else if (res.data?.start_url) {
        window.open(res.data.start_url, '_blank');
        setShowStartModal(false);
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

  // Запустить конкретный урок
  const handleStartScheduledLesson = async () => {
    if (lessonStarting || !selectedLesson) return;
    setLessonStarting(true);
    setLessonStartError(null);
    
    try {
      // Если изменилось название или флаг записи - сначала обновляем урок
      const needsUpdate = 
        (lessonRecordEnabled !== selectedLesson.record_lesson) ||
        (recordingTitle && recordingTitle !== selectedLesson.title);
      
      if (needsUpdate) {
        await updateLesson(selectedLesson.id, {
          record_lesson: lessonRecordEnabled,
          title: recordingTitle || selectedLesson.title,
        });
      }
      
      const response = await startLessonNew(selectedLesson.id, {
        record_lesson: lessonRecordEnabled,
        force_new_meeting: needsUpdate && lessonRecordEnabled && Boolean(selectedLesson.zoom_meeting_id),
      });
      
      if (response.data?.zoom_start_url) {
        window.open(response.data.zoom_start_url, '_blank', 'noopener,noreferrer');
        setShowLessonStartModal(false);
        
        // Обновляем список уроков
        setLessons(prev => prev.map(l => 
          l.id === selectedLesson.id 
            ? { ...l, zoom_start_url: response.data.zoom_start_url, zoom_join_url: response.data.zoom_join_url }
            : l
        ));
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
        <style>{globalStyles}</style>
        <TeacherDashboardSkeleton />
      </div>
    );
  }

  return (
    <div className="dashboard-container">
      <style>{globalStyles}</style>
      
      {/* Subscription Banner */}
      <SubscriptionBanner />

      {/* Platform Selection Modal */}
      {showPlatformModal && (
        <>
          <div className="modal-overlay" onClick={() => setShowPlatformModal(false)} />
          <div className="platform-modal">
            <h3 className="platform-modal-title">Выберите платформу</h3>
            <p className="platform-modal-subtitle">Где вы хотите провести урок?</p>
            
            <div className="platform-options">
              <button
                type="button"
                className={`platform-option ${selectedPlatform === 'zoom' ? 'selected' : ''}`}
                onClick={() => setSelectedPlatform('zoom')}
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
                onClick={() => setSelectedPlatform('google_meet')}
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

            {/* Record Option */}
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

            {startError && (
              <div className="start-modal-error">{startError}</div>
            )}

            <div className="start-modal-actions">
              <button
                className="start-modal-btn primary"
                onClick={handleQuickStart}
                disabled={starting}
              >
                <IconPlay size={16} />
                <span>{starting ? 'Запуск...' : 'Начать урок'}</span>
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

            {/* Record Option */}
            <label className={`start-modal-checkbox ${lessonRecordEnabled ? 'checked' : ''}`}>
              <input
                type="checkbox"
                checked={lessonRecordEnabled}
                onChange={(e) => setLessonRecordEnabled(e.target.checked)}
              />
              <IconDisc size={18} />
              <span>Записывать урок</span>
            </label>

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

            <div className="start-modal-actions">
              <button
                className="start-modal-btn primary"
                onClick={handleStartScheduledLesson}
                disabled={lessonStarting}
              >
                <IconPlay size={16} />
                <span>{lessonStarting ? 'Запуск...' : 'Начать занятие'}</span>
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
          <div className="hero-card">
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
          <div className="section-card">
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
                        {lesson.zoom_start_url ? (
                          <a 
                            href={lesson.zoom_start_url} 
                            target="_blank" 
                            rel="noopener noreferrer"
                            className="schedule-start-btn active"
                          >
                            <IconVideo size={14} />
                            <span>Продолжить</span>
                          </a>
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
          <div className="section-card">
            <div className="section-header">
              <div className="section-title-group">
                <div className="section-icon-wrapper">
                  <IconUsers size={18} />
                </div>
                <h3 className="section-title">Ученики</h3>
              </div>
              <Link to="/groups/manage" className="section-link">
                Управление
                <IconChevronRight size={16} />
              </Link>
            </div>
            <div className="groups-grid">
              {groups.length > 0 ? (
                groups.map((group) => {
                  const colorIndex = getGroupColorIndex(group.name);
                  const cleanName = cleanGroupName(group.name);
                  return (
                    <Link
                      key={group.id}
                      to={`/attendance/${group.id}`}
                      className="group-card-minimal"
                    >
                      <div className={`group-icon-wrapper group-icon-${colorIndex}`}>
                        {getGroupIcon(group.name)}
                      </div>
                      <div className="group-info">
                        <h4 className="group-name-minimal">{cleanName}</h4>
                        <span className="group-count">{group.students?.length || 0} уч.</span>
                      </div>
                      <IconChevronRight size={16} className="group-arrow-icon" />
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
          <div className="stats-card stats-card-extended">
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
    </div>
  );
};

/* =====================================================
   GLOBAL STYLES - Enterprise Indigo Theme
   Aurora Background + Glass Cards
   ===================================================== */
const globalStyles = `
  @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&display=swap');

  /* === CSS VARIABLES - INDIGO THEME === */
  :root {
    --font-family: 'Plus Jakarta Sans', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
    
    /* Indigo Color Palette */
    --indigo-50: #eef2ff;
    --indigo-100: #e0e7ff;
    --indigo-200: #c7d2fe;
    --indigo-300: #a5b4fc;
    --indigo-400: #818cf8;
    --indigo-500: #6366f1;
    --indigo-600: #4f46e5;
    --indigo-700: #4338ca;
    --indigo-800: #3730a3;
    --indigo-900: #312e81;
    
    --color-primary: var(--indigo-600);
    --color-primary-hover: var(--indigo-700);
    --color-primary-light: var(--indigo-100);
    
    --gradient-primary: linear-gradient(135deg, var(--indigo-700) 0%, var(--indigo-500) 100%);
    --gradient-hero: linear-gradient(135deg, var(--indigo-800) 0%, var(--indigo-600) 50%, var(--indigo-500) 100%);
    
    /* Neutrals */
    --slate-50: #f8fafc;
    --slate-100: #f1f5f9;
    --slate-200: #e2e8f0;
    --slate-300: #cbd5e1;
    --slate-400: #94a3b8;
    --slate-500: #64748b;
    --slate-600: #475569;
    --slate-700: #334155;
    --slate-800: #1e293b;
    --slate-900: #0f172a;
    
    --color-bg: var(--slate-50);
    --color-card: #ffffff;
    --color-border: var(--slate-200);
    --color-text-primary: var(--slate-800);
    --color-text-secondary: var(--slate-500);
    --color-text-muted: var(--slate-400);
    
    /* Shadows */
    --shadow-sm: 0 1px 2px rgba(0, 0, 0, 0.04);
    --shadow-md: 0 4px 6px -1px rgba(0, 0, 0, 0.08), 0 2px 4px -2px rgba(0, 0, 0, 0.04);
    --shadow-lg: 0 10px 15px -3px rgba(0, 0, 0, 0.08), 0 4px 6px -4px rgba(0, 0, 0, 0.04);
    --shadow-xl: 0 20px 25px -5px rgba(0, 0, 0, 0.1), 0 8px 10px -6px rgba(0, 0, 0, 0.04);
    --shadow-indigo: 0 20px 40px -10px rgba(79, 70, 229, 0.35);
    
    /* Border Radius */
    --radius-sm: 6px;
    --radius-md: 10px;
    --radius-lg: 14px;
    --radius-xl: 18px;
  }

  /* === DASHBOARD CONTAINER === */
  .dashboard-container {
    font-family: var(--font-family);
    background: transparent;
    min-height: 100vh;
    padding: 7.25rem 1.5rem 1.5rem;
    position: relative;
    overflow-x: hidden;
  }

  .dashboard-container > * {
    position: relative;
    z-index: 1;
  }

  /* === LOADING STATE === */
  .dashboard-loading {
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    min-height: 60vh;
    color: var(--color-text-secondary);
  }

  .loading-spinner {
    width: 44px;
    height: 44px;
    border: 3px solid var(--color-border);
    border-top-color: var(--color-primary);
    border-radius: 50%;
    animation: spin 0.8s linear infinite;
    margin-bottom: 1rem;
  }

  @keyframes spin {
    to { transform: rotate(360deg); }
  }

  /* === GRID LAYOUT === */
  .dashboard-grid {
    display: grid;
    grid-template-columns: 1fr 340px;
    gap: 1.5rem;
    max-width: 1240px;
    margin: 0 auto;
    align-items: stretch;
  }

  .dashboard-left {
    display: flex;
    flex-direction: column;
    gap: 1.5rem;
  }

  .dashboard-right {
    display: flex;
    flex-direction: column;
    gap: 1.5rem;
  }

  /* === HERO CARD === */
  .hero-card {
    background: var(--gradient-hero);
    border-radius: var(--radius-xl);
    padding: 1.75rem 2rem;
    color: #fff;
    position: relative;
    overflow: hidden;
    box-shadow: var(--shadow-indigo);
  }

  .hero-glow {
    position: absolute;
    top: -80px;
    right: -80px;
    width: 200px;
    height: 200px;
    background: radial-gradient(circle, rgba(255,255,255,0.12) 0%, transparent 70%);
    border-radius: 50%;
  }

  .hero-pattern {
    position: absolute;
    inset: 0;
    opacity: 0.4;
  }

  .hero-content {
    position: relative;
    z-index: 1;
  }

  .hero-icon-wrapper {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    width: 44px;
    height: 44px;
    background: rgba(255, 255, 255, 0.15);
    border-radius: var(--radius-md);
    margin-bottom: 0.75rem;
    backdrop-filter: blur(10px);
  }

  .hero-icon {
    color: #fff;
  }

  .hero-title {
    font-size: 1.75rem;
    font-weight: 800;
    margin: 0 0 0.5rem 0;
    letter-spacing: -0.03em;
    font-family: 'Plus Jakarta Sans', sans-serif;
  }

  .hero-subtitle {
    font-size: 1rem;
    font-weight: 500;
    color: rgba(255, 255, 255, 0.95);
    margin-bottom: 1.25rem;
    max-width: 380px;
    line-height: 1.6;
    text-shadow: 0 1px 2px rgba(0, 0, 0, 0.1);
  }

  .hero-button {
    display: inline-flex;
    align-items: center;
    gap: 0.5rem;
    background: #fff;
    color: var(--indigo-700);
    border: none;
    padding: 0.75rem 1.25rem;
    border-radius: var(--radius-md);
    font-family: 'Plus Jakarta Sans', sans-serif;
    font-weight: 700;
    font-size: 0.95rem;
    cursor: pointer;
    box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
    transition: all 0.2s ease;
  }

  .hero-button:hover {
    transform: translateY(-2px);
    box-shadow: 0 6px 20px rgba(0, 0, 0, 0.2);
  }

  .hero-button:disabled {
    opacity: 0.7;
    cursor: not-allowed;
    transform: none;
  }

  /* === SECTION CARD - Glass Morphism === */
  .section-card {
    background: rgba(255, 255, 255, 0.75);
    backdrop-filter: blur(14px);
    -webkit-backdrop-filter: blur(14px);
    border-radius: var(--radius-lg);
    padding: 1.5rem;
    box-shadow: 0 25px 50px -12px rgba(79, 70, 229, 0.12), 
                0 10px 25px -5px rgba(0, 0, 0, 0.06),
                0 0 20px rgba(79, 70, 229, 0.08);
    border: 1px solid rgba(255, 255, 255, 0.6);
    transition: all 0.3s cubic-bezier(0.16, 1, 0.3, 1);
  }

  .section-card:hover {
    box-shadow: 0 30px 60px -14px rgba(79, 70, 229, 0.18),
                0 0 25px rgba(79, 70, 229, 0.15);
    transform: translateY(-4px) scale(1.01);
    border-color: rgba(79, 70, 229, 0.2);
  }

  .section-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 1.25rem;
  }

  .section-title-group {
    display: flex;
    align-items: center;
    gap: 0.625rem;
  }

  .section-icon-wrapper {
    display: flex;
    align-items: center;
    justify-content: center;
    width: 32px;
    height: 32px;
    background: var(--indigo-100);
    border-radius: var(--radius-sm);
    color: var(--indigo-600);
  }

  .section-title {
    font-size: 1.1rem;
    font-weight: 700;
    color: var(--color-text-primary);
    margin: 0;
    font-family: 'Plus Jakarta Sans', sans-serif;
    letter-spacing: -0.02em;
  }

  .section-link {
    display: flex;
    align-items: center;
    gap: 0.25rem;
    font-size: 0.85rem;
    color: var(--color-primary);
    text-decoration: none;
    font-weight: 600;
    transition: all 0.2s;
  }

  .section-link:hover {
    color: var(--color-primary-hover);
  }

  .section-link:hover svg {
    transform: translateX(2px);
  }

  .section-link svg {
    transition: transform 0.2s;
  }

  /* === SCHEDULE LIST === */
  .schedule-list {
    display: flex;
    flex-direction: column;
    gap: 0.625rem;
  }

  .schedule-item {
    display: flex;
    align-items: center;
    gap: 1rem;
    padding: 0.875rem 1rem;
    background: var(--slate-50);
    border-radius: var(--radius-md);
    border: 1px solid transparent;
    transition: all 0.25s cubic-bezier(0.16, 1, 0.3, 1);
  }

  .schedule-item:hover {
    background: #fff;
    border-color: rgba(79, 70, 229, 0.12);
    box-shadow: 0 6px 16px rgba(79, 70, 229, 0.1), 0 2px 6px rgba(0, 0, 0, 0.04);
    transform: translateY(-2px);
  }

  .schedule-time-badge {
    display: flex;
    flex-direction: column;
    align-items: center;
    background: var(--gradient-primary);
    color: #fff;
    padding: 0.5rem 0.75rem;
    border-radius: var(--radius-sm);
    min-width: 68px;
    text-align: center;
  }

  .schedule-date {
    font-size: 0.7rem;
    font-weight: 700;
    text-transform: uppercase;
    opacity: 0.95;
    letter-spacing: 0.5px;
  }

  .schedule-hour {
    font-size: 0.95rem;
    font-weight: 800;
    font-family: 'Plus Jakarta Sans', sans-serif;
  }

  .schedule-info {
    flex: 1;
    min-width: 0;
  }

  .schedule-group-name {
    font-size: 0.95rem;
    font-weight: 700;
    color: var(--color-text-primary);
    margin-bottom: 0.3rem;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
    font-family: 'Plus Jakarta Sans', sans-serif;
  }

  .schedule-topic-row {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    min-height: 24px;
  }

  .schedule-topic {
    font-size: 0.85rem;
    color: var(--color-text-secondary);
    font-weight: 500;
  }

  .schedule-topic-empty {
    font-style: italic;
    color: var(--slate-400);
  }

  .schedule-topic-edit-btn {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    width: 22px;
    height: 22px;
    background: transparent;
    border: 1px solid var(--slate-200);
    border-radius: var(--radius-sm);
    color: var(--slate-400);
    cursor: pointer;
    transition: all 0.15s ease;
  }

  .schedule-topic-edit-btn:hover {
    background: var(--indigo-50);
    border-color: var(--indigo-300);
    color: var(--indigo-600);
  }

  .schedule-topic-edit {
    display: flex;
    align-items: center;
    gap: 0.4rem;
    flex: 1;
  }

  .schedule-topic-input {
    flex: 1;
    padding: 0.35rem 0.6rem;
    border: 1px solid var(--indigo-300);
    border-radius: var(--radius-sm);
    font-size: 0.8rem;
    font-family: var(--font-family);
    outline: none;
    background: #fff;
    min-width: 120px;
  }

  .schedule-topic-input:focus {
    border-color: var(--indigo-500);
    box-shadow: 0 0 0 3px rgba(79, 70, 229, 0.1);
  }

  .schedule-topic-btn {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    width: 24px;
    height: 24px;
    border: none;
    border-radius: var(--radius-sm);
    cursor: pointer;
    transition: all 0.15s ease;
  }

  .schedule-topic-btn.save {
    background: var(--indigo-600);
    color: #fff;
  }

  .schedule-topic-btn.save:hover:not(:disabled) {
    background: var(--indigo-700);
  }

  .schedule-topic-btn.save:disabled {
    opacity: 0.6;
    cursor: not-allowed;
  }

  .schedule-topic-btn.cancel {
    background: var(--slate-200);
    color: var(--slate-600);
  }

  .schedule-topic-btn.cancel:hover {
    background: var(--slate-300);
  }

  .schedule-title {
    font-size: 0.9rem;
    font-weight: 600;
    color: var(--color-text-primary);
    margin-bottom: 0.2rem;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
  }

  .schedule-group {
    font-size: 0.8rem;
    color: var(--color-text-secondary);
  }

  .schedule-actions {
    flex-shrink: 0;
  }

  .schedule-start-btn {
    display: inline-flex;
    align-items: center;
    gap: 0.4rem;
    background: var(--gradient-primary);
    color: #fff;
    border: none;
    padding: 0.5rem 0.9rem;
    border-radius: var(--radius-sm);
    font-family: 'Plus Jakarta Sans', sans-serif;
    font-weight: 700;
    font-size: 0.8rem;
    cursor: pointer;
    text-decoration: none;
    transition: all 0.2s ease;
    box-shadow: 0 2px 6px rgba(79, 70, 229, 0.25);
  }

  .schedule-start-btn:hover {
    transform: translateY(-1px);
    box-shadow: 0 4px 10px rgba(79, 70, 229, 0.35);
  }

  .schedule-start-btn.active {
    background: linear-gradient(135deg, #059669 0%, #10b981 100%);
    box-shadow: 0 2px 6px rgba(16, 185, 129, 0.3);
  }

  .schedule-start-btn.active:hover {
    box-shadow: 0 4px 10px rgba(16, 185, 129, 0.4);
  }

  .status-badge {
    display: inline-flex;
    align-items: center;
    gap: 0.35rem;
    font-size: 0.7rem;
    font-weight: 600;
    padding: 0.35rem 0.65rem;
    border-radius: 100px;
    text-transform: uppercase;
    letter-spacing: 0.3px;
  }

  .status-active {
    background: #dcfce7;
    color: #166534;
  }

  .status-pending {
    background: var(--slate-100);
    color: var(--slate-500);
  }

  /* === GROUPS GRID - Minimal Design === */
  .groups-grid {
    display: flex;
    flex-direction: column;
    gap: 0.5rem;
  }

  .group-card-minimal {
    display: flex;
    align-items: center;
    gap: 0.875rem;
    padding: 0.75rem 1rem;
    background: rgba(255, 255, 255, 0.6);
    border-radius: var(--radius-md);
    text-decoration: none;
    border: 1px solid rgba(226, 232, 240, 0.8);
    transition: all 0.25s cubic-bezier(0.16, 1, 0.3, 1);
  }

  .group-card-minimal:hover {
    background: #fff;
    border-color: rgba(79, 70, 229, 0.12);
    box-shadow: 0 6px 16px rgba(79, 70, 229, 0.1), 0 2px 6px rgba(0, 0, 0, 0.04);
    transform: translateY(-2px);
  }

  .group-icon-wrapper {
    width: 36px;
    height: 36px;
    border-radius: var(--radius-md);
    display: flex;
    align-items: center;
    justify-content: center;
    flex-shrink: 0;
  }

  .group-icon-0 { background: rgba(79, 70, 229, 0.1); color: var(--indigo-600); }
  .group-icon-1 { background: rgba(14, 165, 233, 0.1); color: #0ea5e9; }
  .group-icon-2 { background: rgba(16, 185, 129, 0.1); color: #10b981; }
  .group-icon-3 { background: rgba(245, 158, 11, 0.1); color: #f59e0b; }
  .group-icon-4 { background: rgba(236, 72, 153, 0.1); color: #ec4899; }
  .group-icon-5 { background: rgba(139, 92, 246, 0.1); color: #8b5cf6; }

  .group-cover-icon {
    width: 18px;
    height: 18px;
  }

  .group-info {
    flex: 1;
    min-width: 0;
  }

  .group-name-minimal {
    font-size: 0.9rem;
    font-weight: 700;
    color: var(--color-text-primary);
    margin: 0;
    line-height: 1.3;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
    font-family: 'Plus Jakarta Sans', sans-serif;
  }

  .group-count {
    font-size: 0.8rem;
    color: var(--color-text-secondary);
    font-weight: 600;
  }

  .group-arrow-icon {
    color: var(--color-text-muted);
    flex-shrink: 0;
    opacity: 0;
    transition: opacity 0.2s;
  }

  .group-card-minimal:hover .group-arrow-icon {
    opacity: 1;
    color: var(--color-primary);
  }

  /* === EMPTY STATE === */
  .empty-state {
    text-align: center;
    padding: 1.5rem 1rem;
    color: var(--color-text-secondary);
  }

  .empty-state.full-width {
    grid-column: 1 / -1;
  }

  .empty-icon {
    color: var(--color-text-muted);
    margin-bottom: 0.5rem;
    opacity: 0.6;
  }

  .empty-state p {
    margin: 0 0 0.75rem 0;
    font-size: 0.95rem;
    font-weight: 600;
    color: var(--color-text-secondary);
  }

  .empty-action {
    display: inline-block;
    color: var(--color-primary);
    font-weight: 700;
    font-size: 0.9rem;
    text-decoration: none;
  }

  .empty-action:hover {
    text-decoration: underline;
  }

  /* === STATS CARD (Glass Morphism) === */
  .stats-card {
    background: rgba(255, 255, 255, 0.75);
    backdrop-filter: blur(14px);
    -webkit-backdrop-filter: blur(14px);
    border-radius: var(--radius-lg);
    padding: 1.5rem;
    box-shadow: 0 25px 50px -12px rgba(79, 70, 229, 0.12), 
                0 10px 25px -5px rgba(0, 0, 0, 0.06),
                0 0 20px rgba(79, 70, 229, 0.08);
    border: 1px solid rgba(255, 255, 255, 0.6);
    transition: all 0.3s cubic-bezier(0.16, 1, 0.3, 1);
  }

  .stats-card:hover {
    box-shadow: 0 30px 60px -14px rgba(79, 70, 229, 0.18),
                0 0 25px rgba(79, 70, 229, 0.15);
    transform: translateY(-4px) scale(1.01);
    border-color: rgba(79, 70, 229, 0.2);
  }

  .stats-header {
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 0.5rem;
    margin-bottom: 1rem;
    padding-bottom: 0.75rem;
    border-bottom: 1px solid var(--color-border);
  }

  .stats-icon-wrapper {
    display: flex;
    align-items: center;
    justify-content: center;
    width: 28px;
    height: 28px;
    background: var(--indigo-100);
    border-radius: var(--radius-sm);
    color: var(--indigo-600);
  }

  .stats-title {
    font-size: 1rem;
    font-weight: 700;
    color: var(--color-text-primary);
    margin: 0;
    font-family: 'Plus Jakarta Sans', sans-serif;
    letter-spacing: -0.02em;
  }

  .stats-grid {
    display: grid;
    grid-template-columns: repeat(2, 1fr);
    gap: 0.75rem;
  }

  .stat-tile {
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    text-align: center;
    gap: 0.5rem;
    background: var(--slate-50);
    border-radius: var(--radius-md);
    padding: 1rem 0.75rem;
    border: 1px solid var(--color-border);
    transition: all 0.25s cubic-bezier(0.16, 1, 0.3, 1);
    min-height: 90px;
  }

  .stat-tile:hover {
    transform: translateY(-3px);
    box-shadow: 0 8px 20px rgba(79, 70, 229, 0.12), 0 4px 8px rgba(0, 0, 0, 0.06);
    border-color: rgba(79, 70, 229, 0.15);
    background: #fff;
  }

  .stat-icon {
    display: flex;
    align-items: center;
    justify-content: center;
    width: 32px;
    height: 32px;
    background: var(--indigo-100);
    border-radius: var(--radius-sm);
    color: var(--indigo-600);
    flex-shrink: 0;
  }

  .stat-content {
    display: flex;
    flex-direction: column;
    align-items: center;
  }

  .stat-value {
    font-size: 1.35rem;
    font-weight: 700;
    color: var(--color-text-primary);
    line-height: 1;
    margin-bottom: 0.125rem;
    font-family: 'Plus Jakarta Sans', sans-serif;
  }

  .stat-label {
    font-size: 0.7rem;
    color: var(--color-text-secondary);
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.3px;
    line-height: 1.3;
    display: block;
  }

  /* === QUICK ACTIONS CARD (Glass Morphism) === */
  .quick-actions-card {
    background: rgba(255, 255, 255, 0.75);
    backdrop-filter: blur(14px);
    -webkit-backdrop-filter: blur(14px);
    border-radius: var(--radius-lg);
    padding: 1.5rem;
    box-shadow: 0 25px 50px -12px rgba(79, 70, 229, 0.12), 
                0 10px 25px -5px rgba(0, 0, 0, 0.06),
                0 0 20px rgba(79, 70, 229, 0.08);
    border: 1px solid rgba(255, 255, 255, 0.6);
    flex: 1;
    transition: all 0.3s cubic-bezier(0.16, 1, 0.3, 1);
  }

  .quick-actions-card:hover {
    box-shadow: 0 30px 60px -14px rgba(79, 70, 229, 0.18),
                0 0 25px rgba(79, 70, 229, 0.15);
    transform: translateY(-4px) scale(1.01);
    border-color: rgba(79, 70, 229, 0.2);
  }

  .quick-actions-header {
    display: flex;
    align-items: center;
    gap: 0.625rem;
    margin-bottom: 1rem;
  }

  .quick-actions-icon-wrapper {
    display: flex;
    align-items: center;
    justify-content: center;
    width: 36px;
    height: 36px;
    background: var(--indigo-100);
    border-radius: var(--radius-sm);
    color: var(--indigo-600);
  }

  .quick-actions-title {
    font-size: 1rem;
    font-weight: 600;
    color: var(--color-text-primary);
    margin: 0;
  }

  .quick-actions-list {
    display: flex;
    flex-direction: column;
    gap: 0.5rem;
  }

  .quick-action-item {
    display: flex;
    align-items: center;
    gap: 0.875rem;
    padding: 0.875rem 1rem;
    background: var(--slate-50);
    border-radius: var(--radius-md);
    text-decoration: none;
    border: 1px solid transparent;
    transition: all 0.25s cubic-bezier(0.16, 1, 0.3, 1);
  }

  .quick-action-item:hover {
    background: #fff;
    border-color: rgba(79, 70, 229, 0.12);
    box-shadow: 0 6px 16px rgba(79, 70, 229, 0.1), 0 2px 6px rgba(0, 0, 0, 0.04);
    transform: translateY(-2px);
  }

  .quick-action-item:hover .quick-action-arrow {
    transform: translateX(3px);
    color: var(--color-primary);
  }

  .quick-action-icon {
    display: flex;
    align-items: center;
    justify-content: center;
    width: 36px;
    height: 36px;
    background: var(--indigo-100);
    border-radius: var(--radius-sm);
    color: var(--indigo-600);
    flex-shrink: 0;
  }

  .quick-action-content {
    flex: 1;
    min-width: 0;
    display: flex;
    flex-direction: column;
    gap: 0.125rem;
  }

  .quick-action-label {
    font-size: 0.875rem;
    font-weight: 600;
    color: var(--color-text-primary);
  }

  .quick-action-hint {
    font-size: 0.75rem;
    color: var(--color-text-secondary);
  }

  .quick-action-arrow {
    color: var(--color-text-muted);
    transition: all 0.2s ease;
    flex-shrink: 0;
  }

  /* === RESPONSIVE === */
  @media (max-width: 1024px) {
    .dashboard-grid {
      grid-template-columns: 1fr;
    }

    .dashboard-right {
      display: grid;
      grid-template-columns: repeat(2, 1fr);
      gap: 1rem;
    }
  }

  @media (max-width: 640px) {
    .dashboard-container {
      padding: 6.25rem 1rem 1.25rem;
    }

    .hero-card {
      padding: 1.75rem;
    }

    .hero-title {
      font-size: 1.5rem;
    }

    .groups-grid {
      grid-template-columns: repeat(2, 1fr);
    }

    .dashboard-right {
      grid-template-columns: 1fr;
    }

    .stats-grid {
      grid-template-columns: 1fr 1fr;
    }

    .quick-actions-list {
      gap: 0.375rem;
    }

    .quick-action-hint {
      display: none;
    }
  }

  /* === START LESSON MODAL === */
  .modal-overlay {
    position: fixed;
    inset: 0;
    background: rgba(0, 0, 0, 0.4);
    backdrop-filter: blur(4px);
    z-index: 1000;
  }

  .start-modal {
    position: fixed;
    top: 50%;
    left: 50%;
    transform: translate(-50%, -50%);
    background: #fff;
    border-radius: var(--radius-xl);
    padding: 1.75rem;
    width: 400px;
    max-width: 92vw;
    box-shadow: 0 24px 60px rgba(0, 0, 0, 0.2);
    z-index: 1001;
  }

  .start-modal-title {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    font-size: 1.15rem;
    font-weight: 600;
    color: var(--color-text-primary);
    margin: 0 0 1.25rem 0;
  }

  .start-modal-title svg {
    color: var(--color-primary);
  }

  .start-modal-field {
    margin-bottom: 1rem;
  }

  .start-modal-label {
    display: block;
    font-size: 0.85rem;
    font-weight: 500;
    color: var(--color-text-secondary);
    margin-bottom: 0.5rem;
  }

  .start-modal-select {
    width: 100%;
    padding: 0.75rem 2.5rem 0.75rem 1rem;
    font-size: 0.9rem;
    font-family: var(--font-family);
    border: 2px solid var(--slate-200);
    border-radius: var(--radius-md);
    background: #fff;
    color: var(--color-text-primary);
    cursor: pointer;
    transition: all 0.15s;
    -webkit-appearance: none;
    -moz-appearance: none;
    appearance: none;
    background-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='12' height='12' viewBox='0 0 12 12'%3E%3Cpath fill='%23475569' d='M2 4l4 4 4-4'/%3E%3C/svg%3E");
    background-repeat: no-repeat;
    background-position: right 0.75rem center;
    background-size: 12px;
  }

  .start-modal-select:hover {
    border-color: var(--slate-300);
  }

  .start-modal-select:focus {
    outline: none;
    border-color: var(--color-primary);
    box-shadow: 0 0 0 3px var(--color-primary-light);
  }

  .start-modal-input {
    width: 100%;
    padding: 0.75rem 1rem;
    font-size: 0.9rem;
    font-family: var(--font-family);
    border: 1px solid var(--color-border);
    border-radius: var(--radius-md);
    background: #fff;
    color: var(--color-text-primary);
    transition: border-color 0.15s;
    box-sizing: border-box;
  }

  .start-modal-input:focus {
    outline: none;
    border-color: var(--color-primary);
    box-shadow: 0 0 0 3px var(--color-primary-light);
  }

  .start-modal-input::placeholder {
    color: var(--color-text-muted);
  }

  .start-modal-lesson-info {
    background: var(--slate-50);
    padding: 0.875rem 1rem;
    border-radius: var(--radius-md);
    margin-bottom: 1rem;
    border: 1px solid var(--color-border);
  }

  .start-modal-lesson-name {
    font-size: 0.95rem;
    font-weight: 600;
    color: var(--color-text-primary);
    margin-bottom: 0.25rem;
  }

  .start-modal-lesson-group {
    font-size: 0.8rem;
    color: var(--color-text-secondary);
  }

  .start-modal-lesson-topic {
    font-size: 0.8rem;
    color: var(--indigo-600);
    margin-top: 0.25rem;
    font-style: italic;
  }

  .start-modal-checkbox {
    display: flex;
    align-items: center;
    gap: 0.75rem;
    padding: 0.85rem 1rem;
    border-radius: var(--radius-md);
    border: 1px solid var(--color-border);
    background: #f9fafb;
    cursor: pointer;
    transition: all 0.15s;
    margin-bottom: 0.75rem;
  }

  .start-modal-checkbox.checked {
    background: var(--indigo-50);
    border-color: var(--indigo-200);
  }

  .start-modal-checkbox input {
    width: 1.1rem;
    height: 1.1rem;
    accent-color: var(--color-primary);
    cursor: pointer;
  }

  .start-modal-checkbox svg {
    color: var(--color-text-secondary);
  }

  .start-modal-checkbox.checked svg {
    color: var(--color-primary);
  }

  .start-modal-checkbox span {
    font-size: 0.9rem;
    font-weight: 500;
    color: var(--color-text-primary);
  }

  .start-modal-use-topic-checkbox {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    font-size: 0.85rem;
    color: var(--color-text-secondary);
    cursor: pointer;
    margin-bottom: 0.75rem;
  }

  .start-modal-use-topic-checkbox input {
    width: 1rem;
    height: 1rem;
    accent-color: var(--color-primary);
    cursor: pointer;
  }

  .start-modal-hint {
    display: flex;
    align-items: flex-start;
    gap: 0.5rem;
    padding: 0.75rem 1rem;
    background: var(--indigo-50);
    border-radius: var(--radius-md);
    font-size: 0.8rem;
    color: var(--color-text-secondary);
    margin-bottom: 1rem;
  }

  .start-modal-hint svg {
    color: var(--color-primary);
    flex-shrink: 0;
    margin-top: 1px;
  }

  .start-modal-error {
    padding: 0.75rem 1rem;
    background: #fef2f2;
    border: 1px solid #fecaca;
    border-radius: var(--radius-md);
    color: #dc2626;
    font-size: 0.85rem;
    margin-bottom: 1rem;
  }

  .start-modal-actions {
    display: flex;
    gap: 0.75rem;
    margin-top: 1rem;
  }

  .start-modal-btn {
    flex: 1;
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 0.5rem;
    padding: 0.75rem 1rem;
    font-size: 0.9rem;
    font-weight: 600;
    border-radius: var(--radius-md);
    cursor: pointer;
    transition: all 0.15s;
    border: none;
  }

  .start-modal-btn.primary {
    background: var(--gradient-primary);
    color: #fff;
    box-shadow: 0 4px 12px rgba(79, 70, 229, 0.3);
  }

  .start-modal-btn.primary:hover:not(:disabled) {
    box-shadow: 0 6px 16px rgba(79, 70, 229, 0.4);
    transform: translateY(-1px);
  }

  .start-modal-btn.primary:disabled {
    opacity: 0.7;
    cursor: not-allowed;
  }

  .start-modal-btn.secondary {
    background: #f3f4f6;
    color: var(--color-text-secondary);
    border: 1px solid var(--color-border);
  }

  .start-modal-btn.secondary:hover {
    background: #e5e7eb;
  }

  /* === PLATFORM SELECTION MODAL === */
  .platform-modal {
    position: fixed;
    top: 50%;
    left: 50%;
    transform: translate(-50%, -50%);
    background: #fff;
    border-radius: var(--radius-xl);
    padding: 1.75rem;
    width: 400px;
    max-width: 92vw;
    box-shadow: 0 24px 60px rgba(0, 0, 0, 0.2);
    z-index: 1001;
    animation: modalFadeIn 0.2s ease-out;
  }

  @keyframes modalFadeIn {
    from {
      opacity: 0;
      transform: translate(-50%, -48%);
    }
    to {
      opacity: 1;
      transform: translate(-50%, -50%);
    }
  }

  .platform-modal-title {
    font-size: 1.25rem;
    font-weight: 700;
    color: var(--color-text-primary);
    margin: 0 0 0.25rem 0;
    letter-spacing: -0.02em;
    font-family: 'Plus Jakarta Sans', sans-serif;
  }

  .platform-modal-subtitle {
    font-size: 0.9rem;
    color: var(--color-text-secondary);
    margin: 0 0 1.25rem 0;
  }

  .platform-options {
    display: flex;
    flex-direction: column;
    gap: 0.75rem;
    margin-bottom: 1.5rem;
  }

  .platform-option {
    display: flex;
    align-items: center;
    gap: 1rem;
    padding: 1rem 1.25rem;
    border: 2px solid var(--color-border);
    border-radius: var(--radius-lg);
    background: #fff;
    cursor: pointer;
    transition: all 0.2s ease;
    text-align: left;
    width: 100%;
  }

  .platform-option:hover {
    border-color: var(--indigo-200);
    background: var(--slate-50);
  }

  .platform-option.selected {
    border-color: var(--color-primary);
    background: var(--indigo-50);
    box-shadow: 0 0 0 3px rgba(79, 70, 229, 0.1);
  }

  .platform-option-icon {
    width: 48px;
    height: 48px;
    border-radius: var(--radius-md);
    display: flex;
    align-items: center;
    justify-content: center;
    flex-shrink: 0;
  }

  .platform-option-icon.zoom-icon {
    background: linear-gradient(135deg, #2d8cff 0%, #0b5cff 100%);
    color: #fff;
  }

  .platform-option-icon.meet-icon {
    background: linear-gradient(135deg, #00c853 0%, #00897b 100%);
    color: #fff;
  }

  .platform-option-info {
    flex: 1;
    display: flex;
    flex-direction: column;
    gap: 0.125rem;
  }

  .platform-option-name {
    font-size: 1rem;
    font-weight: 600;
    color: var(--color-text-primary);
    font-family: 'Plus Jakarta Sans', sans-serif;
  }

  .platform-option-desc {
    font-size: 0.8rem;
    color: var(--color-text-secondary);
  }

  .platform-option-check {
    width: 24px;
    height: 24px;
    border-radius: 50%;
    background: var(--color-primary);
    color: #fff;
    display: flex;
    align-items: center;
    justify-content: center;
    flex-shrink: 0;
  }

  .platform-modal-actions {
    display: flex;
    gap: 0.75rem;
  }

  .platform-modal-btn {
    flex: 1;
    padding: 0.75rem 1.25rem;
    font-size: 0.9rem;
    font-weight: 600;
    font-family: var(--font-family);
    border-radius: var(--radius-md);
    cursor: pointer;
    transition: all 0.15s;
    border: none;
  }

  .platform-modal-btn.primary {
    background: var(--gradient-primary);
    color: #fff;
    box-shadow: 0 4px 12px rgba(79, 70, 229, 0.3);
  }

  .platform-modal-btn.primary:hover {
    box-shadow: 0 6px 16px rgba(79, 70, 229, 0.4);
    transform: translateY(-1px);
  }

  .platform-modal-btn.secondary {
    background: #f3f4f6;
    color: var(--color-text-secondary);
    border: 1px solid var(--color-border);
  }

  .platform-modal-btn.secondary:hover {
    background: #e5e7eb;
  }

  /* =====================================================
     EXTENDED STATISTICS CARD STYLES
     ===================================================== */
  .stats-card-extended {
    min-height: auto;
  }

  .stats-grid-extended {
    grid-template-columns: repeat(2, 1fr);
    gap: 0.625rem;
  }

  /* Success state (< 3 days) - Green */
  .stat-tile-success {
    background: rgba(34, 197, 94, 0.12) !important;
    border-color: rgba(34, 197, 94, 0.25) !important;
  }

  .stat-tile-success:hover {
    background: rgba(34, 197, 94, 0.18) !important;
    border-color: rgba(34, 197, 94, 0.35) !important;
    transform: translateY(-3px);
  }

  .stat-tile-success .stat-icon {
    background: rgba(34, 197, 94, 0.2);
    color: #16a34a;
  }

  /* Lime state (3-7 days) - Lime/Yellow-Green */
  .stat-tile-lime {
    background: rgba(163, 230, 53, 0.15) !important;
    border-color: rgba(132, 204, 22, 0.25) !important;
  }

  .stat-tile-lime:hover {
    background: rgba(163, 230, 53, 0.22) !important;
    border-color: rgba(132, 204, 22, 0.35) !important;
    transform: translateY(-3px);
  }

  .stat-tile-lime .stat-icon {
    background: rgba(132, 204, 22, 0.2);
    color: #65a30d;
  }

  /* Warning state (7-14 days) - Light Red/Coral */
  .stat-tile-warning {
    background: rgba(254, 202, 202, 0.4) !important;
    border-color: rgba(239, 68, 68, 0.3) !important;
  }

  .stat-tile-warning:hover {
    background: rgba(254, 202, 202, 0.6) !important;
    border-color: rgba(239, 68, 68, 0.4) !important;
    transform: translateY(-3px);
  }

  .stat-tile-warning .stat-icon {
    background: rgba(239, 68, 68, 0.15);
    color: #dc2626;
  }

  /* Danger state (> 14 days) - Bright Red */
  .stat-tile-danger {
    background: rgba(239, 68, 68, 0.2) !important;
    border-color: rgba(220, 38, 38, 0.4) !important;
  }

  .stat-tile-danger:hover {
    background: rgba(239, 68, 68, 0.3) !important;
    border-color: rgba(220, 38, 38, 0.5) !important;
    transform: translateY(-3px);
  }

  .stat-tile-danger .stat-icon {
    background: rgba(220, 38, 38, 0.25);
    color: #b91c1c;
  }

  .stat-tile-danger .stat-value {
    color: #b91c1c;
  }

  /* Wide tile (spans 2 columns) */
  .stat-tile-wide {
    grid-column: span 2;
    flex-direction: row;
    justify-content: flex-start;
    gap: 1rem;
    padding: 0.875rem 1rem;
    min-height: 60px;
  }

  .stat-tile-wide .stat-content {
    flex-direction: row;
    align-items: center;
    gap: 0.5rem;
  }

  .stat-tile-wide .stat-value {
    font-size: 1.25rem;
    margin-bottom: 0;
  }

  .stat-tile-wide .stat-label {
    text-transform: none;
    font-size: 0.8rem;
  }

  /* Tooltip hint icon */
  .stat-tile-with-tooltip {
    position: relative;
  }

  .stat-tooltip-hint {
    position: absolute;
    top: 0.5rem;
    right: 0.5rem;
    display: inline-flex;
    align-items: center;
    justify-content: center;
    width: 28px;
    height: 28px;
    border-radius: 999px;
    border: 1px solid rgba(99, 102, 241, 0.18);
    background: rgba(255, 255, 255, 0.7);
    color: var(--color-text-muted);
    opacity: 0.5;
    transition:
      opacity var(--duration-fast, 180ms) var(--ease-smooth, cubic-bezier(0.4, 0, 0.2, 1)),
      transform var(--duration-fast, 180ms) var(--ease-smooth, cubic-bezier(0.4, 0, 0.2, 1)),
      background var(--duration-fast, 180ms) var(--ease-smooth, cubic-bezier(0.4, 0, 0.2, 1));
    cursor: help;
  }

  .stat-tooltip-hint:hover {
    transform: translateY(-1px);
  }

  .stat-tooltip-hint:focus {
    outline: none;
  }

  .stat-tooltip-hint:focus-visible {
    opacity: 1;
    color: var(--indigo-500);
    box-shadow: 0 0 0 3px rgba(99, 102, 241, 0.25);
  }

  .stat-tile-with-tooltip:hover .stat-tooltip-hint {
    opacity: 1;
    color: var(--indigo-500);
  }

  .stat-tooltip {
    position: absolute;
    top: 2.4rem;
    right: 0.5rem;
    width: 220px;
    padding: 0.6rem 0.75rem;
    border-radius: 14px;
    background: rgba(255, 255, 255, 0.92);
    border: 1px solid rgba(99, 102, 241, 0.14);
    box-shadow: 0 18px 45px rgba(15, 23, 42, 0.14);
    z-index: var(--z-tooltip, 1070);
    opacity: 0;
    transform: translateY(-6px) scale(0.98);
    pointer-events: none;
    transition:
      opacity var(--duration-normal, 280ms) var(--ease-smooth, cubic-bezier(0.4, 0, 0.2, 1)),
      transform var(--duration-normal, 280ms) var(--ease-spring, cubic-bezier(0.34, 1.56, 0.64, 1));
  }

  .stat-tooltip-title {
    font-size: 0.75rem;
    font-weight: 600;
    letter-spacing: 0.02em;
    color: var(--color-text, #0f172a);
    margin-bottom: 0.15rem;
  }

  .stat-tooltip-value {
    font-size: 0.8rem;
    color: var(--color-text-muted);
    display: flex;
    align-items: center;
    gap: 0.35rem;
    white-space: nowrap;
  }

  .stat-tooltip-sep {
    opacity: 0.6;
  }

  .stat-tile-with-tooltip:hover .stat-tooltip,
  .stat-tile-with-tooltip:focus-within .stat-tooltip {
    opacity: 1;
    transform: translateY(0) scale(1);
  }

  /* Auto-grading icon special color */
  .stat-icon-auto {
    background: linear-gradient(135deg, var(--indigo-100), #dbeafe);
    color: var(--indigo-600);
  }

  /* Responsive adjustments for extended stats */
  @media (max-width: 1400px) {
    .stats-grid-extended {
      gap: 0.5rem;
    }
    
    .stat-tile {
      padding: 0.75rem 0.5rem;
      min-height: 80px;
    }
    
    .stat-value {
      font-size: 1.25rem;
    }
    
    .stat-label {
      font-size: 0.7rem;
    }
  }

  @media (max-width: 768px) {
    .stats-grid-extended {
      grid-template-columns: repeat(2, 1fr);
    }
    
    .stat-tile-wide {
      grid-column: span 2;
    }
  }
`;

export default TeacherHomePage;
