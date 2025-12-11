import React, { useEffect, useState, useMemo, useCallback } from 'react';
import { useAuth } from '../auth';
import { getTeacherStatsSummary, getTeacherStatsBreakdown, getLessons, getIndividualStudents, startQuickLesson, apiClient } from '../apiService';
import { Link, useNavigate, useSearchParams } from 'react-router-dom';
import SwipeableLesson from './SwipeableLesson';
import EmptyState from './EmptyState';
import SupportWidget from './SupportWidget';
import SubscriptionBanner from './SubscriptionBanner';
import TelegramWarningBanner from './TelegramWarningBanner';
import GroupDetailModal from './GroupDetailModal';
import StudentCardModal from './StudentCardModal';
import './TeacherHomePage.css';

const ProgressBar = ({ value, variant = 'default' }) => {
  const safe = Number.isFinite(value) ? Math.max(0, Math.min(100, value)) : 0;
  return (
    <div className={`progress-bar pb-${variant}`}>
      <div className="progress-fill" style={{ width: `${safe}%` }} />
    </div>
  );
};

const TeacherHomePage = () => {
  const { accessTokenValid, subscription } = useAuth();
  const navigate = useNavigate();
  const [searchParams, setSearchParams] = useSearchParams();

  const [loading, setLoading] = useState(true);
  const [todayLessons, setTodayLessons] = useState([]);
  const [stats, setStats] = useState(null);
  const [breakdown, setBreakdown] = useState({ groups: [], students: [] });
  const [error, setError] = useState(null);
  const [quickLessonLoading, setQuickLessonLoading] = useState(false);
  const [quickLessonError, setQuickLessonError] = useState(null);
  const [paymentSuccess, setPaymentSuccess] = useState(false);
  const [groupDetailModal, setGroupDetailModal] = useState({ isOpen: false, group: null });
  const [studentCardModal, setStudentCardModal] = useState({ isOpen: false, studentId: null, groupId: null, isIndividual: false });

  useEffect(() => {
    if (searchParams.get('payment') === 'success') {
      setPaymentSuccess(true);
      searchParams.delete('payment');
      setSearchParams(searchParams, { replace: true });
      setTimeout(() => setPaymentSuccess(false), 5000);
    }
  }, [searchParams, setSearchParams]);

  const loadData = useCallback(async () => {
    if (!accessTokenValid) return;
    setLoading(true);
    setError(null);
    try {
      const todayDate = new Date().toISOString().split('T')[0];
      const [lessonsRes, statsRes, breakdownRes, individualStudentsRes] = await Promise.all([
        getLessons({ date: todayDate, include_recurring: true }),
        getTeacherStatsSummary(),
        getTeacherStatsBreakdown(),
        getIndividualStudents(),
      ]);

      const lessonsList = Array.isArray(lessonsRes.data)
        ? lessonsRes.data
        : lessonsRes.data.results || [];

      setTodayLessons(lessonsList);
      setStats(statsRes.data);

      const individualStudents = Array.isArray(individualStudentsRes.data)
        ? individualStudentsRes.data
        : individualStudentsRes.data.results || [];

      const individualStudentsForDisplay = individualStudents.map((st) => {
        const fullName = st.student_name || `${st.first_name || ''} ${st.last_name || ''}`.trim();
        return {
          id: st.user_id || st.student_id || st.id,
          name: fullName || st.email,
          email: st.email,
          group_id: null,
          group_name: 'Индивидуальный',
          attendance_percent: st.attendance_percent ?? 0,
          homework_percent: st.homework_percent ?? 0,
        };
      });

      setBreakdown({
        groups: breakdownRes.data?.groups || [],
        students: individualStudentsForDisplay,
      });
    } catch (err) {
      console.error('Ошибка загрузки данных:', err);
      setError('Не удалось загрузить данные. Попробуйте обновить страницу.');
    } finally {
      setLoading(false);
    }
  }, [accessTokenValid]);

  useEffect(() => {
    loadData();
  }, [loadData]);

  const launchZoomLesson = useCallback(async () => {
    setQuickLessonLoading(true);
    setQuickLessonError(null);
    try {
      const response = await startQuickLesson();
      const zoomUrl = response?.data?.zoom_start_url || response?.data?.zoom_url || response?.data?.start_url;
      if (!zoomUrl) {
        throw new Error('Ссылка для подключения не получена');
      }
      window.location.href = zoomUrl;
      await loadData();
    } catch (err) {
      console.error('Не удалось запустить быстрый урок:', err);
      const detail = err.response?.data?.detail || err.message || 'Не удалось создать урок.';
      setQuickLessonError(detail);
    } finally {
      setQuickLessonLoading(false);
    }
  }, [loadData]);

  const formatTime = (dateString) => {
    const date = new Date(dateString);
    return date.toLocaleTimeString('ru-RU', { hour: '2-digit', minute: '2-digit' });
  };

  const getLessonDuration = (lesson) => {
    if (lesson.duration_minutes && lesson.duration_minutes > 0) {
      return lesson.duration_minutes;
    }
    if (lesson.start_time && lesson.end_time) {
      const start = new Date(lesson.start_time);
      const end = new Date(lesson.end_time);
      const durationMinutes = Math.round((end - start) / (1000 * 60));
      if (durationMinutes > 0) return durationMinutes;
    }
    return 60;
  };

  const handleDeleteLesson = async (lessonId, deleteType) => {
    try {
      const lesson = todayLessons.find((l) => l.id === lessonId);
      if (!lesson) {
        throw new Error('Урок не найден в расписании. Обновите страницу и попробуйте ещё раз.');
      }

      if (deleteType === 'single') {
        await apiClient.delete(`schedule/lessons/${lessonId}/`);
        await loadData();
        return { status: 'deleted', message: `Урок «${lesson.title}» удалён` };
      }

      if (deleteType === 'recurring') {
        const response = await apiClient.post('schedule/lessons/delete_recurring/', {
          title: lesson.title,
          group_id: lesson.group || lesson.group_id,
        });
        await loadData();
        return {
          status: 'deleted',
          count: response?.data?.count,
          message: response?.data?.message || 'Похожие уроки удалены',
        };
      }

      throw new Error('Неизвестный тип удаления');
    } catch (err) {
      console.error('Ошибка удаления урока:', err);
      throw err;
    }
  };

  const derivedStats = useMemo(() => {
    const totalStudents = stats?.total_students || 0;
    const totalGroups = stats?.total_groups || 0;
    const lessonsCount = stats?.total_lessons || 0;
    const teachingMinutes = stats?.teaching_minutes || 0;
    const portalMinutes = stats?.portal_minutes || 0;

    return {
      totalStudents,
      totalGroups,
      lessonsCount,
      teachingMinutes,
      portalMinutes,
    };
  }, [stats]);

  const headerDate = useMemo(() => {
    const date = new Date();
    const formatted = date.toLocaleDateString('ru-RU', {
      day: 'numeric',
      month: 'long',
      weekday: 'long',
    });
    return formatted.charAt(0).toUpperCase() + formatted.slice(1);
  }, []);

  if (loading) {
    return (
      <div className="teacher-home-page min-h-screen grid place-items-center bg-[#F3F4F6]">
        <div className="text-center space-y-3">
          <div className="spinner" aria-hidden="true"></div>
          <p className="text-slate-600">Загрузка...</p>
        </div>
      </div>
    );
  }

  return (
    <div
      className="teacher-home-page min-h-screen bg-[#F3F4F6] text-slate-900"
      style={{ fontFamily: 'Manrope, "Inter", "Segoe UI", system-ui, sans-serif' }}
    >
      <TelegramWarningBanner />

      <header className="sticky top-0 z-30 backdrop-blur bg-white/80 border-b border-slate-200">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-16 flex items-center justify-between gap-4">
          <div className="flex items-center gap-3">
            <div className="h-10 w-10 rounded-xl bg-gradient-to-br from-[#6B4CFF] to-[#36C3FF] text-white font-bold grid place-items-center shadow-lg">
              LS
            </div>
            <div className="leading-tight">
              <div className="text-[11px] uppercase tracking-[0.18em] text-indigo-600 font-semibold">Lectio Space</div>
              <div className="text-sm text-slate-500">Панель преподавателя</div>
            </div>
          </div>

          <nav className="hidden md:flex items-center gap-5 text-sm text-slate-600">
            <Link to="/home-new" className="hover:text-indigo-600 transition">Главная</Link>
            <Link to="/groups" className="hover:text-indigo-600 transition">Группы</Link>
            <Link to="/calendar" className="hover:text-indigo-600 transition">Календарь</Link>
            <Link to="/materials" className="hover:text-indigo-600 transition">Материалы</Link>
          </nav>

          <div className="flex items-center gap-3">
            <button
              type="button"
              onClick={launchZoomLesson}
              disabled={quickLessonLoading}
              className="inline-flex items-center gap-2 rounded-xl bg-gradient-to-r from-[#6B4CFF] to-[#36C3FF] px-4 py-2 text-sm font-semibold text-white shadow-lg shadow-indigo-200 transition hover:shadow-xl active:scale-[0.98] disabled:opacity-70 disabled:cursor-not-allowed"
            >
              {quickLessonLoading ? 'Запуск...' : 'Быстрый урок'}
            </button>
          </div>
        </div>
      </header>

      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8 space-y-8">
        <SubscriptionBanner
          subscription={subscription}
          onPayClick={() => navigate('/teacher/subscription')}
        />

        {paymentSuccess && (
          <div style={{
            position: 'fixed',
            top: '84px',
            right: '20px',
            zIndex: 9999,
            background: 'linear-gradient(135deg, #f59e0b 0%, #fcd34d 100%)',
            color: '#0f172a',
            padding: '16px 24px',
            borderRadius: '12px',
            boxShadow: '0 10px 40px rgba(245, 158, 11, 0.35)',
            animation: 'slideInRight 0.5s ease',
            maxWidth: '400px',
            border: '2px solid rgba(15, 23, 42, 0.12)'
          }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
              <div style={{ fontSize: '24px' }}>🎉</div>
              <div>
                <div style={{ fontWeight: 600, marginBottom: '4px' }}>Платёж успешен!</div>
                <div style={{ fontSize: '14px', opacity: 0.9 }}>
                  Ваша подписка активирована
                </div>
              </div>
            </div>
          </div>
        )}

        <section className="relative overflow-hidden rounded-2xl bg-gradient-to-r from-[#6B4CFF] via-[#5B7CFF] to-[#36C3FF] text-white shadow-xl">
          <div className="absolute inset-0 opacity-50" aria-hidden="true">
            <div className="absolute -left-10 -top-16 h-40 w-40 rounded-full bg-white/10 blur-3xl" />
            <div className="absolute right-0 top-10 h-44 w-44 rounded-full bg-white/15 blur-3xl" />
          </div>

          <div className="relative flex flex-col lg:flex-row items-start gap-8 p-6 sm:p-8">
            <div className="flex-1 space-y-4">
              <p className="text-xs uppercase tracking-[0.2em] text-white/70">Главная панель · {headerDate}</p>
              <h1 className="text-3xl sm:text-4xl font-bold leading-tight">Запускайте уроки в Lectio Space за секунды</h1>
              <p className="text-base text-white/80 max-w-2xl">
                Единая точка управления расписанием, группами и материалами. Быстрый старт Zoom прямо с дашборда.
              </p>

              <div className="flex flex-wrap items-center gap-3">
                <button
                  type="button"
                  onClick={launchZoomLesson}
                  disabled={quickLessonLoading}
                  className="inline-flex items-center gap-3 rounded-xl bg-white/10 px-5 py-3 text-base font-semibold text-white shadow-lg shadow-black/20 ring-1 ring-white/30 transition hover:bg-white/20 active:scale-[0.98] disabled:opacity-70 disabled:cursor-not-allowed"
                >
                  {quickLessonLoading ? (
                    <>
                      <svg className="h-5 w-5 animate-spin" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
                        <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                        <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
                      </svg>
                      <span>Запускаем Zoom...</span>
                    </>
                  ) : (
                    <>
                      <svg className="h-5 w-5" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
                        <path d="M15 10l4.553-2.276A1 1 0 0121 8.618v6.764a1 1 0 01-1.447.894L15 14M5 18h8a2 2 0 002-2V8a2 2 0 00-2-2H5a2 2 0 00-2 2v8a2 2 0 002 2z" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
                      </svg>
                      <span>Быстрый урок</span>
                    </>
                  )}
                </button>

                <Link
                  to="/calendar"
                  className="inline-flex items-center gap-2 rounded-xl bg-white text-indigo-700 px-4 py-2 text-sm font-semibold shadow-md transition hover:shadow-lg"
                >
                  <span>Открыть календарь</span>
                  <span aria-hidden="true">→</span>
                </Link>
              </div>
            </div>

            <div className="grid w-full max-w-xl grid-cols-2 gap-3">
              {[{
                label: 'Проведённые уроки', value: derivedStats.lessonsCount
              }, {
                label: 'Ученики', value: derivedStats.totalStudents
              }, {
                label: 'Группы', value: derivedStats.totalGroups
              }, {
                label: 'Минут на платформе', value: derivedStats.portalMinutes
              }].map((item) => (
                <div key={item.label} className="rounded-2xl bg-white/10 p-4 backdrop-blur shadow-inner shadow-black/10">
                  <div className="text-sm text-white/70">{item.label}</div>
                  <div className="text-2xl font-semibold">{item.value}</div>
                </div>
              ))}
            </div>
          </div>
        </section>

        {quickLessonError && (
          <div className="rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700 shadow-sm">
            {quickLessonError}
          </div>
        )}

        {error && (
          <div className="rounded-xl border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-800 shadow-sm flex items-center justify-between gap-3">
            <span>{error}</span>
            <button onClick={loadData} className="text-indigo-700 font-semibold hover:underline">Повторить</button>
          </div>
        )}

        <section className="grid grid-cols-1 xl:grid-cols-3 gap-6">
          <div className="xl:col-span-2 space-y-6">
            <div className="bg-white rounded-2xl shadow-sm border border-slate-100 p-6">
              <div className="flex items-start justify-between gap-4">
                <div>
                  <h2 className="text-xl font-semibold text-slate-900">Расписание на сегодня</h2>
                  <p className="text-sm text-slate-500">{headerDate}</p>
                </div>
                <Link to="/calendar" className="text-sm font-semibold text-indigo-600 hover:text-indigo-700">Весь календарь</Link>
              </div>

              {todayLessons.length === 0 ? (
                <div className="mt-6">
                  <EmptyState
                    icon="☀️"
                    title="День свободен!"
                    description="У вас сегодня нет уроков. Используйте время для подготовки материалов или отдыха."
                    action={(
                      <button
                        type="button"
                        onClick={launchZoomLesson}
                        disabled={quickLessonLoading}
                        className="inline-flex items-center gap-2 rounded-full bg-indigo-600 px-4 py-2 text-sm font-semibold text-white shadow-lg shadow-indigo-500/30 transition hover:bg-indigo-700 focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:ring-offset-1 disabled:opacity-70 disabled:cursor-not-allowed"
                      >
                        {quickLessonLoading ? 'Создание...' : 'Запустить быстрый урок'}
                      </button>
                    )}
                  />
                </div>
              ) : (
                <div className="mt-6 space-y-3">
                  {todayLessons.map((lesson) => (
                    <SwipeableLesson
                      key={lesson.id}
                      lesson={lesson}
                      onDelete={handleDeleteLesson}
                      formatTime={formatTime}
                      getLessonDuration={getLessonDuration}
                    />
                  ))}
                </div>
              )}
            </div>

            <div className="bg-white rounded-2xl shadow-sm border border-slate-100 p-6 space-y-6">
              <div className="flex flex-wrap items-center justify-between gap-3">
                <h2 className="text-xl font-semibold text-slate-900">Группы и ученики</h2>
                <span className="text-sm text-slate-500">Свежая статистика</span>
              </div>

              <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
                <div className="space-y-3">
                  <div className="text-sm font-semibold text-slate-700">Группы</div>
                  {(!breakdown?.groups || breakdown.groups.length === 0) && (
                    <div className="rounded-xl border border-dashed border-slate-200 bg-slate-50 px-4 py-3 text-sm text-slate-500">Нет данных по группам</div>
                  )}
                  {breakdown?.groups && breakdown.groups.slice(0, 4).map((g) => (
                    <div
                      key={g.id}
                      className="rounded-xl border border-slate-100 px-4 py-3 hover:border-indigo-200 transition cursor-pointer"
                      role="button"
                      tabIndex={0}
                      onKeyDown={(e) => {
                        if (e.key === 'Enter' || e.key === ' ') {
                          e.preventDefault();
                          setGroupDetailModal({ isOpen: true, group: g });
                        }
                      }}
                      onClick={() => setGroupDetailModal({ isOpen: true, group: g })}
                    >
                      <div className="flex items-center justify-between gap-3">
                        <div>
                          <div className="text-sm font-semibold text-slate-900">{g.name}</div>
                          <div className="text-xs text-slate-500">Учеников: {g.students_count}</div>
                        </div>
                        <div className="text-xs text-indigo-600 font-semibold">Подробнее →</div>
                      </div>
                      <div className="mt-3 grid grid-cols-2 gap-3">
                        <div>
                          <div className="text-xs text-slate-500 mb-1">Посещаемость</div>
                          <ProgressBar value={g.attendance_percent} />
                          <div className="text-sm font-semibold mt-1">{g.attendance_percent != null ? g.attendance_percent + '%' : '—'}</div>
                        </div>
                        <div>
                          <div className="text-xs text-slate-500 mb-1">Домашние задания</div>
                          <ProgressBar value={g.homework_percent} variant="homework" />
                          <div className="text-sm font-semibold mt-1">{g.homework_percent != null ? g.homework_percent + '%' : '—'}</div>
                        </div>
                      </div>
                    </div>
                  ))}
                </div>

                <div className="space-y-3">
                  <div className="text-sm font-semibold text-slate-700">Индивидуальные ученики</div>
                  {(!breakdown?.students || breakdown.students.length === 0) && (
                    <div className="rounded-xl border border-dashed border-slate-200 bg-slate-50 px-4 py-3 text-sm text-slate-500">Нет индивидуальных учеников</div>
                  )}
                  {breakdown?.students && breakdown.students.slice(0, 5).map((st) => (
                    <div
                      key={st.id}
                      className="rounded-xl border border-slate-100 px-4 py-3 hover:border-indigo-200 transition cursor-pointer"
                      role="button"
                      tabIndex={0}
                      onKeyDown={(e) => {
                        if (e.key === 'Enter' || e.key === ' ') {
                          e.preventDefault();
                          setStudentCardModal({
                            isOpen: true,
                            studentId: st.id,
                            groupId: st.group_id || null,
                            isIndividual: !st.group_id,
                          });
                        }
                      }}
                      onClick={() => setStudentCardModal({
                        isOpen: true,
                        studentId: st.id,
                        groupId: st.group_id || null,
                        isIndividual: !st.group_id,
                      })}
                    >
                      <div className="flex items-center justify-between gap-3">
                        <div>
                          <div className="text-sm font-semibold text-slate-900">{st.name}</div>
                          <div className="text-xs text-slate-500">{st.group_name || 'Индивидуальный'}</div>
                        </div>
                        <div className="text-xs text-indigo-600 font-semibold">Карточка →</div>
                      </div>
                      <div className="mt-3 grid grid-cols-2 gap-3">
                        <div>
                          <div className="text-xs text-slate-500 mb-1">Посещаемость</div>
                          <ProgressBar value={st.attendance_percent} />
                          <div className="text-sm font-semibold mt-1">{st.attendance_percent != null ? st.attendance_percent + '%' : '—'}</div>
                        </div>
                        <div>
                          <div className="text-xs text-slate-500 mb-1">Домашние задания</div>
                          <ProgressBar value={st.homework_percent} variant="homework" />
                          <div className="text-sm font-semibold mt-1">{st.homework_percent != null ? st.homework_percent + '%' : '—'}</div>
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          </div>

          <div className="space-y-6">
            <div className="bg-white rounded-2xl shadow-sm border border-slate-100 p-6 space-y-4">
              <div className="flex items-center justify-between">
                <h2 className="text-xl font-semibold text-slate-900">Статистика</h2>
                <span className="text-xs text-slate-500">Обновлено {new Date().toLocaleTimeString('ru-RU', { hour: '2-digit', minute: '2-digit' })}</span>
              </div>
              <div className="grid grid-cols-2 gap-3">
                <div className="rounded-xl border border-slate-100 px-4 py-3">
                  <div className="text-xs text-slate-500">Уроки</div>
                  <div className="text-2xl font-semibold">{derivedStats.lessonsCount}</div>
                  <div className="text-xs text-slate-400">Завершённые</div>
                </div>
                <div className="rounded-xl border border-slate-100 px-4 py-3">
                  <div className="text-xs text-slate-500">Ученики</div>
                  <div className="text-2xl font-semibold">{derivedStats.totalStudents}</div>
                  <div className="text-xs text-slate-400">Активные</div>
                </div>
                <div className="rounded-xl border border-slate-100 px-4 py-3">
                  <div className="text-xs text-slate-500">Группы</div>
                  <div className="text-2xl font-semibold">{derivedStats.totalGroups}</div>
                  <div className="text-xs text-slate-400">Рабочие группы</div>
                </div>
                <div className="rounded-xl border border-slate-100 px-4 py-3">
                  <div className="text-xs text-slate-500">Минуты</div>
                  <div className="text-2xl font-semibold">{derivedStats.portalMinutes}</div>
                  <div className="text-xs text-slate-400">На платформе</div>
                </div>
              </div>
            </div>

            <div className="bg-white rounded-2xl shadow-sm border border-slate-100 p-6 space-y-4">
              <div className="flex items-center justify-between">
                <h2 className="text-xl font-semibold text-slate-900">Недавние материалы</h2>
                <Link to="/materials" className="text-sm font-semibold text-indigo-600 hover:text-indigo-700">Открыть все</Link>
              </div>
              {todayLessons.slice(0, 3).length === 0 ? (
                <div className="rounded-xl border border-dashed border-slate-200 bg-slate-50 px-4 py-3 text-sm text-slate-500">Материалы появятся после загрузки первых файлов или уроков.</div>
              ) : (
                <div className="space-y-3">
                  {todayLessons.slice(0, 3).map((lesson) => (
                    <div key={lesson.id} className="flex items-center justify-between rounded-xl border border-slate-100 px-4 py-3">
                      <div>
                        <div className="text-sm font-semibold text-slate-900">{lesson.title || 'Урок без названия'}</div>
                        <div className="text-xs text-slate-500">{formatTime(lesson.start_time)} · {lesson.group_name || lesson.group_title || 'Группа не указана'}</div>
                      </div>
                      <span className="text-xs text-slate-500">{getLessonDuration(lesson)} мин</span>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        </section>
      </main>

      <GroupDetailModal
        group={groupDetailModal.group}
        isOpen={groupDetailModal.isOpen}
        onClose={() => setGroupDetailModal({ isOpen: false, group: null })}
        onStudentClick={(studentId, groupId) => {
          setGroupDetailModal({ isOpen: false, group: null });
          setStudentCardModal({
            isOpen: true,
            studentId,
            groupId,
            isIndividual: false,
          });
        }}
      />

      <StudentCardModal
        studentId={studentCardModal.studentId}
        groupId={studentCardModal.groupId}
        isIndividual={studentCardModal.isIndividual}
        isOpen={studentCardModal.isOpen}
        onClose={() => setStudentCardModal({ isOpen: false, studentId: null, groupId: null, isIndividual: false })}
      />

      <SupportWidget />
    </div>
  );
};

export default TeacherHomePage;
