import React from 'react';
import { useOnboarding } from './useOnboarding';
import { 
  teacherTourSteps, 
  studentTourSteps,
  subscriptionTourSteps,
  homeworkTourSteps,
  homeworkConstructorTourSteps,
  recordingsTourSteps,
  analyticsTourSteps,
  marketTourSteps,
  studentHomeworkTourSteps,
  studentRecordingsTourSteps,
} from './tourConfig';
import {
  homeworkConstructorDetailedSteps,
  submissionReviewSteps,
  gradedSubmissionsListSteps,
  homeworkTakeSteps,
  studentAIReportsSteps,
  filterExistingSteps,
} from './driverConfig';

/**
 * Компонент онбординга для учителя (главная страница)
 * Автоматически запускает тур при первом входе
 * 
 * @param {function} onComplete - Callback после завершения тура
 * @param {number} userId - ID пользователя для привязки прогресса
 */
export const TeacherOnboarding = ({ onComplete, userId }) => {
  useOnboarding('teacher', teacherTourSteps, { onComplete, userId });
  return null; // Компонент не рендерит UI
};

/**
 * Компонент онбординга для ученика (главная страница)
 * Автоматически запускает тур при первом входе
 * 
 * @param {function} onComplete - Callback после завершения тура
 * @param {number} userId - ID пользователя для привязки прогресса
 */
export const StudentOnboarding = ({ onComplete, userId }) => {
  useOnboarding('student', studentTourSteps, { onComplete, userId });
  return null;
};

/**
 * Онбординг для страницы подписки (оплата, хранилище, Zoom)
 */
export const SubscriptionOnboarding = ({ onComplete, userId }) => {
  useOnboarding('subscription', subscriptionTourSteps, { onComplete, userId });
  return null;
};

/**
 * Онбординг для страницы домашних заданий (вкладки)
 */
export const HomeworkOnboarding = ({ onComplete, userId }) => {
  useOnboarding('homework', homeworkTourSteps, { onComplete, userId });
  return null;
};

/**
 * Онбординг для конструктора ДЗ (детальный тур по созданию заданий)
 */
export const HomeworkConstructorOnboarding = ({ onComplete, userId }) => {
  useOnboarding('homework-constructor', homeworkConstructorTourSteps, { onComplete, userId });
  return null;
};

/**
 * Онбординг для страницы записей уроков
 */
export const RecordingsOnboarding = ({ onComplete, userId }) => {
  useOnboarding('recordings', recordingsTourSteps, { onComplete, userId });
  return null;
};

/**
 * Онбординг для страницы аналитики
 */
export const AnalyticsOnboarding = ({ onComplete, userId }) => {
  useOnboarding('analytics', analyticsTourSteps, { onComplete, userId });
  return null;
};

/**
 * Онбординг для маркета (магазин услуг)
 */
export const MarketOnboarding = ({ onComplete, userId }) => {
  useOnboarding('market', marketTourSteps, { onComplete, userId });
  return null;
};

/**
 * Онбординг для страницы ДЗ ученика
 */
export const StudentHomeworkOnboarding = ({ onComplete, userId }) => {
  useOnboarding('student-homework', studentHomeworkTourSteps, { onComplete, userId });
  return null;
};

// =====================================================
// НОВЫЕ ДЕТАЛЬНЫЕ ТУРЫ ДЛЯ ДОМАШНИХ ЗАДАНИЙ
// =====================================================

/**
 * Детальный онбординг для конструктора ДЗ с объяснением ВСЕХ типов вопросов
 * Используется при первом создании задания
 */
export const HomeworkConstructorDetailedOnboarding = ({ onComplete, userId }) => {
  // Фильтруем шаги, чтобы показывать только существующие элементы
  const filteredSteps = React.useMemo(() => {
    return filterExistingSteps(homeworkConstructorDetailedSteps);
  }, []);
  
  useOnboarding('homework-constructor-detailed', filteredSteps, { onComplete, userId });
  return null;
};

/**
 * Онбординг для страницы проверки работы ученика
 * Объясняет AI-анализ и выставление оценок
 */
export const SubmissionReviewOnboarding = ({ onComplete, userId }) => {
  const filteredSteps = React.useMemo(() => {
    return filterExistingSteps(submissionReviewSteps);
  }, []);
  
  useOnboarding('submission-review', filteredSteps, { onComplete, userId });
  return null;
};

/**
 * Онбординг для списка сданных работ
 * Объясняет статусы и фильтры
 */
export const GradedSubmissionsListOnboarding = ({ onComplete, userId }) => {
  const filteredSteps = React.useMemo(() => {
    return filterExistingSteps(gradedSubmissionsListSteps);
  }, []);
  
  useOnboarding('graded-submissions', filteredSteps, { onComplete, userId });
  return null;
};

/**
 * Онбординг для прохождения ДЗ учеником (детальный)
 * Объясняет все типы вопросов с точки зрения ученика
 */
export const HomeworkTakeOnboarding = ({ onComplete, userId }) => {
  const filteredSteps = React.useMemo(() => {
    return filterExistingSteps(homeworkTakeSteps);
  }, []);
  
  useOnboarding('homework-take', filteredSteps, { onComplete, userId });
  return null;
};

/**
 * Онбординг для страницы AI-анализа результатов ученика
 */
export const StudentAIReportsOnboarding = ({ onComplete, userId }) => {
  const filteredSteps = React.useMemo(() => {
    return filterExistingSteps(studentAIReportsSteps);
  }, []);
  
  useOnboarding('student-ai-reports', filteredSteps, { onComplete, userId });
  return null;
};

/**
 * Онбординг для страницы записей ученика
 */
export const StudentRecordingsOnboarding = ({ onComplete, userId }) => {
  useOnboarding('student-recordings', studentRecordingsTourSteps, { onComplete, userId });
  return null;
};

/**
 * Универсальный компонент с render-props для ручного управления туром
 * 
 * Использование:
 * <OnboardingTrigger tourKey="teacher">
 *   {({ startTour, resetTour, isCompleted }) => (
 *     <button onClick={startTour}>Повторить тур</button>
 *   )}
 * </OnboardingTrigger>
 */
export const OnboardingTrigger = ({ tourKey, children, autoStart = false }) => {
  const stepsMap = {
    // Базовые туры
    teacher: teacherTourSteps,
    student: studentTourSteps,
    subscription: subscriptionTourSteps,
    homework: homeworkTourSteps,
    'homework-constructor': homeworkConstructorTourSteps,
    recordings: recordingsTourSteps,
    analytics: analyticsTourSteps,
    market: marketTourSteps,
    'student-homework': studentHomeworkTourSteps,
    'student-recordings': studentRecordingsTourSteps,
    
    // Детальные туры для домашних заданий
    'homework-constructor-detailed': homeworkConstructorDetailedSteps,
    'submission-review': submissionReviewSteps,
    'graded-submissions': gradedSubmissionsListSteps,
    'homework-take': homeworkTakeSteps,
    'student-ai-reports': studentAIReportsSteps,
  };
  
  const rawSteps = stepsMap[tourKey] || teacherTourSteps;
  // Фильтруем шаги для детальных туров
  const steps = tourKey.includes('detailed') || tourKey.includes('review') || tourKey.includes('take') || tourKey.includes('ai-reports')
    ? filterExistingSteps(rawSteps)
    : rawSteps;
  
  // Если autoStart=false, передаём пустой массив чтобы отключить автозапуск
  const { startTour, resetTour, isCompleted } = useOnboarding(
    tourKey,
    autoStart ? steps : [],
    {}
  );

  // Для ручного запуска нужен доступ к реальным шагам
  const manualStart = () => {
    if (steps.length > 0) {
      // Создаём новый инстанс driver.js для ручного запуска
      import('driver.js').then(({ driver }) => {
        const driverInstance = driver({
          showProgress: true,
          showButtons: ['next', 'previous', 'close'],
          popoverClass: 'lectio-tour-popover',
          overlayColor: 'rgba(15, 23, 42, 0.75)',
          stagePadding: 10,
          stageRadius: 12,
          popoverOffset: 12,
          smoothScroll: true,
          allowClose: true,
          doneBtnText: 'Готово',
          closeBtnText: 'Пропустить',
          nextBtnText: 'Далее',
          prevBtnText: 'Назад',
          progressText: '{{current}} из {{total}}',
          steps: steps.filter(step => !step.element || document.querySelector(step.element)),
        });
        driverInstance.drive();
      });
    }
  };

  return children({ 
    startTour: manualStart, 
    resetTour, 
    isCompleted 
  });
};

export default { 
  // Базовые туры
  TeacherOnboarding, 
  StudentOnboarding, 
  SubscriptionOnboarding,
  HomeworkOnboarding,
  HomeworkConstructorOnboarding,
  RecordingsOnboarding,
  AnalyticsOnboarding,
  MarketOnboarding,
  StudentHomeworkOnboarding,
  StudentRecordingsOnboarding,
  
  // Детальные туры для ДЗ
  HomeworkConstructorDetailedOnboarding,
  SubmissionReviewOnboarding,
  GradedSubmissionsListOnboarding,
  HomeworkTakeOnboarding,
  StudentAIReportsOnboarding,
  
  // Утилиты
  OnboardingTrigger,
};
