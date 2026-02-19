import React, { useEffect } from 'react';
import { BrowserRouter, Routes, Route, Navigate, useLocation } from 'react-router-dom';
import './App.css';
import './branding.css';
import { AuthProvider, useAuth, Protected } from './auth';
import { TenantProvider, setTenantSlug } from './TenantContext';
import { BrandingProvider } from './BrandingContext';
import RegisterPage from './components/RegisterPage';
import TeacherDashboard from './components/TeacherDashboard';
import StudentDashboard from './components/StudentDashboard';
import StudentHomePage from './components/StudentHomePage';
import HomeworkList from './components/HomeworkList';
import HomeworkSubmission from './components/HomeworkSubmission';
import HomeworkTake from './modules/homework-analytics/components/homework/HomeworkTake';
import SubmissionReview from './modules/homework-analytics/components/teacher/SubmissionReview';
import SubmissionsList from './modules/homework-analytics/components/teacher/SubmissionsList';
import HomeworkManage from './components/HomeworkManage';
import RecurringLessonsManage from './components/RecurringLessonsManage';
import GroupsManage from './components/GroupsManage';
import { Calendar } from './modules/core';
import { HomeworkConstructor } from './modules/homework-analytics';
import AuthPage from './components/AuthPage';
import EmailVerificationPage from './components/EmailVerificationPage';
import PasswordResetPage from './components/PasswordResetPage';
import TeacherHomePage from './components/TeacherHomePage';
import AdminHomePage from './components/AdminHomePage';
import BrandingAdmin from './components/BrandingAdmin';
import NavBarNew from './components/NavBarNew';
import ProfilePage from './components/ProfilePage';
import ChatPage from './components/ChatPage';
import OlgaAuthPage from './components/olga/OlgaAuthPage';
import OlgaCourseCatalog from './components/olga/OlgaCourseCatalog';
import OlgaCourseView from './components/olga/OlgaCourseView';
import OlgaNavBar from './components/olga/OlgaNavBar';
import OlgaProfile from './components/olga/OlgaProfile';
import OlgaCourseAdmin from './components/olga/OlgaCourseAdmin';
import OlgaDashboard from './components/olga/OlgaDashboard';

// Lazy loaded components
const SimpleResetPage = React.lazy(() => import('./components/SimpleResetPage'));
const FinancePage = React.lazy(() => import('./components/FinancePage'));

const RoleRouter = () => {
  const { accessTokenValid, role, loading } = useAuth();
  if (loading) return <div style={{ padding: '2rem', textAlign: 'center' }}>Проверка авторизации...</div>;
  if (!accessTokenValid) return <Navigate to="/auth-new" replace />;
  if (role === 'teacher') return <Navigate to="/teacher" replace />;
  if (role === 'student') return <Navigate to="/student" replace />;
  if (role === 'admin') return <Navigate to="/admin" replace />;
  return <div style={{ padding:'2rem' }}>Роль не поддерживается: {role}</div>;
};

const AppRoutes = () => {
  const location = useLocation();
  const hostname = window.location.hostname || '';
  const isOlgaDomain = hostname === 'olga.lectiospace.ru' || hostname.startsWith('olga.');
  const hideNavPaths = ['/auth-new', '/register', '/verify-email', '/olga/auth', '/simple-reset'];
  const isOlgaRoute = location.pathname.startsWith('/olga');
  const shouldShowNav = !hideNavPaths.includes(location.pathname) && !isOlgaRoute;

  // Автоматически устанавливаем tenant slug для маршрутов Ольги
  useEffect(() => {
    if (isOlgaRoute || isOlgaDomain) {
      setTenantSlug('olga');
    }
  }, [isOlgaRoute, isOlgaDomain]);

  const RootRedirect = () => {
    const { accessTokenValid, role, loading } = useAuth();
    if (loading) return <div style={{ padding: '2rem', textAlign: 'center' }}>Проверка авторизации...</div>;
    if (!accessTokenValid) return <Navigate to={isOlgaDomain ? '/olga/courses' : '/auth-new'} replace />;
    if (isOlgaDomain) {
      if (role === 'teacher' || role === 'admin') return <Navigate to="/home-new" replace />;
      if (role === 'student') return <Navigate to="/olga/my" replace />;
      return <Navigate to="/olga/courses" replace />;
    }
    if (role === 'teacher') return <Navigate to="/home-new" replace />;
    if (role === 'student') return <Navigate to="/student" replace />;
    if (role === 'admin') return <Navigate to="/admin" replace />;
    return <Navigate to="/auth-new" replace />;
  };
  return (
    <>
      {shouldShowNav && <NavBarNew />}
      {isOlgaRoute && !hideNavPaths.includes(location.pathname) && <OlgaNavBar />}
      <Routes>
        <Route path="/" element={<RootRedirect />} />
        {/* Auth */}
        <Route path="/auth-new" element={isOlgaDomain ? <Navigate to="/olga/auth" replace /> : <AuthPage />} />
        <Route path="/register" element={<RegisterPage />} />
        <Route path="/verify-email" element={<EmailVerificationPage />} />
        <Route path="/reset-password/:uid/:token" element={<PasswordResetPage />} />
        <Route path="/simple-reset" element={<React.Suspense fallback={<div style={{padding:'2rem',textAlign:'center'}}>Загрузка...</div>}><SimpleResetPage /></React.Suspense>} />
        
        {/* Olga tenant routes */}
        <Route path="/olga/auth" element={<OlgaAuthPage />} />
        <Route path="/olga/courses" element={<OlgaCourseCatalog />} />
        <Route path="/olga/courses/:courseId" element={<OlgaCourseView />} />
        <Route path="/olga/my" element={<Protected allowRoles={['student', 'teacher', 'admin']}><OlgaDashboard /></Protected>} />
        <Route path="/olga/admin" element={<Protected allowRoles={['teacher', 'admin']}><OlgaCourseAdmin /></Protected>} />
        <Route path="/olga/profile" element={<Protected allowRoles={['student', 'teacher', 'admin']}><OlgaProfile /></Protected>} />
        
        {/* Маршруты LectioSpace — скрыты на домене Ольги */}
        {!isOlgaDomain && (
          <>
            {/* Teacher */}
            <Route path="/home-new" element={<Protected allowRoles={['teacher', 'admin']}><TeacherHomePage /></Protected>} />
            <Route path="/teacher" element={<Protected allowRoles={['teacher', 'admin']}><TeacherDashboard /></Protected>} />
            <Route path="/homework/manage" element={<Protected allowRoles={['teacher']}><HomeworkManage /></Protected>} />
            <Route
              path="/homework/constructor"
              element={<Protected allowRoles={['teacher']}><HomeworkConstructor /></Protected>}
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
            
            {/* Student */}
            <Route path="/student" element={<Protected allowRoles={['student']}><StudentHomePage /></Protected>} />
            <Route path="/student/courses" element={<Protected allowRoles={['student']}><StudentHomePage /></Protected>} />
            <Route path="/student/stats" element={<Protected allowRoles={['student']}><StudentDashboard /></Protected>} />
            <Route path="/homework" element={<Protected allowRoles={['student']}><HomeworkList /></Protected>} />
            <Route path="/student/homework/:id" element={<Protected allowRoles={['student']}><HomeworkTake /></Protected>} />
            
            {/* Admin */}
            <Route path="/admin" element={<Protected allowRoles={['admin']}><AdminHomePage /></Protected>} />
            <Route path="/admin/branding" element={<Protected allowRoles={['admin', 'owner']}><BrandingAdmin /></Protected>} />
            
            {/* Finance */}
            <Route path="/finance" element={<Protected allowRoles={['teacher', 'admin']}><React.Suspense fallback={<div>Загрузка...</div>}><FinancePage /></React.Suspense></Protected>} />
            
            {/* Common */}
            <Route path="/calendar" element={<Protected allowRoles={['teacher', 'student']}><Calendar /></Protected>} />
            <Route path="/profile" element={<Protected allowRoles={['teacher', 'student', 'admin']}><ProfilePage /></Protected>} />
            <Route path="/chat" element={<Protected allowRoles={['teacher', 'student']}><ChatPage /></Protected>} />
            <Route path="/redirect" element={<RoleRouter />} />
          </>
        )}
        <Route path="*" element={<Navigate to={isOlgaDomain ? '/olga/courses' : '/'} replace />} />

      </Routes>
    </>
  );
};

function App() {
  return (
    <AuthProvider>
      <TenantProvider>
        <BrandingProvider>
          <BrowserRouter future={{
            v7_startTransition: true,
            v7_relativeSplatPath: true
          }}>
            <AppRoutes />
          </BrowserRouter>
        </BrandingProvider>
      </TenantProvider>
    </AuthProvider>
  );
}

export default App;
