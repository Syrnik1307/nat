import React, { Suspense, lazy, useEffect, useState, useMemo, memo } from 'react';
import { BrowserRouter, Routes, Route, Navigate, useLocation } from 'react-router-dom';
import './App.css';
import { AuthProvider, useAuth, Protected } from './auth';
import { NotificationProvider } from './shared/context/NotificationContext';
import { AuthCheckingSkeleton } from './shared/components';
import SubmissionReview from './modules/homework-analytics/components/teacher/SubmissionReview';

// Навбары загружаются синхронно - они нужны сразу
// Мемоизируем их чтобы избежать ререндеров при смене страницы
import NavBarNewBase from './components/NavBarNew';
import StudentNavBarBase from './components/StudentNavBar';

const NavBarNew = memo(NavBarNewBase);
const StudentNavBar = memo(StudentNavBarBase);

// Минимальный fallback - почти мгновенный skeleton
// Показываем прелоадер сразу, но с лёгким fade-in для плавности
const PageLoader = () => {
  return (
    <div className="page-loader-wrapper visible">
      <div className="page-loader-content">
        <div className="page-loader-spinner" />
      </div>
      <style>{`
        .page-loader-wrapper {
          display: flex;
          justify-content: center;
          align-items: center;
          min-height: 40vh;
          background: transparent;
          opacity: 1;
          animation: pageLoaderFadeIn 0.1s ease-out;
        }
        @keyframes pageLoaderFadeIn {
          from { opacity: 0; }
          to { opacity: 1; }
        }
        .page-loader-content {
          display: flex;
          flex-direction: column;
          align-items: center;
          gap: 16px;
        }
        .page-loader-spinner {
          width: 32px;
          height: 32px;
          border: 2px solid #e2e8f0;
          border-top-color: #4F46E5;
          border-radius: 50%;
          animation: pageLoaderSpin 0.6s linear infinite;
        }
        @keyframes pageLoaderSpin { 
          to { transform: rotate(360deg); } 
        }
      `}</style>
    </div>
  );
};

// === PRELOADING: Загружаем основные страницы сразу после первого рендера ===
// Это критически важно для быстрой навигации между страницами

// Lazy imports с prefetch - компоненты начинают грузиться в фоне
const teacherHomeImport = () => import('./components/TeacherHomePage');
const studentHomeImport = () => import('./components/StudentHomePage');
const analyticsImport = () => import('./components/AnalyticsPage');
const profileImport = () => import('./components/ProfilePage');
const groupsManageImport = () => import('./components/GroupsManage');
const homeworkPageImport = () => import('./modules/homework-analytics/components/HomeworkPage');
const homeworkListImport = () => import('./components/HomeworkList');
const homeworkTakeImport = () => import('./modules/homework-analytics/components/homework/HomeworkTake');
const homeworkAnswersImport = () => import('./modules/homework-analytics/components/homework/HomeworkAnswersView');
const calendarImport = () => import('./modules/core/calendar/Calendar');
const recordingsImport = () => import('./modules/Recordings/RecordingsPage');
const teacherRecordingsImport = () => import('./modules/Recordings/TeacherRecordingsPage');
const teacherMaterialsImport = () => import('./modules/Recordings/TeacherMaterialsPage');
const studentMaterialsImport = () => import('./modules/Recordings/StudentMaterialsPage');
const studentDashboardImport = () => import('./components/StudentDashboard');

// Lazy-loaded компоненты - грузятся по требованию
const AuthPage = lazy(() => import('./components/AuthPage'));
const RegisterPage = lazy(() => import('./components/RegisterPage'));
const EmailVerificationPage = lazy(() => import('./components/EmailVerificationPage'));
const PasswordResetPage = lazy(() => import('./components/PasswordResetPage'));
const MockPaymentPage = lazy(() => import('./components/MockPaymentPage'));
const PaymentResultPage = lazy(() => import('./components/PaymentResultPage'));
const StatusPage = lazy(() => import('./components/StatusPage'));

// Teacher pages - используем уже созданные импорты
const TeacherHomePage = lazy(teacherHomeImport);
const AttendanceLogPage = lazy(() => import('./components/AttendanceLogPage'));
const TeacherRecordingsPage = lazy(teacherRecordingsImport);
const TeacherMaterialsPage = lazy(teacherMaterialsImport);
const AnalyticsPage = lazy(analyticsImport);
const HomeworkManage = lazy(() => import('./components/HomeworkManage'));
const HomeworkPage = lazy(homeworkPageImport);
const SubmissionsList = lazy(() => import('./modules/homework-analytics/components/teacher/SubmissionsList'));
const RecurringLessonsManage = lazy(() => import('./components/RecurringLessonsManage'));
const GroupsManage = lazy(groupsManageImport);
const StudentAIReports = lazy(() => import('./components/StudentAIReports'));
const CalendarIntegrationPage = lazy(() => import('./components/CalendarIntegrationSimple'));

// Student pages - используем уже созданные импорты
const StudentHomePage = lazy(studentHomeImport);
const StudentDashboard = lazy(studentDashboardImport);
const RecordingsPage = lazy(recordingsImport);
const StudentMaterialsPage = lazy(studentMaterialsImport);
const HomeworkList = lazy(homeworkListImport);
const HomeworkTake = lazy(homeworkTakeImport);
const HomeworkAnswersView = lazy(homeworkAnswersImport);

// Admin pages
const AdminHomePage = lazy(() => import('./components/AdminHomePage'));

// Common pages - используем уже созданный импорт
const Calendar = lazy(calendarImport);
const ProfilePage = lazy(profileImport);
const ChatPage = lazy(() => import('./components/ChatPage'));

// Preload основных страниц после загрузки приложения
const preloadPages = (role) => {
  // Используем requestIdleCallback для загрузки в фоне без блокировки UI
  const scheduleLoad = (fn) => {
    if ('requestIdleCallback' in window) {
      requestIdleCallback(() => fn(), { timeout: 3000 });
    } else {
      setTimeout(fn, 100);
    }
  };
  
  if (role === 'teacher') {
    scheduleLoad(teacherHomeImport);
    scheduleLoad(analyticsImport);
    scheduleLoad(groupsManageImport);
    scheduleLoad(homeworkPageImport);
    scheduleLoad(profileImport);
    scheduleLoad(teacherRecordingsImport);
    scheduleLoad(teacherMaterialsImport); // Предзагрузка Материалов учителя
  } else if (role === 'student') {
    scheduleLoad(studentHomeImport);
    scheduleLoad(studentDashboardImport);
    scheduleLoad(recordingsImport);
    scheduleLoad(studentMaterialsImport); // Предзагрузка Материалов ученика
    scheduleLoad(profileImport);
    scheduleLoad(homeworkListImport);
    scheduleLoad(homeworkTakeImport);
    scheduleLoad(homeworkAnswersImport);
    scheduleLoad(calendarImport);
  }
};

const RoleRouter = () => {
  const { accessTokenValid, role, loading } = useAuth();
  if (loading) return <AuthCheckingSkeleton />;
  if (!accessTokenValid) return <Navigate to="/auth-new" replace />;
  if (role === 'teacher') return <Navigate to="/teacher" replace />;
  if (role === 'student') return <Navigate to="/student" replace />;
  if (role === 'admin') return <Navigate to="/admin-home" replace />;
  return <div style={{ padding:'2rem' }}>Роль не поддерживается: {role}</div>;
};

const AppRoutes = () => {
  const location = useLocation();
  const { accessTokenValid, role } = useAuth();
  const hideNavPaths = ['/auth-new', '/register', '/verify-email'];
  const baseNavVisible = !hideNavPaths.includes(location.pathname);
  const isStudentView = accessTokenValid && role === 'student';
  const isAdminHomeView = accessTokenValid && role === 'admin' && location.pathname.startsWith('/admin-home');
  const shouldShowStudentNav = baseNavVisible && isStudentView;
  // В админке используем собственный хедер страницы, верхний общий navbar не показываем
  const shouldShowNav = baseNavVisible && !isStudentView && !isAdminHomeView;

  // Preload страниц после авторизации
  useEffect(() => {
    if (accessTokenValid && role) {
      preloadPages(role);
    }
  }, [accessTokenValid, role]);

  const RootRedirect = () => {
    const { accessTokenValid, role, loading } = useAuth();
    if (loading) return <AuthCheckingSkeleton />;
    if (!accessTokenValid) return <Navigate to="/auth-new" replace />;
    if (role === 'teacher') return <Navigate to="/home-new" replace />;
    if (role === 'student') return <Navigate to="/student" replace />;
    if (role === 'admin') return <Navigate to="/admin-home" replace />;
    return <Navigate to="/auth-new" replace />;
  };
  return (
    <>
      {shouldShowStudentNav && <StudentNavBar />}
      {shouldShowNav && <NavBarNew />}
      <Suspense fallback={<PageLoader />}>
        <Routes>
          <Route path="/" element={<RootRedirect />} />
          {/* Auth */}
          <Route path="/auth-new" element={<AuthPage />} />
          <Route path="/register" element={<RegisterPage />} />
          <Route path="/verify-email" element={<EmailVerificationPage />} />
          <Route path="/reset-password/:uid/:token" element={<PasswordResetPage />} />
          <Route path="/mock-payment" element={<MockPaymentPage />} />
          <Route path="/status" element={<StatusPage />} />
          <Route path="/teacher/subscription/success" element={<Protected allowRoles={['teacher', 'admin']}><PaymentResultPage /></Protected>} />
          
          {/* Teacher */}
          <Route path="/home-new" element={<Protected allowRoles={['teacher', 'admin']}><TeacherHomePage /></Protected>} />
          <Route path="/teacher" element={<Navigate to="/home-new" replace />} />
          <Route path="/attendance/:groupId" element={<Protected allowRoles={['teacher', 'admin']}><AttendanceLogPage /></Protected>} />
          <Route path="/teacher/recordings" element={<Protected allowRoles={['teacher']}><TeacherRecordingsPage /></Protected>} />
          <Route path="/teacher/materials" element={<Protected allowRoles={['teacher']}><TeacherMaterialsPage /></Protected>} />
          <Route path="/homework/manage" element={<Protected allowRoles={['teacher']}><HomeworkManage /></Protected>} />
          <Route
            path="/homework/constructor"
            element={<Protected allowRoles={['teacher']}><HomeworkPage /></Protected>}
          />
          <Route
            path="/homework/my"
            element={<Protected allowRoles={['teacher']}><HomeworkPage /></Protected>}
          />
          <Route
            path="/homework/templates"
            element={<Protected allowRoles={['teacher']}><Navigate to="/homework/my" replace /></Protected>}
          />
          <Route
            path="/homework/to-review"
            element={<Protected allowRoles={['teacher']}><HomeworkPage /></Protected>}
          />
          <Route
            path="/homework/graded"
            element={<Protected allowRoles={['teacher']}><HomeworkPage /></Protected>}
          />
          <Route
            path="/submissions"
            element={<Protected allowRoles={['teacher']}><SubmissionsList /></Protected>}
          />
          <Route
            path="/submissions/:submissionId/review"
            element={<Protected allowRoles={['teacher']}><SubmissionReview /></Protected>}
          />
          <Route path="/recurring-lessons/manage" element={<Protected allowRoles={['teacher']}><RecurringLessonsManage /></Protected>} />
          <Route path="/groups/manage" element={<Protected allowRoles={['teacher']}><GroupsManage /></Protected>} />
          <Route path="/analytics" element={<Protected allowRoles={['teacher', 'admin']}><AnalyticsPage /></Protected>} />
          <Route path="/teacher/ai-reports" element={<Protected allowRoles={['teacher']}><StudentAIReports /></Protected>} />
          <Route path="/calendar/settings" element={<Protected allowRoles={['teacher', 'student']}><CalendarIntegrationPage /></Protected>} />
          
          {/* Student */}
          <Route path="/student" element={<Protected allowRoles={['student']}><StudentHomePage /></Protected>} />
          <Route path="/student/courses" element={<Protected allowRoles={['student']}><StudentHomePage /></Protected>} />
          <Route path="/student/stats" element={<Protected allowRoles={['student']}><StudentDashboard /></Protected>} />
          <Route path="/student/recordings" element={<Protected allowRoles={['student']}><RecordingsPage /></Protected>} />
          <Route path="/student/materials" element={<Protected allowRoles={['student']}><StudentMaterialsPage /></Protected>} />
          <Route path="/homework" element={<Protected allowRoles={['student']}><HomeworkList /></Protected>} />
          <Route path="/student/homework/:id" element={<Protected allowRoles={['student']}><HomeworkTake /></Protected>} />
          <Route path="/homework/:id/answers" element={<Protected allowRoles={['student']}><HomeworkAnswersView /></Protected>} />
        
          {/* Admin */}
          <Route path="/admin" element={<Navigate to="/admin-home" replace />} />
          <Route path="/admin-home" element={<Protected allowRoles={['admin']}><AdminHomePage /></Protected>} />
          
          {/* Common */}
          <Route path="/calendar" element={<Protected allowRoles={['teacher', 'student']}><Calendar /></Protected>} />
          <Route path="/profile" element={<Protected allowRoles={['teacher', 'student', 'admin']}><ProfilePage /></Protected>} />
          <Route path="/billing" element={<Navigate to="/profile?tab=subscription" replace />} />
          <Route path="/teacher/subscription" element={<Navigate to="/profile?tab=subscription" replace />} />
          <Route path="/chat" element={<Protected allowRoles={['teacher', 'student']}><ChatPage /></Protected>} />
          <Route path="/redirect" element={<RoleRouter />} />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </Suspense>
    </>
  );
};

function App() {
  return (
    <AuthProvider>
      <BrowserRouter future={{
        v7_startTransition: true,
        v7_relativeSplatPath: true
      }}>
        <NotificationProvider>
          <AppRoutes />
        </NotificationProvider>
      </BrowserRouter>
    </AuthProvider>
  );
}

export default App;
