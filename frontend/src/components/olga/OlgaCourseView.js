import React, { useState, useEffect, useCallback } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { apiClient } from '../../apiService';
import { getAccessToken } from '../../apiService';
import { useAuth } from '../../auth';
import './OlgaCourseView.css';

const PLAYBACK_DEVICE_KEY = 'tp_playback_device_id';

const getOrCreatePlaybackDeviceId = () => {
  try {
    const existing = localStorage.getItem(PLAYBACK_DEVICE_KEY);
    if (existing) return existing;

    const nextValue = window.crypto?.randomUUID
      ? window.crypto.randomUUID()
      : `dev-${Date.now()}-${Math.random().toString(16).slice(2)}`;

    localStorage.setItem(PLAYBACK_DEVICE_KEY, nextValue);
    return nextValue;
  } catch {
    return `dev-fallback-${Date.now()}`;
  }
};

const getIframeSrc = (rawUrl) => {
  if (!rawUrl) return '';

  try {
    const url = new URL(rawUrl);
    const host = url.hostname.replace('www.', '');

    // ── Kinescope ────────────────────────────────────────────
    if (host === 'kinescope.io' || host === 'player.kinescope.io') {
      // Уже embed — используем как есть
      if (url.pathname.startsWith('/embed/')) {
        return rawUrl;
      }
      // Преобразуем обычную ссылку в embed
      const videoId = url.pathname.split('/').filter(Boolean).pop();
      return videoId ? `https://kinescope.io/embed/${videoId}` : rawUrl;
    }

    if (host === 'youtu.be') {
      const videoId = url.pathname.split('/').filter(Boolean)[0];
      return videoId ? `https://www.youtube.com/embed/${videoId}` : rawUrl;
    }

    if (host === 'youtube.com' || host === 'm.youtube.com') {
      if (url.pathname === '/watch') {
        const videoId = url.searchParams.get('v');
        return videoId ? `https://www.youtube.com/embed/${videoId}` : rawUrl;
      }

      if (url.pathname.startsWith('/shorts/')) {
        const videoId = url.pathname.split('/').filter(Boolean)[1];
        return videoId ? `https://www.youtube.com/embed/${videoId}` : rawUrl;
      }

      if (url.pathname.startsWith('/embed/')) {
        return rawUrl;
      }
    }

    if (host === 'vimeo.com') {
      const videoId = url.pathname.split('/').filter(Boolean)[0];
      return videoId ? `https://player.vimeo.com/video/${videoId}` : rawUrl;
    }

    if (host === 'rutube.ru') {
      if (url.pathname.startsWith('/play/embed/')) {
        return rawUrl;
      }

      if (url.pathname.startsWith('/video/')) {
        const videoId = url.pathname.split('/').filter(Boolean)[1];
        return videoId ? `https://rutube.ru/play/embed/${videoId}` : rawUrl;
      }
    }

    return rawUrl;
  } catch {
    return rawUrl;
  }
};

/**
 * OlgaCourseView — страница просмотра отдельного курса.
 *
 * Для купленных курсов показывает:
 * - Список уроков (записи + текстовые материалы)
 * - Видеоплеер для текущего урока
 * - Текстовый контент урока
 *
 * Для не-купленных — описание и кнопку покупки.
 */
const OlgaCourseView = () => {
  const { courseId } = useParams();
  const navigate = useNavigate();
  const { user } = useAuth();
  const [course, setCourse] = useState(null);
  const [loading, setLoading] = useState(true);
  const [activeLesson, setActiveLesson] = useState(null);
  const isMobile = typeof window !== 'undefined' && window.innerWidth <= 768;
  const [sidebarOpen, setSidebarOpen] = useState(!isMobile);
  const [showBuyModal, setShowBuyModal] = useState(false);
  const [buying, setBuying] = useState(false);
  const [protectionSessionToken, setProtectionSessionToken] = useState(null);
  const [protectedVideoUrl, setProtectedVideoUrl] = useState(null);
  const [blockedReason, setBlockedReason] = useState('');
  const [watermarkTick, setWatermarkTick] = useState(0);

  const protectionEnabled = Boolean(activeLesson?.protected_content_id);
  const watermarkPositions = ['top-left', 'top-right', 'bottom-left', 'bottom-right'];
  const watermarkPosition = watermarkPositions[watermarkTick % watermarkPositions.length];

  const reportProtectionEvent = useCallback(async (eventType, severity = 'warning', metadata = {}) => {
    if (!protectionSessionToken) return;
    try {
      const res = await apiClient.post('content-protection/sessions/event/', {
        session_token: protectionSessionToken,
        event_type: eventType,
        severity,
        metadata: {
          lesson_id: activeLesson?.id,
          course_id: course?.id,
          ...metadata,
        },
      });

      if (res?.data?.action === 'block') {
        setBlockedReason(res.data.blocked_reason || 'Нарушение политики защиты контента');
      }
    } catch (err) {
      const blocked = err?.response?.data;
      if (blocked?.action === 'block') {
        setBlockedReason(blocked.blocked_reason || 'Доступ заблокирован системой защиты');
      }
    }
  }, [protectionSessionToken, activeLesson?.id, course?.id]);

  const loadCourse = useCallback(async () => {
    setLoading(true);
    try {
      const res = await apiClient.get(`courses/${courseId}/`);
      setCourse(res.data);
      if (res.data.lessons?.length > 0) {
        setActiveLesson(res.data.lessons[0]);
      }
    } catch (err) {
      console.error('Ошибка загрузки курса:', err);
      const demo = getDemoCourse(courseId);
      setCourse(demo);
      if (demo.lessons?.length > 0) setActiveLesson(demo.lessons[0]);
    } finally {
      setLoading(false);
    }
  }, [courseId]);

  useEffect(() => {
    loadCourse();
  }, [loadCourse]);

  useEffect(() => {
    setBlockedReason('');
  }, [activeLesson?.id]);

  useEffect(() => {
    let mounted = true;

    const startProtection = async () => {
      if (!activeLesson?.protected_content_id || blockedReason) {
        setProtectionSessionToken(null);
        setProtectedVideoUrl(null);
        return;
      }

      try {
        const res = await apiClient.post('content-protection/sessions/start/', {
          content_id: activeLesson.protected_content_id,
        });

        if (!mounted) return;

        setProtectionSessionToken(res.data.session_token);

        const deviceId = getOrCreatePlaybackDeviceId();
        try {
          const playbackRes = await apiClient.post('content-protection/sessions/playback-url/', {
            session_token: res.data.session_token,
            device_id: deviceId,
          });

          if (!mounted) return;
          setProtectedVideoUrl(playbackRes?.data?.playback_url || activeLesson.video_url);
        } catch {
          if (!mounted) return;
          setProtectedVideoUrl(activeLesson.video_url || null);
        }
      } catch (err) {
        if (!mounted) return;
        setProtectionSessionToken(null);
        setProtectedVideoUrl(activeLesson.video_url || null);
      }
    };

    startProtection();

    return () => {
      mounted = false;
    };
  }, [activeLesson?.id, activeLesson?.protected_content_id, activeLesson?.video_url, blockedReason]);

  useEffect(() => {
    if (!protectionSessionToken || blockedReason) return undefined;

    let stopped = false;

    const sendHeartbeat = async () => {
      if (stopped) return;

      const devtoolsOpen = Math.abs(window.outerWidth - window.innerWidth) > 160 ||
        Math.abs(window.outerHeight - window.innerHeight) > 160;

      try {
        const res = await apiClient.post('content-protection/sessions/heartbeat/', {
          session_token: protectionSessionToken,
          is_visible: document.visibilityState === 'visible',
          is_focused: document.hasFocus(),
          is_fullscreen: Boolean(document.fullscreenElement),
          devtools_open: devtoolsOpen,
          recorder_suspected: false,
          display_capture_detected: false,
          multiple_screens_detected: false,
          metadata: {
            lesson_id: activeLesson?.id,
            course_id: course?.id,
            href: window.location.href,
          },
        });

        if (res?.data?.action === 'block') {
          setBlockedReason(res.data.blocked_reason || 'Сессия заблокирована системой защиты');
        }
      } catch (err) {
        const data = err?.response?.data;
        if (data?.action === 'block' || data?.status === 'blocked') {
          setBlockedReason(data.blocked_reason || 'Сессия заблокирована системой защиты');
        }
      }
    };

    const interval = window.setInterval(sendHeartbeat, 5000);
    sendHeartbeat();

    return () => {
      stopped = true;
      window.clearInterval(interval);
    };
  }, [protectionSessionToken, activeLesson?.id, course?.id, blockedReason]);

  useEffect(() => {
    if (!protectionSessionToken || blockedReason) return undefined;

    const onVisibility = () => {
      if (document.visibilityState !== 'visible') {
        reportProtectionEvent('tab_hidden', 'warning', { visibility: document.visibilityState });
      }
    };

    const onBlur = () => reportProtectionEvent('window_blur', 'info');

    const onFullscreen = () => {
      if (!document.fullscreenElement) {
        reportProtectionEvent('fullscreen_exited', 'warning');
      }
    };

    const onKeyDown = (event) => {
      if (event.key === 'PrintScreen') {
        reportProtectionEvent('print_screen_pressed', 'warning');
      }
      if (event.key === 'F12' || ((event.ctrlKey || event.metaKey) && event.shiftKey && event.key.toLowerCase() === 'i')) {
        reportProtectionEvent('devtools_opened', 'warning');
      }
    };

    const mediaDevices = navigator.mediaDevices;
    const originalGetDisplayMedia = mediaDevices?.getDisplayMedia ? mediaDevices.getDisplayMedia.bind(mediaDevices) : null;
    let patchedGetDisplayMedia = false;

    if (mediaDevices && originalGetDisplayMedia) {
      try {
        mediaDevices.getDisplayMedia = async (...args) => {
          reportProtectionEvent('display_capture_detected', 'critical', { source: 'browser_api' });
          return originalGetDisplayMedia(...args);
        };
        patchedGetDisplayMedia = true;
      } catch {
        patchedGetDisplayMedia = false;
      }
    }

    document.addEventListener('visibilitychange', onVisibility);
    window.addEventListener('blur', onBlur);
    document.addEventListener('fullscreenchange', onFullscreen);
    window.addEventListener('keydown', onKeyDown);

    return () => {
      document.removeEventListener('visibilitychange', onVisibility);
      window.removeEventListener('blur', onBlur);
      document.removeEventListener('fullscreenchange', onFullscreen);
      window.removeEventListener('keydown', onKeyDown);

      if (mediaDevices && originalGetDisplayMedia && patchedGetDisplayMedia) {
        mediaDevices.getDisplayMedia = originalGetDisplayMedia;
      }
    };
  }, [protectionSessionToken, blockedReason, reportProtectionEvent]);

  useEffect(() => {
    if (!protectionSessionToken) return undefined;

    const endSession = () => {
      const token = getAccessToken();
      if (!token) return;

      fetch(`/api/content-protection/sessions/${protectionSessionToken}/end/`, {
        method: 'POST',
        keepalive: true,
        headers: {
          Authorization: `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
      }).catch(() => undefined);
    };

    window.addEventListener('beforeunload', endSession);
    return () => {
      endSession();
      window.removeEventListener('beforeunload', endSession);
    };
  }, [protectionSessionToken]);

  useEffect(() => {
    if (!protectionEnabled || blockedReason) return undefined;

    const interval = window.setInterval(() => {
      setWatermarkTick((value) => value + 1);
    }, 7000);

    return () => {
      window.clearInterval(interval);
    };
  }, [protectionEnabled, blockedReason, activeLesson?.id]);

  if (loading) {
    return (
      <div className="olga-course-loading">
        <div className="olga-spinner" />
        <p>Загрузка курса...</p>
      </div>
    );
  }

  if (!course) {
    return (
      <div className="olga-course-not-found">
        <span className="olga-nf-icon">—</span>
        <h2>Курс не найден</h2>
        <button className="olga-back-btn" onClick={() => navigate('/olga/courses')}>
          ← К каталогу курсов
        </button>
      </div>
    );
  }

  // Не куплен — показываем описание
  if (!course.has_access) {
    return (
      <div className="olga-course-preview">
        <button className="olga-back-link" onClick={() => navigate('/olga/courses')}>
          ← К каталогу
        </button>
        <div className="olga-preview-hero">
          {course.cover_url ? (
            <img src={course.cover_url} alt={course.title} className="olga-preview-cover" />
          ) : (
            <div className="olga-preview-cover-placeholder">
              <span>Фото</span>
            </div>
          )}
        </div>
        <div className="olga-preview-body">
          <h1 className="olga-preview-title">{course.title}</h1>
          <p className="olga-preview-desc">{course.description}</p>

          <div className="olga-preview-details">
            {course.lessons_count != null && (
              <div className="olga-detail-item">
                <span className="olga-detail-icon">Уроки</span>
                <span>{course.lessons_count} уроков</span>
              </div>
            )}
            {course.duration && (
              <div className="olga-detail-item">
                <span className="olga-detail-icon">Длительность</span>
                <span>{course.duration}</span>
              </div>
            )}
          </div>

          {course.lessons && course.lessons.length > 0 && (
            <div className="olga-preview-lessons">
              <h3>Программа курса</h3>
              <ol className="olga-lesson-list-preview">
                {course.lessons.map((lesson, i) => (
                  <li key={lesson.id || i} className="olga-lesson-preview-item">
                    <span className="olga-lesson-num">{i + 1}</span>
                    <span className="olga-lesson-name">{lesson.title}</span>
                    {lesson.duration && <span className="olga-lesson-dur">{lesson.duration}</span>}
                  </li>
                ))}
              </ol>
            </div>
          )}

          <div className="olga-preview-cta">
            <div className="olga-preview-price">
              {course.price ? `${course.price} ₽` : 'Бесплатно'}
            </div>
            {user ? (
              <button className="olga-buy-btn" onClick={() => setShowBuyModal(true)}>
                Получить доступ
              </button>
            ) : (
              <button className="olga-buy-btn" onClick={() => navigate('/olga/auth')}>
                Войти и купить
              </button>
            )}
          </div>
        </div>

        {/* Модальное окно покупки */}
        {showBuyModal && (
          <div className="olga-modal-overlay" onClick={() => setShowBuyModal(false)}>
            <div className="olga-modal" onClick={e => e.stopPropagation()}>
              <button className="olga-modal-close" onClick={() => setShowBuyModal(false)}>×</button>
              <h2>Подтверждение покупки</h2>
              <div className="olga-modal-course-info">
                <h3>{course.title}</h3>
                <p className="olga-modal-price">{course.price ? `${course.price} ₽` : 'Бесплатно'}</p>
              </div>
              <p className="olga-modal-note">
                Сейчас действует тестовый режим: реальная касса для Ольги ещё не подключена.
                Нажмите «Получить доступ», чтобы активировать курс.
              </p>
              <div className="olga-modal-actions">
                <button
                  className="olga-modal-cancel"
                  onClick={() => setShowBuyModal(false)}
                  disabled={buying}
                >
                  Отмена
                </button>
                <button
                  className="olga-modal-buy"
                  disabled={buying}
                  onClick={async () => {
                    setBuying(true);
                    try {
                      await apiClient.post(`courses/${courseId}/grant-access/`, {
                        access_type: 'purchased'
                      });
                      setShowBuyModal(false);
                      // Перезагрузим курс — теперь has_access = true
                      loadCourse();
                    } catch (err) {
                      console.error('Ошибка покупки:', err);
                      alert('Ошибка при оформлении доступа. Попробуйте снова.');
                    } finally {
                      setBuying(false);
                    }
                  }}
                >
                  {buying ? 'Обработка...' : 'Получить доступ'}
                </button>
              </div>
            </div>
          </div>
        )}
      </div>
    );
  }

  // Куплен — показываем уроки с контентом
  return (
    <div className={`olga-course-view ${sidebarOpen ? '' : 'sidebar-closed'}`}>
      {/* Сайдбар со списком уроков */}
      <aside className={`olga-lessons-sidebar ${sidebarOpen ? 'open' : ''}`}>
        <div className="olga-sidebar-header">
          <button className="olga-back-link" onClick={() => navigate('/olga/courses')}>
            ← Каталог
          </button>
          <h2 className="olga-sidebar-title">{course.title}</h2>
        </div>
        <ul className="olga-lessons-list">
          {(course.lessons || []).map((lesson, i) => (
            <li
              key={lesson.id || i}
              className={`olga-lesson-item ${activeLesson?.id === lesson.id ? 'active' : ''}`}
              onClick={() => {
                setActiveLesson(lesson);
                if (window.innerWidth <= 768) setSidebarOpen(false);
              }}
              role="button"
              tabIndex={0}
              onKeyDown={(e) => {
                if (e.key === 'Enter') {
                  setActiveLesson(lesson);
                  if (window.innerWidth <= 768) setSidebarOpen(false);
                }
              }}
            >
              <span className="olga-lesson-number">{i + 1}</span>
              <div className="olga-lesson-info">
                <span className="olga-lesson-title">{lesson.title}</span>
                {lesson.duration && (
                  <span className="olga-lesson-duration">{lesson.duration}</span>
                )}
              </div>
              {lesson.completed && <span className="olga-lesson-check">✓</span>}
            </li>
          ))}
        </ul>
      </aside>

      {/* Основной контент */}
      <main className="olga-lesson-content">
        <div className="olga-content-topbar">
          <button
            className="olga-toggle-sidebar"
            onClick={() => setSidebarOpen(!sidebarOpen)}
            aria-label="Переключить список уроков"
          >
            {sidebarOpen ? '◂' : '▸'} Уроки
          </button>
          {activeLesson && (
            <h3 className="olga-content-title">{activeLesson.title}</h3>
          )}
        </div>

        {activeLesson ? (
          <div className="olga-lesson-body">
            {blockedReason && (
              <div className="olga-protection-blocked">
                <h4>Просмотр временно заблокирован</h4>
                <p>{blockedReason}</p>
              </div>
            )}

            {/* Видео */}
            {!blockedReason && activeLesson.video_status === 'processing' && (
              <div className="olga-video-wrap olga-video-processing">
                <div className="olga-processing-message">
                  <span className="olga-processing-icon">...</span>
                  <h4>Видео обрабатывается</h4>
                  <p>Видео загружено и находится в обработке. Обычно это занимает несколько минут.</p>
                </div>
              </div>
            )}

            {!blockedReason && activeLesson.video_status === 'error' && (
              <div className="olga-video-wrap olga-video-error">
                <div className="olga-processing-message">
                  <span className="olga-processing-icon">Ошибка</span>
                  <h4>Ошибка обработки видео</h4>
                  <p>При обработке видео произошла ошибка. Попробуйте загрузить видео повторно.</p>
                </div>
              </div>
            )}

            {!blockedReason && activeLesson.video_url && activeLesson.video_status !== 'processing' && activeLesson.video_status !== 'error' && (
              <div className="olga-video-wrap">
                <iframe
                  key={protectedVideoUrl || activeLesson.video_url}
                  className="olga-video-player"
                  src={getIframeSrc(protectedVideoUrl || activeLesson.kinescope_embed_url || activeLesson.video_url)}
                  title={activeLesson.title || 'Видео урока'}
                  allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture; web-share"
                  allowFullScreen
                  loading="lazy"
                  referrerPolicy="strict-origin-when-cross-origin"
                />
                {protectionEnabled && user && activeLesson.video_provider !== 'kinescope' && (
                  <div className={`olga-video-watermark ${watermarkPosition}`}>
                    {user.email} · {new Date().toLocaleString()} · {watermarkTick}
                  </div>
                )}
              </div>
            )}

            {/* Текстовый контент */}
            {activeLesson.content && (
              <div
                className="olga-lesson-text"
                dangerouslySetInnerHTML={{ __html: activeLesson.content }}
              />
            )}

            {/* Материалы для скачивания */}
            {activeLesson.materials && activeLesson.materials.length > 0 && (
              <div className="olga-lesson-materials">
                <h4>Материалы</h4>
                <ul>
                  {activeLesson.materials.map((m, i) => (
                    <li key={i}>
                      <a href={m.url} target="_blank" rel="noopener noreferrer">
                        Файл: {m.name || m.url}
                      </a>
                    </li>
                  ))}
                </ul>
              </div>
            )}
          </div>
        ) : (
          <div className="olga-no-lesson">
            <span>—</span>
            <p>Выберите урок из списка</p>
          </div>
        )}
      </main>
    </div>
  );
};

/** Демо-данные для курса */
function getDemoCourse(id) {
  return {
    id,
    title: 'Основы лепки фарфоровых роз',
    description: 'В этом курсе вы научитесь создавать реалистичные розы из холодного фарфора — от простейших бутонов до пышных многолепестковых цветов. Каждый урок содержит видеозапись мастер-класса и подробные текстовые материалы. Вы узнаете о подготовке материалов, правильной раскатке лепестков, способах тонировки и финишной обработке.',
    cover_url: null,
    price: 4900,
    has_access: true,
    lessons_count: 5,
    duration: '3 часа',
    lessons: [
      {
        id: 'l1',
        title: 'Введение. Материалы и инструменты',
        duration: '15 мин',
        video_url: null,
        content: '<h3>Добро пожаловать!</h3><p>В этом уроке вы узнаете, какие материалы и инструменты понадобятся для создания фарфоровых цветов.</p><h4>Список материалов:</h4><ul><li>Холодный фарфор (самозатвердевающий)</li><li>Масляные краски для тонировки</li><li>Клей ПВА</li><li>Проволока флористическая (№24, №26)</li><li>Тейп-лента зелёная</li></ul><h4>Инструменты:</h4><ul><li>Стек с шариком</li><li>Молд лепестка розы</li><li>Каттеры (вырубки)</li><li>Коврик для раскатки</li><li>Кисти для тонировки</li></ul>',
        materials: [],
        completed: true,
      },
      {
        id: 'l2',
        title: 'Подготовка массы и раскатка',
        duration: '25 мин',
        video_url: null,
        content: '<h3>Подготовка массы</h3><p>Правильная подготовка массы — залог успеха. В этом уроке разберём как замешать массу, добиться нужной пластичности и окрасить её в базовый цвет.</p><p>Масса должна быть эластичной, не липнуть к рукам и не трескаться при высыхании.</p>',
        materials: [],
        completed: true,
      },
      {
        id: 'l3',
        title: 'Лепка лепестков розы',
        duration: '35 мин',
        video_url: null,
        content: '<h3>Создание лепестков</h3><p>Формируем лепестки разного размера — от маленьких внутренних до крупных внешних. Используем молд для придания текстуры.</p>',
        materials: [],
        completed: false,
      },
      {
        id: 'l4',
        title: 'Сборка розы',
        duration: '40 мин',
        video_url: null,
        content: '<h3>Сборка цветка</h3><p>Собираем розу послойно: сердцевина, внутренние лепестки, средние, наружные. Крепим на проволочный стебель.</p>',
        materials: [],
        completed: false,
      },
      {
        id: 'l5',
        title: 'Тонировка и финиш',
        duration: '30 мин',
        video_url: null,
        content: '<h3>Тонировка</h3><p>Придаём розе реалистичность с помощью сухой пастели и масляных красок. Учимся наносить градиенты и тени.</p>',
        materials: [],
        completed: false,
      },
    ],
  };
}

export default OlgaCourseView;
