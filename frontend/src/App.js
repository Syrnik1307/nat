import React from 'react';
import { BrowserRouter, Routes, Route, Navigate, useLocation } from 'react-router-dom';
import './App.css';
import { AuthProvider, useAuth, Protected } from './auth';
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
// Импорт новых компонентов из модуля Core
import { Calendar } from './modules/core';
import { HomeworkConstructor } from './modules/homework-analytics';
// Новый дизайн - синяя тема
import AuthPage from './components/AuthPage';
import EmailVerificationPage from './components/EmailVerificationPage';
import PasswordResetPage from './components/PasswordResetPage';
import TeacherHomePage from './components/TeacherHomePage';
import AdminHomePage from './components/AdminHomePage';
import NavBarNew from './components/NavBarNew';
import StudentNavBar from './components/StudentNavBar';
import ProfilePage from './components/ProfilePage';
// Chat система
import ChatPage from './components/ChatPage';
// Записи уроков
import RecordingsPage from './modules/Recordings/RecordingsPage';
import TeacherRecordingsPage from './modules/Recordings/TeacherRecordingsPage';
// Админ - управление хранилищем

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
  const { accessTokenValid, role } = useAuth();
  const hideNavPaths = ['/auth-new', '/register', '/verify-email'];
  const baseNavVisible = !hideNavPaths.includes(location.pathname);
  const isStudentView = accessTokenValid && role === 'student';
  const shouldShowStudentNav = baseNavVisible && isStudentView;
  const shouldShowNav = baseNavVisible && !isStudentView;

  const RootRedirect = () => {
    const { accessTokenValid, role, loading } = useAuth();
    if (loading) return <div style={{ padding: '2rem', textAlign: 'center' }}>Проверка авторизации...</div>;
    if (!accessTokenValid) return <Navigate to="/auth-new" replace />;
    if (role === 'teacher') return <Navigate to="/home-new" replace />;
    if (role === 'student') return <Navigate to="/student" replace />;
    if (role === 'admin') return <Navigate to="/admin" replace />;
    return <Navigate to="/auth-new" replace />;
  };
  return (
    <>
      {shouldShowStudentNav && <StudentNavBar />}
      {shouldShowNav && <NavBarNew />}
      <Routes>
        <Route path="/" element={<RootRedirect />} />
        {/* Auth */}
        <Route path="/auth-new" element={<AuthPage />} />
        <Route path="/register" element={<RegisterPage />} />
        <Route path="/verify-email" element={<EmailVerificationPage />} />
        <Route path="/reset-password/:uid/:token" element={<PasswordResetPage />} />
        
        {/* Teacher */}
        <Route path="/home-new" element={<Protected allowRoles={['teacher', 'admin']}><TeacherHomePage /></Protected>} />
        <Route path="/teacher" element={<Protected allowRoles={['teacher', 'admin']}><TeacherDashboard /></Protected>} />
        <Route path="/teacher/recordings" element={<Protected allowRoles={['teacher']}><TeacherRecordingsPage /></Protected>} />
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
        <Route path="/student/recordings" element={<Protected allowRoles={['student']}><RecordingsPage /></Protected>} />
        <Route path="/homework" element={<Protected allowRoles={['student']}><HomeworkList /></Protected>} />
        <Route path="/student/homework/:id" element={<Protected allowRoles={['student']}><HomeworkTake /></Protected>} />
        
        {/* Admin */}
        <Route path="/admin" element={<Protected allowRoles={['admin']}><AdminHomePage /></Protected>} />
        
        {/* Common */}
        <Route path="/calendar" element={<Protected allowRoles={['teacher', 'student']}><Calendar /></Protected>} />
        <Route path="/profile" element={<Protected allowRoles={['teacher', 'student', 'admin']}><ProfilePage /></Protected>} />
        <Route path="/chat" element={<Protected allowRoles={['teacher', 'student']}><ChatPage /></Protected>} />
        <Route path="/redirect" element={<RoleRouter />} />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
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
        <AppRoutes />
      </BrowserRouter>
    </AuthProvider>
  );
}

export default App;
